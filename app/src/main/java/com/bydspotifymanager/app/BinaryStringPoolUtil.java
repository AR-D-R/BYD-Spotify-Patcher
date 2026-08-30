package com.bydspotifymanager.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Small, version-safe binary Android string-pool editor used only for known Spotify 9.1.78 resources. */
final class BinaryStringPoolUtil {
    private static final int STRING_POOL_TYPE = 0x0001;
    private static final int UTF8_FLAG = 0x00000100;

    private BinaryStringPoolUtil() {}

    static byte[] replaceFirstString(byte[] container, String oldValue, String newValue) {
        return rebuild(container, oldValue, null, newValue, false);
    }

    static byte[] appendToFirstStringStartingWith(byte[] container, String prefix, String suffix) {
        return rebuild(container, null, prefix, suffix, true);
    }

    private static byte[] rebuild(byte[] container, String exact, String prefix, String value, boolean append) {
        if (container == null || container.length < 12) return container;
        int outerHeader = u16(container, 2);
        int pool = outerHeader;
        while (pool + 8 <= container.length) {
            int type = u16(container, pool);
            int size = i32(container, pool + 4);
            if (size < 8 || pool + size > container.length) return container;
            if (type == STRING_POOL_TYPE) break;
            pool += size;
        }
        if (pool + 28 > container.length || u16(container, pool) != STRING_POOL_TYPE) return container;

        int headerSize = u16(container, pool + 2);
        int poolSize = i32(container, pool + 4);
        int stringCount = i32(container, pool + 8);
        int styleCount = i32(container, pool + 12);
        int flags = i32(container, pool + 16);
        int stringsStart = i32(container, pool + 20);
        int stylesStart = i32(container, pool + 24);
        if (headerSize < 28 || stringCount < 0 || stringsStart < headerSize || pool + poolSize > container.length) return container;

        boolean utf8 = (flags & UTF8_FLAG) != 0;
        int offsetsStart = pool + headerSize;
        if (offsetsStart + stringCount * 4L + styleCount * 4L > pool + stringsStart) return container;
        int oldStringEndRel = stylesStart != 0 ? stylesStart : poolSize;
        if (oldStringEndRel < stringsStart || oldStringEndRel > poolSize) return container;

        int match = -1;
        String replacement = null;
        for (int i = 0; i < stringCount; i++) {
            int rel = i32(container, offsetsStart + i * 4);
            String decoded = decode(container, pool + stringsStart + rel, utf8);
            boolean ok = exact != null ? exact.equals(decoded) : decoded != null && decoded.startsWith(prefix);
            if (ok) {
                match = i;
                replacement = append ? decoded + value : value;
                break;
            }
        }
        if (match < 0 || replacement == null) return container;

        // SpotifyPlus9 is intentionally stored as the final value string in the supported
        // resources.arsc. Replace that tail in-place instead of rebuilding the huge global
        // pool (which contains shared/duplicate string offsets).
        if (exact != null && match == stringCount - 1) {
            int rel = i32(container, offsetsStart + match * 4);
            int stringAbs = pool + stringsStart + rel;
            int oldEncodedLen = encodedLength(container, stringAbs, utf8);
            int oldStylesAbs = stylesStart != 0 ? pool + stylesStart : pool + poolSize;
            if (stringAbs + oldEncodedLen <= oldStylesAbs) {
                byte[] encoded = encode(replacement, utf8);
                int newStylesRel = align4((stringAbs - pool) + encoded.length);
                int newStylesAbs = pool + newStylesRel;
                int delta = newStylesAbs - oldStylesAbs;
                byte[] out = new byte[container.length + delta];
                System.arraycopy(container, 0, out, 0, stringAbs);
                System.arraycopy(encoded, 0, out, stringAbs, encoded.length);
                // remaining bytes before newStylesAbs are zero padding
                System.arraycopy(container, oldStylesAbs, out, newStylesAbs, container.length - oldStylesAbs);
                putI32(out, pool + 4, poolSize + delta);
                if (stylesStart != 0) putI32(out, pool + 24, newStylesRel);
                putI32(out, 4, i32(container, 4) + delta);
                return out;
            }
        }

        ByteArrayOutputStream strings = new ByteArrayOutputStream(oldStringEndRel - stringsStart + 64);
        int[] newOffsets = new int[stringCount];
        for (int i = 0; i < stringCount; i++) {
            newOffsets[i] = strings.size();
            int rel = i32(container, offsetsStart + i * 4);
            int abs = pool + stringsStart + rel;
            if (i == match) {
                byte[] encoded = encode(replacement, utf8);
                strings.write(encoded, 0, encoded.length);
            } else {
                int len = encodedLength(container, abs, utf8);
                if (len <= 0 || abs + len > container.length) return container;
                strings.write(container, abs, len);
            }
        }
        while (((stringsStart + strings.size()) & 3) != 0) strings.write(0);

        int newStylesStart = styleCount > 0 ? stringsStart + strings.size() : 0;
        int oldStylesAbs = stylesStart != 0 ? pool + stylesStart : pool + poolSize;
        int styleBytes = pool + poolSize - oldStylesAbs;
        int newPoolSize = stringsStart + strings.size() + styleBytes;
        byte[] newPool = new byte[newPoolSize];
        System.arraycopy(container, pool, newPool, 0, stringsStart);
        putI32(newPool, 4, newPoolSize);
        putI32(newPool, 24, newStylesStart);
        for (int i = 0; i < stringCount; i++) putI32(newPool, headerSize + i * 4, newOffsets[i]);
        byte[] stringBytes = strings.toByteArray();
        System.arraycopy(stringBytes, 0, newPool, stringsStart, stringBytes.length);
        if (styleBytes > 0) System.arraycopy(container, oldStylesAbs, newPool, newStylesStart, styleBytes);

        int delta = newPoolSize - poolSize;
        byte[] out = new byte[container.length + delta];
        System.arraycopy(container, 0, out, 0, pool);
        System.arraycopy(newPool, 0, out, pool, newPool.length);
        System.arraycopy(container, pool + poolSize, out, pool + newPoolSize, container.length - (pool + poolSize));
        // Android XML/resource-table outer chunks both store total byte size at offset 4.
        putI32(out, 4, i32(container, 4) + delta);
        return out;
    }

    private static String decode(byte[] b, int p, boolean utf8) {
        try {
            if (utf8) {
                int[] a = readLen8(b, p); p = a[1];
                int[] n = readLen8(b, p); p = n[1];
                return new String(b, p, n[0], StandardCharsets.UTF_8);
            }
            int[] n = readLen16(b, p); p = n[1];
            return new String(b, p, n[0] * 2, StandardCharsets.UTF_16LE);
        } catch (Exception e) {
            return null;
        }
    }

    private static int encodedLength(byte[] b, int p, boolean utf8) {
        int start = p;
        if (utf8) {
            int[] chars = readLen8(b, p); p = chars[1];
            int[] bytes = readLen8(b, p); p = bytes[1];
            return (p - start) + bytes[0] + 1;
        }
        int[] chars = readLen16(b, p); p = chars[1];
        return (p - start) + chars[0] * 2 + 2;
    }

    private static byte[] encode(String s, boolean utf8) {
        ByteArrayOutputStream out = new ByteArrayOutputStream(s.length() * 3 + 8);
        if (utf8) {
            byte[] bytes = s.getBytes(StandardCharsets.UTF_8);
            writeLen8(out, s.length()); // UTF-16 code units, as required by Android's UTF-8 pool format.
            writeLen8(out, bytes.length);
            out.write(bytes, 0, bytes.length);
            out.write(0);
        } else {
            byte[] bytes = s.getBytes(StandardCharsets.UTF_16LE);
            writeLen16(out, s.length());
            out.write(bytes, 0, bytes.length);
            out.write(0); out.write(0);
        }
        return out.toByteArray();
    }

    private static int[] readLen8(byte[] b, int p) {
        int a = b[p++] & 0xff;
        if ((a & 0x80) != 0) return new int[]{((a & 0x7f) << 8) | (b[p++] & 0xff), p};
        return new int[]{a, p};
    }

    private static int[] readLen16(byte[] b, int p) {
        int a = u16(b, p); p += 2;
        if ((a & 0x8000) != 0) {
            int c = u16(b, p); p += 2;
            return new int[]{((a & 0x7fff) << 16) | c, p};
        }
        return new int[]{a, p};
    }

    private static void writeLen8(ByteArrayOutputStream out, int v) {
        if (v > 0x7f) { out.write(((v >> 8) & 0x7f) | 0x80); out.write(v & 0xff); }
        else out.write(v);
    }

    private static void writeLen16(ByteArrayOutputStream out, int v) {
        if (v > 0x7fff) {
            int hi = ((v >> 16) & 0x7fff) | 0x8000;
            out.write(hi & 0xff); out.write((hi >> 8) & 0xff);
            out.write(v & 0xff); out.write((v >> 8) & 0xff);
        } else {
            out.write(v & 0xff); out.write((v >> 8) & 0xff);
        }
    }

    private static int align4(int v) { return (v + 3) & ~3; }

    private static int u16(byte[] b, int o) { return (b[o] & 0xff) | ((b[o + 1] & 0xff) << 8); }
    private static int i32(byte[] b, int o) { return (b[o] & 0xff) | ((b[o+1]&0xff)<<8) | ((b[o+2]&0xff)<<16) | (b[o+3]<<24); }
    private static void putI32(byte[] b, int o, int v) { b[o]=(byte)v; b[o+1]=(byte)(v>>>8); b[o+2]=(byte)(v>>>16); b[o+3]=(byte)(v>>>24); }
}
