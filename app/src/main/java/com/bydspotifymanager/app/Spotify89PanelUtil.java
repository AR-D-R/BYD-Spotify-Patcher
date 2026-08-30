package com.bydspotifymanager.app;

import java.util.*;

/** Spotify 8.9 Right/RHD adaptive-main transform. Left/LHD leaves stock layout untouched. */
final class Spotify89PanelUtil {
    static final String WIDE_LAYOUT_PATH="res/layout-w600dp-v13/adaptive_main.xml";
    static final String BASE_SHA256="9e25d64fdfd097a1fe544af86439fe674942911fc7f6a12a2ea99321a4a7027e";
    private Spotify89PanelUtil() {}

    static byte[] patchRight(byte[] data,String targetPackage){
        int rootHs=Spotify89BinaryUtil.u16(data,2); if(rootHs!=8)throw new IllegalArgumentException("Unexpected 8.9 adaptive_main root header");
        int poolOff=rootHs; Spotify89BinaryUtil.Pool meta=Spotify89BinaryUtil.parsePool(data,poolOff); List<String> old=meta.strings;
        String ltrClass=targetPackage+".LtrFrameLayout";
        if(old.contains("layoutDirection")||old.contains(ltrClass))throw new IllegalArgumentException("8.9 wide layout already RHS patched");
        int frameOld=old.indexOf("FrameLayout"); if(frameOld<0)throw new IllegalArgumentException("8.9 FrameLayout marker missing");
        int insert=8; List<String> neu=new ArrayList<>(old); neu.add(insert,"layoutDirection"); Map<Integer,Integer> mapping=new HashMap<>(); for(int i=0;i<old.size();i++)mapping.put(i,i>=insert?i+1:i);
        int frameNew=mapping.get(frameOld); neu.set(frameNew,ltrClass); byte[] newPool=Spotify89BinaryUtil.buildPool(neu,meta);

        int o=poolOff+meta.size; if(Spotify89BinaryUtil.u16(data,o)!=0x0180)throw new IllegalArgumentException("8.9 adaptive_main resource map missing");
        int hs=Spotify89BinaryUtil.u16(data,o+2), sz=Spotify89BinaryUtil.i32(data,o+4), count=(sz-hs)/4; if(count!=19)throw new IllegalArgumentException("Expected 19 adaptive_main resource IDs, found "+count);
        List<Integer> vals=new ArrayList<>(); for(int i=0;i<count;i++)vals.add(Spotify89BinaryUtil.i32(data,o+hs+4*i)); vals.add(insert,0x010103b2);
        byte[] rm=new byte[hs+4*vals.size()]; System.arraycopy(data,o,rm,0,hs); Spotify89BinaryUtil.put32(rm,4,rm.length); for(int i=0;i<vals.size();i++)Spotify89BinaryUtil.put32(rm,hs+4*i,vals.get(i)); o+=sz;

        List<byte[]> chunks=new ArrayList<>();
        while(o<data.length){
            int typ=Spotify89BinaryUtil.u16(data,o), csz=Spotify89BinaryUtil.i32(data,o+4); if(csz<8||o+csz>data.length)throw new IllegalArgumentException("Invalid adaptive_main XML chunk");
            byte[] c=Arrays.copyOfRange(data,o,o+csz);
            if(typ==0x0100||typ==0x0101){ for(int q:new int[]{16,20})Spotify89BinaryUtil.put32(c,q,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,q),mapping)); }
            else if(typ==0x0102){
                for(int q:new int[]{16,20})Spotify89BinaryUtil.put32(c,q,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,q),mapping));
                int attrStart=Spotify89BinaryUtil.u16(c,24), attrSize=Spotify89BinaryUtil.u16(c,26), attrCount=Spotify89BinaryUtil.u16(c,28), ap=16+attrStart;
                for(int i=0;i<attrCount;i++){int ao=ap+i*attrSize;for(int q:new int[]{0,4,8})Spotify89BinaryUtil.put32(c,ao+q,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,ao+q),mapping));if((c[ao+15]&0xff)==3)Spotify89BinaryUtil.put32(c,ao+16,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,ao+16),mapping));}
                String tag=neu.get(Spotify89BinaryUtil.i32(c,20)); Integer idVal=null; List<Attr> attrs=new ArrayList<>();
                for(int i=0;i<attrCount;i++){int ao=ap+i*attrSize,ni=Spotify89BinaryUtil.i32(c,ao+4),dt=c[ao+15]&0xff,dv=Spotify89BinaryUtil.i32(c,ao+16),raw=Spotify89BinaryUtil.i32(c,ao+8);String name=neu.get(ni);attrs.add(new Attr(name,ao,ni,dt,dv,raw));if("id".equals(name))idVal=dv;}
                Integer needDir=null; if("com.spotify.musicappplatform.main.MainLayout".equals(tag))needDir=1; else if(ltrClass.equals(tag)||"androidx.coordinatorlayout.widget.CoordinatorLayout".equals(tag)||"com.spotify.encoremobile.tooltip.TooltipContainer".equals(tag))needDir=2;
                if("androidx.constraintlayout.widget.Guideline".equals(tag)&&idVal!=null&&idVal==0x7f0b12a3){for(Attr a:attrs)if("layout_constraintGuide_percent".equals(a.name)){if(a.dtype!=4||a.dval!=0x3e800000)throw new IllegalArgumentException("Unexpected 8.9 panel guideline value");Spotify89BinaryUtil.put32(c,a.off+16,0x3ea3d70a);}}
                if(needDir!=null){
                    int androidNs=-1; for(Attr a:attrs){int rid=Spotify89BinaryUtil.attrResId(a.nameIdx,vals);if((rid>>>24)==0x01){androidNs=Spotify89BinaryUtil.i32(c,a.off);break;}} if(androidNs<0)androidNs=neu.indexOf("http://schemas.android.com/apk/res/android");
                    byte[] attr=new byte[20]; Spotify89BinaryUtil.put32(attr,0,androidNs); Spotify89BinaryUtil.put32(attr,4,insert); Spotify89BinaryUtil.put32(attr,8,0xffffffff); Spotify89BinaryUtil.put16(attr,12,8); attr[14]=0;attr[15]=0x10;Spotify89BinaryUtil.put32(attr,16,needDir);
                    int ins=attrCount; for(int i=0;i<attrs.size();i++)if(Integer.compareUnsigned(Spotify89BinaryUtil.attrResId(attrs.get(i).nameIdx,vals),0x010103b2)>0){ins=i;break;}
                    int pos=ap+ins*attrSize; byte[] nc=new byte[c.length+attrSize];System.arraycopy(c,0,nc,0,pos);System.arraycopy(attr,0,nc,pos,attr.length);System.arraycopy(c,pos,nc,pos+attrSize,c.length-pos);c=nc;Spotify89BinaryUtil.put32(c,4,csz+attrSize);Spotify89BinaryUtil.put16(c,28,attrCount+1);
                }
            } else if(typ==0x0103){for(int q:new int[]{16,20})Spotify89BinaryUtil.put32(c,q,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,q),mapping));}
            else if(typ==0x0104){Spotify89BinaryUtil.put32(c,16,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,16),mapping));if((c[23]&0xff)==3)Spotify89BinaryUtil.put32(c,24,Spotify89BinaryUtil.mapIndex(Spotify89BinaryUtil.i32(c,24),mapping));}
            chunks.add(c);o+=csz;
        }
        int total=rootHs+newPool.length+rm.length;for(byte[]c:chunks)total+=c.length;byte[]out=new byte[total];System.arraycopy(data,0,out,0,rootHs);int p=rootHs;System.arraycopy(newPool,0,out,p,newPool.length);p+=newPool.length;System.arraycopy(rm,0,out,p,rm.length);p+=rm.length;for(byte[]c:chunks){System.arraycopy(c,0,out,p,c.length);p+=c.length;}Spotify89BinaryUtil.put32(out,4,out.length);return out;
    }

    private static final class Attr{String name;int off,nameIdx,dtype,dval,raw;Attr(String n,int o,int ni,int dt,int dv,int r){name=n;off=o;nameIdx=ni;dtype=dt;dval=dv;raw=r;}}
}
