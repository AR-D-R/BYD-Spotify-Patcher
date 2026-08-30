package com.bydspotifymanager.app;

import java.util.Arrays;

/**
 * Forces the Android-backed Compose Density factory in Spotify 9.1.78.2215 to
 * use the Manager-selected font scale.
 *
 * Spotify/Compose creates its runtime DensityWithConverter in classes2.dex by
 * reading Resources.Configuration.fontScale.  The previous v0.1.10 patch only
 * replaced Density.F0() getters later in classes.dex.  Optimised Compose code
 * can use the density object's stored fontScale/converter directly, so changing
 * those getters did not change player/playlist typography.
 *
 * This patch changes the source of truth instead: the exact 4-byte
 *   iget v0, v0, Configuration.fontScale
 * instruction in Density(context) is replaced by an equal-size const/high16.
 * The same v0 is then used both to construct the FontScaleConverter and as the
 * DensityWithConverter.fontScale constructor argument.  No DEX offsets move.
 *
 * 100% never invokes this helper and therefore stays byte-for-byte stock.
 */
final class ComposeFontScaleUtil {
    private ComposeFontScaleUtil() {}

    // classes2.dex, method Lp/l3d1;.a(Context):Lp/dlp;
    // Stock instruction: iget v0, v0, Landroid/content/res/Configuration;->fontScale:F
    private static final int FONT_SCALE_READ_OFFSET = 0x7d3d68;
    private static final byte[] STOCK_FONT_SCALE_READ = hex("52003100");

    static byte[] apply(byte[] stockDex, float requestedScale) throws Exception {
        if (Math.abs(requestedScale - 1.0f) < 0.0001f) return stockDex;
        if (requestedScale < 1.0f || requestedScale > 2.0f) {
            throw new IllegalArgumentException("Unsupported Compose font scale: " + requestedScale);
        }

        if (FONT_SCALE_READ_OFFSET < 0
                || FONT_SCALE_READ_OFFSET + STOCK_FONT_SCALE_READ.length > stockDex.length) {
            throw new IllegalStateException("Spotify 9.1 Compose font-scale target is outside classes2.dex");
        }
        byte[] actual = Arrays.copyOfRange(stockDex, FONT_SCALE_READ_OFFSET,
                FONT_SCALE_READ_OFFSET + STOCK_FONT_SCALE_READ.length);
        if (!Arrays.equals(actual, STOCK_FONT_SCALE_READ)) {
            throw new IllegalStateException(
                    "Spotify 9.1 Compose font-scale signature mismatch at 0x"
                            + Integer.toHexString(FONT_SCALE_READ_OFFSET));
        }

        // const/high16 keeps the replacement exactly the same 2 code units as iget.
        // Use the nearest high-half float: 1.20 -> 1.203125, 1.40 -> 1.3984375,
        // 1.60 -> 1.6015625.
        int bits = Float.floatToIntBits(requestedScale);
        int high16 = ((bits + 0x8000) >>> 16) & 0xffff;

        byte[] out = stockDex.clone();
        out[FONT_SCALE_READ_OFFSET] = 0x15;       // const/high16 v0, #BBBB0000
        out[FONT_SCALE_READ_OFFSET + 1] = 0x00;  // v0
        out[FONT_SCALE_READ_OFFSET + 2] = (byte) (high16 & 0xff);
        out[FONT_SCALE_READ_OFFSET + 3] = (byte) ((high16 >>> 8) & 0xff);
        return DexUtil.repair(out);
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
