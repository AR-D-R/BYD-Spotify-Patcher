package com.bydspotifymanager.app;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.math.BigInteger;
import java.security.*;
import java.security.cert.X509Certificate;
import java.util.Calendar;
import javax.security.auth.x500.X500Principal;

final class SigningKeyStore {
    static final class KeyMaterial {
        final PrivateKey privateKey;
        final X509Certificate certificate;
        KeyMaterial(PrivateKey k, X509Certificate c) { privateKey = k; certificate = c; }
    }

    static KeyMaterial getOrCreate() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (!ks.containsAlias(BuildConfigData.KEY_ALIAS)) {
            Calendar start = Calendar.getInstance();
            Calendar end = Calendar.getInstance(); end.add(Calendar.YEAR, 25);
            KeyPairGenerator gen = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore");
            KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                    BuildConfigData.KEY_ALIAS, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                    .setKeySize(2048)
                    .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                    .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                    .setCertificateSubject(new X500Principal("CN=BYD Spotify Manager Local Key"))
                    .setCertificateSerialNumber(BigInteger.ONE)
                    .setCertificateNotBefore(start.getTime())
                    .setCertificateNotAfter(end.getTime())
                    .build();
            gen.initialize(spec);
            gen.generateKeyPair();
            ks.load(null);
        }
        PrivateKey key = (PrivateKey) ks.getKey(BuildConfigData.KEY_ALIAS, null);
        X509Certificate cert = (X509Certificate) ks.getCertificate(BuildConfigData.KEY_ALIAS);
        if (key == null || cert == null) throw new KeyStoreException("Signing key unavailable");
        return new KeyMaterial(key, cert);
    }
}
