# BYD Spotify Patcher

Unofficial Windows tool for creating a BYD-friendly SpotifyPlus APK
from a user-supplied Spotify APK.

A copy of the original APK is available from APKMirror:

- Spotify version: 8.9.76.538
- Version code: 119017142
- Package: com.spotify.music
- Variant: Universal / nodpi APK

https://www.apkmirror.com/apk/spotify-ab/spotify/spotify-music-and-podcasts-8-9-76-538-release/spotify-music-and-podcasts-8-9-76-538-2-android-apk-download/

## What it does

- Installs alongside the factory BYD Spotify app
- Changes the package to SpotifyPlus
- Supports LHS and RHS BYD layouts
- Applies larger text and wide-screen UI adjustments
- Restores background playback after vehicle startup
- Signs the generated APK locally

## How to use

### 1. Download Spotify apk and BYD Spotify Patcher

Download Spotify 8.9.76.538 from apkmirror and download patcher from release section. Save them somewhere on your computer.

### 2. Open BYD Spotify Patcher

Extract the ZIP and run `BYDSpotifyPatcher.exe`.

Windows will most likely flag it because it is not signed.

![Open BYD Spotify Patcher](docs/images/Step1.jpg)

![skip warning](docs/images/Step2.jpg)

![skip warning2](docs/images/Step3.jpg)

### 3. Select the original Spotify APK. Patch and sign

Click **Browse...** and select the original Spotify 8.9.76.538 APK.

Choose:

- **Left (LHS)** – navigation/player on the left
- **Right (RHS)** – navigation/player on the right

Click **ANALYSE APK**, then **PATCH + SIGN**.

![Select Spotify APK](docs/images/Step4.jpg)

![Select Spotify APK2](docs/images/Step5.jpg)

### 6. Install SpotifyPlus

Copy the generated APK to the BYD infotainment system and install it.

SpotifyPlus installs alongside the factory Spotify app.

![Install SpotifyPlus](docs/images/Step6.jpg)

### 6. Enjoy fully functional Spotify

![Install SpotifyPlus](docs/images/Step7.jpg)

## Important

This repository does not contain or distribute Spotify APKs.
Users must supply their own compatible Spotify APK.
This project is not affiliated with Spotify or BYD.
