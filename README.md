# BYD Spotify Patcher v0.5.3

Windows tool for patching a **user-supplied Spotify 8.9.76.538 APK** for BYD Android infotainment.

It creates separately installable Spotify instances that can coexist with BYD's factory Spotify app.

The patcher does **not** contain or download Spotify. The original APK is supplied by the user and patched locally on their PC.

## Screenshots

![BYD Spotify Patcher](docs/patcher-main.png)

![BYD Spotify Patcher on BYD infotainment](docs/patcher-byd.png)

## Features

* Install **two separate Spotify instances** alongside BYD's factory Spotify.
* Use different Spotify accounts in each instance.
* Automatically restores playback after the BYD infotainment system restarts.
* **Left (LHD)** and **Right (RHD)** wide-screen layouts.
* Custom visible app name.
* Adjustable launcher-icon colour with live preview.
* Automatic APK patching, signing and verification.

### App instances

| Instance  | Internal package    | Default name    | Output        |
| --------- | ------------------- | --------------- | ------------- |
| Primary   | `com.spotify.musib` | `SpotifyPlus`   | `*_BYD.apk`   |
| Secondary | `com.spotify.musia` | `SpotifyPlus-S` | `*_BYD_S.apk` |

Both instances have been tested successfully on BYD infotainment and can be installed together.

If one of the patched Spotify apps was playing when the vehicle was shut down, that same instance resumes playback after the infotainment system starts again.

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

![BYD Spotify Patcher](docs/Step1.jpg)
![BYD Spotify Patcher2](docs/Step2.jpg)
![BYD Spotify Patcher3](docs/Step3.jpg)

4. Select the original Spotify APK.
5. Choose **Primary** or **Secondary**.
6. Optionally change the visible app name and icon colour.
7. Choose **Left (LHD)** or **Right (RHD)**.
8. Click **ANALYSE APK**.
![BYD Spotify Patcher4](docs/Step4.jpg)

9. If the APK is supported, click **PATCH + SIGN**.

![BYD Spotify Patcher5](docs/Step5.jpg)

10. Install the generated APK on the BYD infotainment system.

![BYD Spotify Patcher6](docs/Step6.jpg)
![BYD Spotify Patcher7](docs/Step7.jpg)

The patched apps can coexist with each other and with BYD's original `com.spotify.music` installation.

## Wide-screen layout

Choose the layout that suits the vehicle:

* **Left (LHD)** — navigation and mini-player remain on the left.
* **Right (RHD)** — navigation and mini-player are moved to the right while Spotify content remains left-to-right.

The layout is selected when creating the APK.

## Launcher icon

The patched Spotify icon includes a small **+** mark.

Its colour can be adjusted from **0–359°** to make Primary and Secondary easier to distinguish. The patcher shows a live preview before creating the APK.

## Playback restore

Playback restoration has been tested on BYD infotainment.

If a patched Spotify instance was playing before the vehicle was shut down, that instance can resume playback after the infotainment system restarts.

## Download

The current self-contained Windows version is available from:

**[GitHub Releases](../../releases/latest)**

No Python, Java, Android Studio or Android SDK is required to use the released Windows version.

## Notes

This project modifies a user-supplied Spotify APK so cloned instances can coexist with the original BYD installation and work correctly with the BYD wide-screen interface.

**No Spotify APK, Spotify DEX, Spotify resources or other Spotify binaries are distributed with this project.**
