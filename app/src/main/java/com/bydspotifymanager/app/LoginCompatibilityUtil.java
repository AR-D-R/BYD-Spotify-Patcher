package com.bydspotifymanager.app;


/**
 * Spotify 9.1.78.2215 clone-login compatibility.
 *
 * The stock login flow gates the email one-time-code path behind the
 * android-feature-login:email_otp_login_enabled remote-config property.
 * Cloned/resigned installs can otherwise fall back to the password path,
 * which is not usable in the tested BYD configuration.
 *
 * This exact-version patch changes the generated property getter p.lw3.e():Z
 * to return true. The byte signature is deliberately strict and must match
 * exactly once; a different Spotify build fails closed instead of receiving
 * a speculative DEX edit.
 */
final class LoginCompatibilityUtil {
    private LoginCompatibilityUtil() {}

    // Instructions of p.lw3.e():Z in Spotify 9.1.78.2215 classes6.dex.
    // Keep the code_item itself unchanged in size; only the instruction body
    // is replaced, so all DEX indexes/offsets remain stable.
    private static final byte[] EMAIL_OTP_GETTER_STOCK = hex(
            "6e10b79001000c00380007006e10ba9000000a000f005510d16f0f00");

    // const/4 v0, #1 ; return v0 ; nop... (same 28-byte instruction body)
    private static final byte[] EMAIL_OTP_GETTER_FORCED = hex(
            "12100f00000000000000000000000000000000000000000000000000");

    static byte[] forceEmailOtpLogin(byte[] dex) throws Exception {
        int first = indexOf(dex, EMAIL_OTP_GETTER_STOCK, 0);
        if (first < 0) {
            // Allow idempotent rebuilding only if the forced signature exists exactly once.
            int forced = indexOf(dex, EMAIL_OTP_GETTER_FORCED, 0);
            if (forced >= 0 && indexOf(dex, EMAIL_OTP_GETTER_FORCED, forced + 1) < 0) {
                return dex;
            }
            throw new IllegalStateException("Spotify 9.1 email-code login signature was not found");
        }
        if (indexOf(dex, EMAIL_OTP_GETTER_STOCK, first + 1) >= 0) {
            throw new IllegalStateException("Spotify 9.1 email-code login signature is ambiguous");
        }
        byte[] out = dex.clone();
        System.arraycopy(EMAIL_OTP_GETTER_FORCED, 0, out, first, EMAIL_OTP_GETTER_FORCED.length);
        return DexUtil.repair(out);
    }

    private static int indexOf(byte[] haystack, byte[] needle, int from) {
        if (needle.length == 0) return Math.max(0, from);
        outer:
        for (int i = Math.max(0, from); i <= haystack.length - needle.length; i++) {
            for (int j = 0; j < needle.length; j++) {
                if (haystack[i + j] != needle[j]) continue outer;
            }
            return i;
        }
        return -1;
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
