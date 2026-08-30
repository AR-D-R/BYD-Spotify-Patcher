package com.bydspotifymanager.app;

import android.app.PendingIntent;
import android.content.*;
import android.content.pm.PackageInstaller;
import android.os.Build;

import java.io.*;

final class PackageInstallHelper {
    static void install(Context context, File apk, File dm, String packageName) throws Exception {
        PackageInstaller installer = context.getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams params = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        params.setAppPackageName(packageName);
        int id = installer.createSession(params);
        PackageInstaller.Session session = installer.openSession(id);
        try {
            write(session, apk, "base.apk");
            if (dm != null) write(session, dm, "base.dm");
            Intent result = new Intent(context, InstallResultReceiver.class)
                    .setAction("com.bydspotifymanager.app.INSTALL_RESULT")
                    .putExtra("targetPackage", packageName);
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
            PendingIntent pending = PendingIntent.getBroadcast(context, id, result, flags);
            session.commit(pending.getIntentSender());
        } finally {
            session.close();
        }
    }

    private static void write(PackageInstaller.Session session, File file, String name) throws Exception {
        try (InputStream in = new BufferedInputStream(new FileInputStream(file));
             OutputStream out = session.openWrite(name, 0, file.length())) {
            IoUtil.copy(in, out);
            session.fsync(out);
        }
    }
}
