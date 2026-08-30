package com.bydspotifymanager.app;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Spotify 9.1.78.2215 large-screen LHS hook installer.
 *
 * v0.1.20 keeps Spotify's complete ConstraintLayout/state-machine geometry stock.
 * The runtime hook mirrors the MainLayout render coordinate system, then
 * counter-mirrors each direct child so its local content remains LTR. Because
 * Spotify's own player/navigation rectangles are animated inside that mirrored
 * parent coordinate system, both startup and collapsed/expanded animations run
 * directly on the LHS instead of completing on RHS and being translated later.
 *
 * The only XML edit is replacing the shared direct-child FrameLayout tag in
 * large_main.xml with a FrameLayout-compatible hook class. Only the hook instance
 * carrying display_cutout_placeholder_start activates. Its DEX is added separately
 * as classes15.dex only for LHS builds.
 */
final class PlayerPositionUtil {
    static final String LARGE_MAIN_PATH = "res/layout/large_main.xml";
    static final String HOOK_ASSET = "lhs_hook/classes.dex";
    static final String HOOK_DEX_ENTRY = "classes15.dex";
    private static final String FRAME_LAYOUT = "FrameLayout";
    private static final String HOOK_CLASS = "com.bydspotify.lhshook.LhsLayoutHook";

    private PlayerPositionUtil() {}

    static byte[] moveLargePlayerLeft(byte[] stockXml) {
        if (stockXml == null || stockXml.length < 64) {
            throw new IllegalArgumentException("large_main.xml is missing or truncated");
        }
        byte[] out = BinaryStringPoolUtil.replaceFirstString(stockXml, FRAME_LAYOUT, HOOK_CLASS);
        if (out == stockXml || Arrays.equals(out, stockXml)) {
            throw new IllegalStateException("Spotify 9.1 large_main.xml FrameLayout hook target was not found");
        }
        byte[] hook = HOOK_CLASS.getBytes(StandardCharsets.UTF_8);
        if (indexOf(out, hook) < 0) {
            throw new IllegalStateException("LHS runtime hook class was not written into large_main.xml");
        }
        // Exact supported layout has one shared FrameLayout string used by the two
        // cutout placeholders plus the navigation/IME inset placeholders. Replacing that one
        // pool entry intentionally subclasses all three; only the START cutout ID
        // activates the hook at runtime.
        if (indexOf(out, FRAME_LAYOUT.getBytes(StandardCharsets.UTF_8)) >= 0) {
            throw new IllegalStateException("Unexpected additional FrameLayout string in supported large_main.xml");
        }
        return out;
    }

    private static int indexOf(byte[] haystack, byte[] needle) {
        outer:
        for (int i = 0; i <= haystack.length - needle.length; i++) {
            for (int j = 0; j < needle.length; j++) {
                if (haystack[i + j] != needle[j]) continue outer;
            }
            return i;
        }
        return -1;
    }
}
