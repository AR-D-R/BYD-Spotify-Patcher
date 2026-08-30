package com.bydspotifymanager.app;

import java.io.*;
import java.security.MessageDigest;

final class IoUtil {
    private IoUtil() {}

    static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] buf = new byte[1024 * 1024];
        int n;
        while ((n = in.read(buf)) != -1) {
            if (n > 0) out.write(buf, 0, n);
        }
    }

    static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        copy(in, out);
        return out.toByteArray();
    }

    static String sha256(File f) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new BufferedInputStream(new FileInputStream(f))) {
            byte[] buf = new byte[1024 * 1024];
            int n;
            while ((n = in.read(buf)) != -1) md.update(buf, 0, n);
        }
        StringBuilder sb = new StringBuilder();
        for (byte b : md.digest()) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    static byte[] replaceSameLength(byte[] input, byte[] from, byte[] to) {
        if (from.length != to.length) throw new IllegalArgumentException("Replacement length mismatch");
        byte[] out = input.clone();
        outer: for (int i = 0; i <= out.length - from.length; i++) {
            for (int j = 0; j < from.length; j++) {
                if (out[i + j] != from[j]) continue outer;
            }
            System.arraycopy(to, 0, out, i, to.length);
            i += from.length - 1;
        }
        return out;
    }
}
