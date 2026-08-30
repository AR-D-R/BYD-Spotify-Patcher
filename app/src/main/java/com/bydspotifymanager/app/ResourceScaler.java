package com.bydspotifymanager.app;

import android.util.TypedValue;

final class ResourceScaler {
    private static final int RES_TABLE_TYPE = 0x0002;
    private static final int RES_TABLE_PACKAGE_TYPE = 0x0200;
    private static final int RES_TABLE_TYPE_TYPE = 0x0201;
    private static final int RES_XML_TYPE = 0x0003;
    private static final int RES_XML_START_ELEMENT_TYPE = 0x0102;
    private static final int TYPE_DIMENSION = 0x05;
    private static final int ENTRY_FLAG_COMPLEX = 0x0001;
    private static final int TYPE_FLAG_SPARSE = 0x01;
    private static final int TYPE_FLAG_OFFSET16 = 0x02;

    // Keep large screen/container geometry unchanged. Normal controls, rows, cards,
    // tiles, icon sizes, padding/gaps and text are scaled.
    private static final float MAX_DIP_TO_SCALE = 320f;
    private static final float MAX_SP_TO_SCALE = 128f;
    // Both dp and sp values use the selected factor. The stock baseline is restored first,
    // including dimensions embedded inside TextAppearance/style resources, so every preset means
    // the selected percentage of the original Spotify value rather than 140% of an already enlarged v16 value.

    private ResourceScaler() {}

    static int scaleResourceTable(byte[] data, float factor) {
        if (factor == 1f || data.length < 12 || u16(data, 0) != RES_TABLE_TYPE) return 0;
        int total = boundedSize(data, 0);
        int pos = u16(data, 2);
        int changed = 0;
        while (pos + 8 <= total) {
            int type = u16(data, pos);
            int size = boundedSize(data, pos);
            if (size < 8 || pos + size > total) break;
            if (type == RES_TABLE_PACKAGE_TYPE) changed += scalePackage(data, pos, size, factor);
            pos += size;
        }
        return changed;
    }

    private static int scalePackage(byte[] data, int start, int size, float factor) {
        int end = start + size;
        int pos = start + u16(data, start + 2);
        int changed = 0;
        while (pos + 8 <= end) {
            int type = u16(data, pos);
            int childSize = boundedSize(data, pos);
            if (childSize < 8 || pos + childSize > end) break;
            if (type == RES_TABLE_TYPE_TYPE) changed += scaleTypeChunk(data, pos, childSize, factor);
            pos += childSize;
        }
        return changed;
    }

    private static int scaleTypeChunk(byte[] data, int start, int size, float factor) {
        if (start + 20 > data.length) return 0;
        int headerSize = u16(data, start + 2);
        int flags = data[start + 9] & 0xff;
        int entryCount = i32(data, start + 12);
        int entriesStart = i32(data, start + 16);
        if (headerSize < 20 || entryCount < 0 || entriesStart < headerSize || entriesStart >= size) return 0;
        int changed = 0;

        if ((flags & TYPE_FLAG_SPARSE) != 0) {
            int p = start + headerSize;
            for (int i = 0; i < entryCount && p + 4 <= start + size; i++, p += 4) {
                int offUnits = u16(data, p + 2);
                int off = offUnits * 4;
                changed += scaleEntry(data, start + entriesStart + off, start + size, factor);
            }
        } else if ((flags & TYPE_FLAG_OFFSET16) != 0) {
            int p = start + headerSize;
            for (int i = 0; i < entryCount && p + 2 <= start + size; i++, p += 2) {
                int offUnits = u16(data, p);
                if (offUnits == 0xffff) continue;
                changed += scaleEntry(data, start + entriesStart + offUnits * 4, start + size, factor);
            }
        } else {
            int p = start + headerSize;
            for (int i = 0; i < entryCount && p + 4 <= start + size; i++, p += 4) {
                int off = i32(data, p);
                if (off == -1) continue;
                changed += scaleEntry(data, start + entriesStart + off, start + size, factor);
            }
        }
        return changed;
    }

    private static int scaleEntry(byte[] data, int entry, int end, float factor) {
        if (entry < 0 || entry + 8 > end || entry + 8 > data.length) return 0;
        int entrySize = u16(data, entry);
        int flags = u16(data, entry + 2);
        if (entrySize < 8 || entry + entrySize > end) return 0;
        int changed = 0;
        if ((flags & ENTRY_FLAG_COMPLEX) != 0) {
            if (entry + 16 > end) return 0;
            int count = i32(data, entry + 12);
            int p = entry + entrySize;
            for (int i = 0; i < count && p + 12 <= end; i++, p += 12) {
                changed += scaleResValue(data, p + 4, factor);
            }
        } else {
            changed += scaleResValue(data, entry + entrySize, factor);
        }
        return changed;
    }

    static int scaleBinaryXml(byte[] data, float factor) {
        if (factor == 1f || data.length < 8 || u16(data, 0) != RES_XML_TYPE) return 0;
        int total = boundedSize(data, 0);
        int pos = u16(data, 2);
        int changed = 0;
        while (pos + 8 <= total) {
            int type = u16(data, pos);
            int size = boundedSize(data, pos);
            if (size < 8 || pos + size > total) break;
            if (type == RES_XML_START_ELEMENT_TYPE && pos + 36 <= total) {
                int ext = pos + 16;
                int attrStart = u16(data, ext + 8);
                int attrSize = u16(data, ext + 10);
                int attrCount = u16(data, ext + 12);
                if (attrSize >= 20) {
                    int p = ext + attrStart;
                    for (int i = 0; i < attrCount && p + attrSize <= pos + size; i++, p += attrSize) {
                        changed += scaleResValue(data, p + 12, factor);
                    }
                }
            }
            pos += size;
        }
        return changed;
    }

    private static int scaleResValue(byte[] data, int valueOff, float factor) {
        if (valueOff < 0 || valueOff + 8 > data.length || u16(data, valueOff) < 8) return 0;
        if ((data[valueOff + 3] & 0xff) != TYPE_DIMENSION) return 0;
        int complex = i32(data, valueOff + 4);
        int unit = complex & TypedValue.COMPLEX_UNIT_MASK;
        float value = TypedValue.complexToFloat(complex);
        float abs = Math.abs(value);
        boolean scale;
        if (unit == TypedValue.COMPLEX_UNIT_SP) {
            scale = abs > 0.01f && abs <= MAX_SP_TO_SCALE;
        } else if (unit == TypedValue.COMPLEX_UNIT_DIP) {
            scale = abs > 0.01f && abs <= MAX_DIP_TO_SCALE;
        } else {
            scale = false;
        }
        if (!scale) return 0;

        int mantissa = complex & 0xffffff00;
        long scaled = Math.round((mantissa * (double) factor) / 256.0) * 256L;
        if (scaled > 0x7fffff00L) scaled = 0x7fffff00L;
        if (scaled < -0x80000000L) scaled = -0x80000000L;
        int newComplex = ((int) scaled & 0xffffff00) | (complex & 0xff);
        if (newComplex == complex) return 0;
        putI32(data, valueOff + 4, newComplex);
        return 1;
    }

    private static int boundedSize(byte[] data, int off) {
        long size = u32(data, off + 4);
        if (size < 0 || size > Integer.MAX_VALUE) return 0;
        return (int) size;
    }

    private static int u16(byte[] b, int o) {
        return (b[o] & 0xff) | ((b[o + 1] & 0xff) << 8);
    }

    private static int i32(byte[] b, int o) {
        return (b[o] & 0xff) | ((b[o + 1] & 0xff) << 8) | ((b[o + 2] & 0xff) << 16) | (b[o + 3] << 24);
    }

    private static long u32(byte[] b, int o) {
        return i32(b, o) & 0xffffffffL;
    }

    private static void putI32(byte[] b, int o, int v) {
        b[o] = (byte) v;
        b[o + 1] = (byte) (v >>> 8);
        b[o + 2] = (byte) (v >>> 16);
        b[o + 3] = (byte) (v >>> 24);
    }
}
