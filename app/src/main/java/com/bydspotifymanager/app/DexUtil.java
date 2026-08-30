package com.bydspotifymanager.app;

import java.security.MessageDigest;
import java.util.zip.Adler32;

final class DexUtil {
    private DexUtil() {}

    static byte[] repair(byte[] dex) throws Exception {
        if (dex.length < 32 || dex[0] != 'd' || dex[1] != 'e' || dex[2] != 'x') return dex;
        byte[] out = dex.clone();
        MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
        sha1.update(out, 32, out.length - 32);
        byte[] sig = sha1.digest();
        System.arraycopy(sig, 0, out, 12, 20);
        Adler32 adler = new Adler32();
        adler.update(out, 12, out.length - 12);
        long v = adler.getValue();
        out[8] = (byte)(v & 0xff);
        out[9] = (byte)((v >>> 8) & 0xff);
        out[10] = (byte)((v >>> 16) & 0xff);
        out[11] = (byte)((v >>> 24) & 0xff);
        return out;
    }
}
