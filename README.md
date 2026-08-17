# BYD Spotify Patcher v0.5.3

Windows tool for patching a **user-supplied Spotify 8.9.76.538 APK** for BYD Android infotainment.

It creates separately installable Spotify instances that can coexist with BYD's factory Spotify app.

The patcher does **not** contain or download Spotify. The original APK is supplied by the user and patched locally on their PC.

## Features
* Allows to use fully functional Spotify app within BYD infotainment system. (DJ X, sorting playlists by genre, easy to start radio from a song, albums, lyrics, artists information, etc.)
* Can generate up to 2 separate Spotify instances that can be installed alongside BYD's factory Spotify. User1 can use SpotifyPlus A logged into User1 account and User2 can use SpotifyPlus B logged into User 2 Spotify account.
* Similar to the OEM version a patched app will automatically restore playback after the BYD infotainment system restarts.
* **Left (LHD)** and **Right (RHD)** wide-screen layouts.
* Custom visible app name. SpotifyPlus as default.
* Adjustable launcher-icon colour with live preview.
* Applies larger text and wide-screen UI adjustments
* Automatic APK patching, signing and verification.

## Supported Spotify version

Currently supported:

* Spotify **8.9.76.538**
* versionCode **119017142**

**Download the tested Spotify 8.9.76.538 universal APK from [APKMirror](https://www.apkmirror.com/apk/spotify-ab/spotify/spotify-music-and-podcasts-8-9-76-538-release/spotify-music-and-podcasts-8-9-76-538-2-android-apk-download/).**

Other Spotify versions are rejected by **ANALYSE APK** rather than being patched with an untested profile.

## How to use

1. Download the Windows patcher from the **[Releases](../../releases/latest)** section.
2. Download the supported Spotify 8.9.76.538 APK.
3. Start `BYDSpotifyPatcher.exe`. 
Windows may show a security warning because the patcher is not code-signed with a commercial certificate. This is expected for an independently distributed open-source tool and does not mean Windows has detected malware.
If SmartScreen appears, click More info and then Run anyway.

![BYD Spotify Patcher](docs/images/Step1.jpg)
![BYD Spotify Patcher2](docs/images/Step2.jpg)
![BYD Spotify Patcher3](docs/images/Step3.jpg)

4. Select the original Spotify APK.
5. Choose **Primary** or **Secondary**.
6. Optionally change the visible app name and icon colour.
7. Choose **Left (LHD)** or **Right (RHD)**.

* **Left (LHD)** — navigation and mini-player remain on the left.
* **Right (RHD)** — navigation and mini-player are moved to the right while Spotify content remains left-to-right.

8. Click **ANALYSE APK**.
![BYD Spotify Patcher4](docs/images/Step4.jpg)

9. If the APK is supported, click **PATCH + SIGN**.

![BYD Spotify Patcher5](docs/images/Step5.jpg)

10. Install the generated APK on the BYD infotainment system.

![BYD Spotify Patcher6](docs/images/Step6.jpg)
![BYD Spotify Patcher7](docs/images/Step7.jpg)

The patched apps can coexist with each other and with BYD's original `com.spotify.music` installation.

## Playback restore

Playback restoration has been tested on BYD infotainment.

If a patched Spotify instance was playing before the vehicle was shut down, that instance can resume playback after the infotainment system restarts.

## Download

The current self-contained Windows version is available from:

**[GitHub Releases](../../releases/latest)**

## Notes

This project modifies a user-supplied Spotify APK so cloned instances can coexist with the original BYD installation and work correctly with the BYD wide-screen interface.

**No Spotify APK, Spotify DEX, Spotify resources or other Spotify binaries are distributed with this project.**
