package com.bydspotifymanager.app;

import android.content.Context;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

/** Spotify 8.9.76.538 patch engine. */
final class ApkPatchEngine89 {
    interface Progress { void onProgress(String message); }
    static final String VERSION="8.9.76.538";
    static final long VERSION_CODE=119017142L;

    static final class Validation {
        final boolean ok; final String detail;
        Validation(boolean ok,String detail){this.ok=ok;this.detail=detail;}
    }

    private ApkPatchEngine89(){}

    static Validation validateSource(File apk) {
        try (ZipFile z=new ZipFile(apk)) {
            String[] required={"AndroidManifest.xml","resources.arsc","classes.dex",Spotify89PanelUtil.WIDE_LAYOUT_PATH};
            for(String n:required) if(z.getEntry(n)==null)return new Validation(false,"Missing required Spotify 8.9 entry: "+n);
            byte[] manifest=IoUtil.readAll(z.getInputStream(z.getEntry("AndroidManifest.xml")));
            if(!Spotify89ManifestUtil.isOriginalPackage(manifest))return new Validation(false,"Selected APK is not an original com.spotify.music package.");
            Spotify89ManifestUtil.VersionInfo vi=Spotify89ManifestUtil.versionInfo(manifest);
            if(!VERSION.equals(vi.name)||vi.code!=VERSION_CODE)return new Validation(false,"Expected Spotify "+VERSION+" ("+VERSION_CODE+") but found "+vi.name+" ("+vi.code+").");
            Spotify89ManifestUtil.PortraitResult mr=Spotify89ManifestUtil.patchPortraitOrientations(manifest);
            if(mr.count!=12)return new Validation(false,"Spotify 8.9 portrait-lock profile mismatch: expected 12, found "+mr.count+".");
            List<String> ms=Spotify89ManifestUtil.scanStrings(manifest);
            if(!ms.contains("com.spotify.connect.mediarouteprovider.SpotifyMediaRouteProviderService")||!ms.contains("android.media.MediaRoute2ProviderService")||!ms.contains("foregroundServiceType"))return new Validation(false,"Spotify 8.9 auto-resume service slot was not found.");

            byte[] resources=IoUtil.readAll(z.getInputStream(z.getEntry("resources.arsc")));
            if(count(resources,Spotify89ResourceUtil.RESOURCE_AUTHORITY_OLD.getBytes(StandardCharsets.US_ASCII))==0)return new Validation(false,"Spotify 8.9 media API provider authority was not found.");
            Spotify89ResourceUtil.validateProfile(resources);

            byte[] wide=IoUtil.readAll(z.getInputStream(z.getEntry(Spotify89PanelUtil.WIDE_LAYOUT_PATH)));
            if(!Spotify89PanelUtil.BASE_SHA256.equalsIgnoreCase(sha256(wide)))return new Validation(false,"Spotify 8.9 wide-screen layout does not match the supported build.");
            for(String p:Spotify89BrandingUtil.DENSITY_ICONS)if(z.getEntry(p)==null)return new Validation(false,"Spotify 8.9 launcher icon resource missing: "+p);
            if(z.getEntry(Spotify89ResourceUtil.OLD_ADAPTIVE_FOREGROUND_PATH)==null)return new Validation(false,"Spotify 8.9 adaptive launcher foreground is missing.");

            int dexCount=0, orientationHits=0, pkgHits=0;
            for(Enumeration<? extends ZipEntry> en=z.entries();en.hasMoreElements();){ZipEntry e=en.nextElement();String n=e.getName();if(n.matches("classes(\\d+)?\\.dex")){dexCount++;byte[] d=IoUtil.readAll(z.getInputStream(e));Spotify89DexUtil.PatchResult pr=Spotify89DexUtil.patchPackage(d,BuildConfigData.V89_PRIMARY_PACKAGE);pkgHits+=pr.count;orientationHits+=Spotify89DexUtil.patchRuntimePortraitRequests(d).count;}}
            if(dexCount!=7||z.getEntry("classes8.dex")!=null||z.getEntry("classes9.dex")!=null)return new Validation(false,"Expected stock Spotify 8.9 seven-DEX layout; found "+dexCount+" DEX files.");
            if(pkgHits<=0)return new Validation(false,"No exact com.spotify.music process/package DEX marker was found.");
            if(orientationHits!=3)return new Validation(false,"Spotify 8.9 runtime portrait profile mismatch: expected 3, found "+orientationHits+".");
            return new Validation(true,"Verified original Spotify "+VERSION);
        } catch(Exception e){return new Validation(false,e.getClass().getSimpleName()+": "+e.getMessage());}
    }

    static File build(Context context, File sourceApk, File output, boolean secondary, String appName,
                      Spotify89ResourceUtil.FontPreset fontPreset, boolean rightPanel, boolean preventPortrait,
                      int iconHue, boolean iconBadge, Progress progress) throws Exception {
        String targetPackage=secondary?BuildConfigData.V89_SECONDARY_PACKAGE:BuildConfigData.V89_PRIMARY_PACKAGE;
        String clean=appName==null?"":appName.trim(); if(clean.isEmpty())clean=secondary?"SpotifyPlus2":"SpotifyPlus";
        if(clean.codePointCount(0,clean.length())>24)throw new IllegalArgumentException("Spotify 8.9 app name can be up to 24 characters.");
        boolean modifyIcon=iconBadge||IconBrandingUtil.normaliseHue(iconHue)!=0;

        Validation validation=validateSource(sourceApk); if(!validation.ok)throw new IllegalArgumentException(validation.detail);
        progress.onProgress("Spotify 8.9 source profile verified.");

        try(ZipFile zin=new ZipFile(sourceApk)){
            byte[] manifest=IoUtil.readAll(zin.getInputStream(zin.getEntry("AndroidManifest.xml")));
            manifest=Spotify89ManifestUtil.patchIdentity(manifest,targetPackage);
            manifest=Spotify89ManifestUtil.patchAutoResume(manifest,targetPackage);
            if(preventPortrait){Spotify89ManifestUtil.PortraitResult pr=Spotify89ManifestUtil.patchPortraitOrientations(manifest);if(pr.count!=12)throw new IllegalArgumentException("Expected 12 manifest portrait locks, patched "+pr.count);manifest=pr.data;progress.onProgress("8.9 portrait locks removed from manifest.");}

            byte[] resources=IoUtil.readAll(zin.getInputStream(zin.getEntry("resources.arsc")));
            resources=Spotify89ResourceUtil.patchIdentityAuthority(resources,targetPackage);
            resources=Spotify89ResourceUtil.patchUi(resources,fontPreset);
            Spotify89ResourceUtil.BrandingResult br=Spotify89ResourceUtil.patchBranding(resources,clean,modifyIcon);resources=br.resources;
            progress.onProgress("8.9 BYD layout + "+fontPreset.name().toLowerCase(Locale.ROOT)+" font profile applied.");

            byte[] wide=IoUtil.readAll(zin.getInputStream(zin.getEntry(Spotify89PanelUtil.WIDE_LAYOUT_PATH)));
            if(rightPanel){wide=Spotify89PanelUtil.patchRight(wide,targetPackage);progress.onProgress("8.9 Right/RHD panel transform applied.");} else progress.onProgress("8.9 Left/LHD panel kept on stock side.");

            Map<String,byte[]> brandedIcons=new HashMap<>(); byte[] adaptivePng=null;
            if(modifyIcon){
                for(String p:Spotify89BrandingUtil.DENSITY_ICONS){byte[] raw=IoUtil.readAll(zin.getInputStream(zin.getEntry(p)));brandedIcons.put(p,Spotify89BrandingUtil.brandDensityIcon(raw,iconHue,iconBadge));}
                byte[] xxx=IoUtil.readAll(zin.getInputStream(zin.getEntry(Spotify89BrandingUtil.DENSITY_ICONS[Spotify89BrandingUtil.DENSITY_ICONS.length-1])));
                adaptivePng=Spotify89BrandingUtil.buildAdaptiveForeground(xxx,iconHue,iconBadge);
            }

            byte[] autoDex=Spotify89DexUtil.retargetHelperDex(IoUtil.readAll(context.getAssets().open("spotify89/auto_resume.dex")),targetPackage);
            byte[] ltrDex=rightPanel?Spotify89DexUtil.retargetHelperDex(IoUtil.readAll(context.getAssets().open("spotify89/ltr_frame.dex")),targetPackage):null;
            int pkgChanges=0,orientationChanges=0;

            try(CountingOutputStream counted=new CountingOutputStream(new FileOutputStream(output));
                ZipOutputStream zout=new ZipOutputStream(counted)){
                for(Enumeration<? extends ZipEntry> en=zin.entries();en.hasMoreElements();){
                    ZipEntry src=en.nextElement();String name=src.getName();
                    if(isV1Signature(name))continue;
                    if(modifyIcon&&Spotify89ResourceUtil.OLD_ADAPTIVE_FOREGROUND_PATH.equals(name))continue;
                    byte[] data;
                    if("AndroidManifest.xml".equals(name))data=manifest;
                    else if("resources.arsc".equals(name))data=resources;
                    else if(Spotify89PanelUtil.WIDE_LAYOUT_PATH.equals(name))data=wide;
                    else if(brandedIcons.containsKey(name))data=brandedIcons.get(name);
                    else {data=IoUtil.readAll(zin.getInputStream(src)); if(name.matches("classes(\\d+)?\\.dex")){Spotify89DexUtil.PatchResult p=Spotify89DexUtil.patchPackage(data,targetPackage);data=p.data;pkgChanges+=p.count;if(preventPortrait){Spotify89DexUtil.PatchResult q=Spotify89DexUtil.patchRuntimePortraitRequests(data);data=q.data;orientationChanges+=q.count;}}}
                    writeEntry(zout,counted.count,src,data);
                }
                if(modifyIcon&&adaptivePng!=null)writeAdded(zout,Spotify89ResourceUtil.NEW_ADAPTIVE_FOREGROUND_PATH,adaptivePng);
                if(rightPanel){writeAdded(zout,"classes8.dex",ltrDex);writeAdded(zout,"classes9.dex",autoDex);}else writeAdded(zout,"classes8.dex",autoDex);
            }
            if(pkgChanges<=0){output.delete();throw new IllegalArgumentException("No Spotify 8.9 DEX package markers were patched.");}
            if(preventPortrait&&orientationChanges!=3){output.delete();throw new IllegalArgumentException("Expected 3 runtime portrait requests, patched "+orientationChanges);}
        }
        verifyOutput(sourceApk, output, targetPackage, clean, rightPanel, preventPortrait, modifyIcon);
        progress.onProgress("Spotify 8.9 clone verified for "+targetPackage+".");
        return output;
    }

    private static boolean isV1Signature(String name){String u=name.toUpperCase(Locale.ROOT);if("META-INF/MANIFEST.MF".equals(u))return true;return u.matches("META-INF/[^/]+\\.(SF|RSA|DSA|EC)");}

    private static final class CountingOutputStream extends FilterOutputStream {
        long count;
        CountingOutputStream(OutputStream out){super(out);}
        @Override public void write(int b)throws IOException{out.write(b);count++;}
        @Override public void write(byte[]b,int off,int len)throws IOException{out.write(b,off,len);count+=len;}
    }

    private static void writeAdded(ZipOutputStream z,String name,byte[]data)throws IOException{
        ZipEntry e=new ZipEntry(name);e.setMethod(ZipEntry.DEFLATED);z.putNextEntry(e);z.write(data);z.closeEntry();
    }

    /** Preserve 4-byte alignment for uncompressed APK entries. */
    private static void writeEntry(ZipOutputStream z,long currentOffset,ZipEntry t,byte[]data)throws IOException{
        ZipEntry e=new ZipEntry(t.getName());
        e.setTime(t.getTime()); e.setComment(t.getComment());
        byte[] extra=t.getExtra(); if(extra==null)extra=new byte[0]; else extra=extra.clone();
        int m=t.getMethod();if(m!=ZipEntry.STORED&&m!=ZipEntry.DEFLATED)m=ZipEntry.DEFLATED;e.setMethod(m);
        if(m==ZipEntry.STORED){
            byte[] name=e.getName().getBytes(StandardCharsets.UTF_8);
            long base=currentOffset+30L+name.length+extra.length;
            int needed=(int)((-base)&3L);
            if(needed!=0){
                byte[] aligned=Arrays.copyOf(extra,extra.length+4+needed);int p=extra.length;
                aligned[p]=(byte)0x35;aligned[p+1]=(byte)0xD9;aligned[p+2]=(byte)needed;aligned[p+3]=0;
                extra=aligned;
            }
            CRC32 c=new CRC32();c.update(data);e.setSize(data.length);e.setCompressedSize(data.length);e.setCrc(c.getValue());
        }
        if(extra.length>0)e.setExtra(extra);
        z.putNextEntry(e);z.write(data);z.closeEntry();
    }

    private static void verifyOutput(File source,File output,String targetPackage,String appLabel,boolean rightPanel,boolean preventPortrait,boolean modifiedIcon)throws Exception{
        if(!output.isFile()||output.length()<1024)throw new IOException("Spotify 8.9 output APK was not created correctly");
        try(ZipFile src=new ZipFile(source);ZipFile out=new ZipFile(output)){
            // Preserve Java/service-loader metadata exactly; only obsolete v1 signatures are removed.
            Map<String,String> srcServices=serviceHashes(src),outServices=serviceHashes(out);
            if(!srcServices.equals(outServices))throw new IllegalArgumentException("META-INF/services runtime files were not preserved exactly");

            ZipEntry me=out.getEntry("AndroidManifest.xml");if(me==null)throw new IllegalArgumentException("Output manifest missing");
            byte[] manifest=IoUtil.readAll(out.getInputStream(me));List<String> ms=Spotify89ManifestUtil.scanStrings(manifest);
            if(!ms.contains(targetPackage))throw new IllegalArgumentException("8.9 output package identity verification failed");
            if(ms.contains(Spotify89ManifestUtil.OLD_PACKAGE))throw new IllegalArgumentException("Old com.spotify.music manifest identity remains");
            if(!ms.contains(targetPackage+".AutoResumeService")||!ms.contains("byd.intent.action.RESTORE_PLAYBACK"))throw new IllegalArgumentException("8.9 AutoResume manifest verification failed");
            if(preventPortrait&&Spotify89ManifestUtil.patchPortraitOrientations(manifest).count!=0)throw new IllegalArgumentException("Explicit 8.9 portrait manifest locks remain");

            ZipEntry re=out.getEntry("resources.arsc");if(re==null)throw new IllegalArgumentException("Output resources.arsc missing");
            byte[] resources=IoUtil.readAll(out.getInputStream(re));Spotify89BinaryUtil.Pool gp=Spotify89BinaryUtil.parsePool(resources,Spotify89BinaryUtil.u16(resources,2));
            if(!gp.strings.contains(appLabel))throw new IllegalArgumentException("8.9 app label verification failed");
            if(modifiedIcon&&!gp.strings.contains(Spotify89ResourceUtil.NEW_ADAPTIVE_FOREGROUND_PATH))throw new IllegalArgumentException("8.9 launcher branding verification failed");
            if(!modifiedIcon&&out.getEntry(Spotify89ResourceUtil.OLD_ADAPTIVE_FOREGROUND_PATH)==null)throw new IllegalArgumentException("Original 8.9 launcher foreground was not preserved");

            byte[] sourceWide=IoUtil.readAll(src.getInputStream(src.getEntry(Spotify89PanelUtil.WIDE_LAYOUT_PATH)));
            byte[] expectedWide=rightPanel?Spotify89PanelUtil.patchRight(sourceWide,targetPackage):sourceWide;
            byte[] actualWide=IoUtil.readAll(out.getInputStream(out.getEntry(Spotify89PanelUtil.WIDE_LAYOUT_PATH)));
            if(!Arrays.equals(expectedWide,actualWide))throw new IllegalArgumentException("8.9 wide-screen layout verification failed");

            int dexCount=0;
            for(Enumeration<? extends ZipEntry> en=out.entries();en.hasMoreElements();){
                ZipEntry e=en.nextElement();String n=e.getName();if(!n.matches("classes(\\d+)?\\.dex"))continue;dexCount++;
                byte[] d=IoUtil.readAll(out.getInputStream(e));if(!Arrays.equals(d,DexUtil.repair(d)))throw new IllegalArgumentException("DEX checksum verification failed: "+n);
                if(n.matches("classes[1-7]?\\.dex")&&Spotify89DexUtil.patchPackage(d,targetPackage).count!=0)throw new IllegalArgumentException("Old exact com.spotify.music DEX marker remains: "+n);
                if(preventPortrait&&Spotify89DexUtil.patchRuntimePortraitRequests(d).count!=0)throw new IllegalArgumentException("Runtime portrait request remains: "+n);
            }
            int expectedDex=rightPanel?9:8;if(dexCount!=expectedDex)throw new IllegalArgumentException("Expected "+expectedDex+" output DEX files, found "+dexCount);
        }
    }

    private static Map<String,String> serviceHashes(ZipFile z)throws Exception{
        Map<String,String> m=new TreeMap<>();for(Enumeration<? extends ZipEntry> en=z.entries();en.hasMoreElements();){ZipEntry e=en.nextElement();if(e.getName().startsWith("META-INF/services/"))m.put(e.getName(),sha256(IoUtil.readAll(z.getInputStream(e))));}return m;
    }

    private static String sha256(byte[]data)throws Exception{MessageDigest md=MessageDigest.getInstance("SHA-256");byte[]h=md.digest(data);StringBuilder s=new StringBuilder();for(byte b:h)s.append(String.format(Locale.ROOT,"%02x",b));return s.toString();}
    private static int count(byte[]h,byte[]n){int c=0;for(int i=0;i+n.length<=h.length;){boolean ok=true;for(int j=0;j<n.length;j++)if(h[i+j]!=n[j]){ok=false;break;}if(ok){c++;i+=n.length;}else i++;}return c;}
}
