package com.bydspotifymanager.app;

final class BuildConfigData {
    static final String MANAGER_VERSION = "1.0";

    // Spotify 9.1.
    static final String SUPPORTED_VERSION = "9.1.78.2215";
    static final long SUPPORTED_VERSION_CODE = 145505425L;
    static final String STOCK_SHA256 = "e8d8c7316619a63bd8a314d51f389feac9db70d62234b0da87a1b75b08ae85d2";
    static final String OFFICIAL_PACKAGE = "com.spotify.music";
    static final String PRIMARY_PACKAGE = "com.spotify.musia";
    static final String SECONDARY_PACKAGE = "com.spotify.musib";
    static final String APKMIRROR_URL = "https://www.apkmirror.com/apk/spotify-ab/spotify-music-podcasts/spotify-music-and-podcasts-9-1-78-2215-release/spotify-music-and-podcasts-9-1-78-2215-2-android-apk-download/";

    // Spotify 8.9 uses the same Primary/Secondary package slots as Spotify 9.1.
    static final String V89_SUPPORTED_VERSION = "8.9.76.538";
    static final long V89_SUPPORTED_VERSION_CODE = 119017142L;
    static final String V89_PRIMARY_PACKAGE = PRIMARY_PACKAGE;
    static final String V89_SECONDARY_PACKAGE = SECONDARY_PACKAGE;
    static final String V89_APKMIRROR_URL = "https://www.apkmirror.com/apk/spotify-ab/spotify/spotify-music-and-podcasts-8-9-76-538-release/spotify-music-and-podcasts-8-9-76-538-2-android-apk-download/";

    static final String KEY_ALIAS = "byd_spotify_manager_spotifyplus";
    private BuildConfigData() {}
}
