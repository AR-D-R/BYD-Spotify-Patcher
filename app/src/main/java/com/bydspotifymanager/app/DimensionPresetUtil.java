package com.bydspotifymanager.app;

import android.content.Context;

import java.io.DataInputStream;
import java.io.InputStream;

final class DimensionPresetUtil {
    private DimensionPresetUtil() {}

    static int apply(Context context, byte[] resourceTable, String assetPath) throws Exception {
        int changed = 0;
        try (InputStream raw = context.getAssets().open(assetPath);
             DataInputStream in = new DataInputStream(raw)) {
            int count = readLeInt(in);
            for (int i = 0; i < count; i++) {
                int offset = readLeInt(in);
                int value = readLeInt(in);
                if (offset < 0 || offset + 4 > resourceTable.length) {
                    throw new IllegalStateException("Dimension map offset outside resources.arsc: " + offset);
                }
                int old = (resourceTable[offset] & 0xff)
                        | ((resourceTable[offset + 1] & 0xff) << 8)
                        | ((resourceTable[offset + 2] & 0xff) << 16)
                        | (resourceTable[offset + 3] << 24);
                if (old != value) {
                    resourceTable[offset] = (byte) value;
                    resourceTable[offset + 1] = (byte) (value >>> 8);
                    resourceTable[offset + 2] = (byte) (value >>> 16);
                    resourceTable[offset + 3] = (byte) (value >>> 24);
                    changed++;
                }
            }
        }
        return changed;
    }

    private static int readLeInt(DataInputStream in) throws Exception {
        int b0 = in.readUnsignedByte();
        int b1 = in.readUnsignedByte();
        int b2 = in.readUnsignedByte();
        int b3 = in.readUnsignedByte();
        return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
    }
}
