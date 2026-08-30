package com.bydspotifymanager.app;

import android.graphics.*;
import java.io.*;

/** Spotify 8.9 launcher branding using the same hue/+ badge visual treatment as the locked Spotify 9.1 profile. */
final class Spotify89BrandingUtil {
    static final String[] DENSITY_ICONS={
            "res/mipmap-mdpi-v4/ic_launcher_renaissance.webp",
            "res/mipmap-hdpi-v4/ic_launcher_renaissance.webp",
            "res/mipmap-xhdpi-v4/ic_launcher_renaissance.webp",
            "res/mipmap-xxhdpi-v4/ic_launcher_renaissance.webp",
            "res/mipmap-xxxhdpi-v4/ic_launcher_renaissance.webp"
    };
    private Spotify89BrandingUtil(){}
    static boolean isDensityIcon(String n){for(String s:DENSITY_ICONS)if(s.equals(n))return true;return false;}

    static byte[] brandDensityIcon(byte[] data,int hue,boolean badge)throws IOException{
        Bitmap src=BitmapFactory.decodeByteArray(data,0,data.length);if(src==null)throw new IOException("Cannot decode Spotify 8.9 launcher icon");
        Bitmap out=render(src,hue,badge);ByteArrayOutputStream bos=new ByteArrayOutputStream(data.length+2048);boolean ok=out.compress(Bitmap.CompressFormat.WEBP,100,bos);if(out!=src)out.recycle();src.recycle();if(!ok)throw new IOException("Cannot encode Spotify 8.9 launcher icon");return bos.toByteArray();
    }

    static byte[] buildAdaptiveForeground(byte[] xxxhdpi,int hue,boolean badge)throws IOException{
        Bitmap src=BitmapFactory.decodeByteArray(xxxhdpi,0,xxxhdpi.length);if(src==null)throw new IOException("Cannot decode Spotify 8.9 xxxhdpi icon");Bitmap branded=render(src,hue,badge);Bitmap scaled=Bitmap.createScaledBitmap(branded,240,240,true);Bitmap canvas=Bitmap.createBitmap(432,432,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(canvas);c.drawBitmap(scaled,(432-240)/2f,(432-240)/2f,null);ByteArrayOutputStream bos=new ByteArrayOutputStream();boolean ok=canvas.compress(Bitmap.CompressFormat.PNG,100,bos);if(branded!=src)branded.recycle();src.recycle();scaled.recycle();canvas.recycle();if(!ok)throw new IOException("Cannot encode Spotify 8.9 adaptive icon");return bos.toByteArray();
    }

    static Bitmap render(Bitmap stock,int hue,boolean badge){
        return IconBrandingUtil.renderPreview(stock,hue,badge);
    }
}
