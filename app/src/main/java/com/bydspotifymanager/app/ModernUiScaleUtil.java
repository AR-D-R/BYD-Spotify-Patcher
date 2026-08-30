package com.bydspotifymanager.app;

import java.util.Arrays;

/**
 * Runtime sizing patch for Spotify 9.1.78.2215 modern UI surfaces.
 *
 * The older v13-v16 experimental base replaced eleven public F0():float method
 * bodies in classes.dex with a hard-coded 1.5f return. Those edits survived even
 * after resource dp/sp values were restored, which is why playlist/player text
 * remained enlarged at the Manager's 100% setting.
 *
 * This helper is exact-version/fail-closed and is now a consistency backstop.
 * v0.1.11 also patches the Android-backed Compose Density factory in classes2.dex,
 * which is the source of truth used by player/playlist typography. At 100% the
 * caller invokes neither patch, leaving the stock DEX untouched. For larger
 * presets these getters are kept consistent with the factory-selected scale.
 */
final class ModernUiScaleUtil {
    private ModernUiScaleUtil() {}

    private static final Target[] TARGETS = new Target[] {
            new Target(0x33bfc4, "5410355c380007007210d44c00000a000f001500803f0f00"),
            new Target(0x35b7d4, "54105f7872102ed600000c007210d44c00000a000f00"),
            new Target(0x41e1ec, "521020240f00"),
            new Target(0x41e31c, "5210972a0f00"),
            new Target(0x540784, "5410ac9e7210d44c00000a000f00"),
            new Target(0x5a9ed8, "541015535400ed5971108fe200007210d44c00000a000f00"),
            new Target(0x5f0600, "521073142b000a0000001500803f0f001500803f0f000000000101000000000006000000"),
            new Target(0x617270, "5410ca9a7210d44c00000a000f00"),
            new Target(0x63d854, "541072287210d44c00000a000f00"),
            new Target(0x6b00c4, "54106a4d6e108b8800000a000f00"),
            new Target(0x6b05d4, "71103de001000c0054003fb57210d44c00000a000f00")
    };

    static byte[] apply(byte[] stockDex, float requestedScale) throws Exception {
        if (Math.abs(requestedScale - 1.0f) < 0.0001f) return stockDex;
        if (requestedScale < 1.0f || requestedScale > 2.0f) {
            throw new IllegalArgumentException("Unsupported runtime UI scale: " + requestedScale);
        }

        // The shortest target method has only three 16-bit instructions available.
        // const/high16 v0 + return v0 fits exactly. Round the IEEE-754 high half to
        // the nearest representable value: 1.20 -> 1.203125, 1.40 -> 1.3984375, 1.60 -> 1.6015625.
        int bits = Float.floatToIntBits(requestedScale);
        int high16 = ((bits + 0x8000) >>> 16) & 0xffff;

        byte[] out = stockDex.clone();
        for (Target target : TARGETS) {
            int off = target.offset;
            byte[] expected = target.stockInstructions;
            if (off < 0 || off + expected.length > out.length) {
                throw new IllegalStateException("Spotify 9.1 runtime-scale target is outside classes.dex");
            }
            byte[] actual = Arrays.copyOfRange(out, off, off + expected.length);
            if (!Arrays.equals(actual, expected)) {
                throw new IllegalStateException(
                        "Spotify 9.1 runtime-scale signature mismatch at 0x" + Integer.toHexString(off));
            }

            Arrays.fill(out, off, off + expected.length, (byte) 0x00); // nop padding
            out[off] = 0x15;                 // const/high16 v0, #BBBB0000
            out[off + 1] = 0x00;
            out[off + 2] = (byte) (high16 & 0xff);
            out[off + 3] = (byte) ((high16 >>> 8) & 0xff);
            out[off + 4] = 0x0f;             // return v0
            out[off + 5] = 0x00;
        }
        return DexUtil.repair(out);
    }

    private static final class Target {
        final int offset;
        final byte[] stockInstructions;

        Target(int offset, String stockHex) {
            this.offset = offset;
            this.stockInstructions = hex(stockHex);
        }
    }

    private static byte[] hex(String s) {
        if ((s.length() & 1) != 0) throw new IllegalArgumentException("Odd hex length");
        byte[] out = new byte[s.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(s.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }
}
