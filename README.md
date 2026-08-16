# BYD Spotify Patcher v0.4

Experimental Windows tool for patching a **user-supplied Spotify 8.9.76.538 APK** for BYD Android infotainment.

The tool does **not** contain or download Spotify. The user supplies the original `com.spotify.music` APK locally.

## What v0.4 does

Every output gets the common, car-tested patch set:

- clones `com.spotify.music` to `com.spotify.musib`, so it can coexist with BYD's factory Spotify;
- fixes package-scoped permissions/providers and the media-api provider collision;
- patches Spotify's exact process/package DEX strings and repairs DEX SHA-1/Adler32;
- preserves `META-INF/services/*` runtime metadata;
- applies the proven v9 compact/larger-text BYD resource profile;
- renames the installed app to **SpotifyPlus**;
- adds a small **+** to the Spotify launcher icon;
- adds the proven `byd.intent.action.RESTORE_PLAYBACK` MediaBrowser auto-resume helper;
- aligns, signs and verifies the final APK.

The user can choose one of two static wide-screen layouts:

- **Left (LHD)** — the stable v9 layout; navigation + mini-player stay on the left.
- **Right (RHD)** — the same v9 text/spacing plus the stable v14 right-side panel transformation. Spotify content remains LTR internally.

There is intentionally no live side-switch button. The static LHS/RHS choice is more reliable on the BYD head unit.

## Supported Spotify version

v0.4 is intentionally strict and supports only:

- Spotify **8.9.76.538**
- versionCode **119017142**

Later Spotify 9.x builds were not included in this profile because the cloned package had authentication/login compatibility problems during testing. `ANALYSE APK` refuses an unsupported or structurally different APK rather than producing an untested build.

## Normal user flow

1. Select the original Spotify 8.9.76.538 APK.
2. Select **Left (LHD)** or **Right (RHD)**.
3. Click **ANALYSE APK**.
4. If the exact profile is supported, click **PATCH + SIGN**.
5. Install the generated APK on the car.

The output package is `com.spotify.musib`, so the factory `com.spotify.music` installation remains untouched.

## Signing / updates

The patcher creates a private per-user signing identity on first use and reuses it for future updates. It is stored in:

```text
%LOCALAPPDATA%\BYDSpotifyPatcher
```

Use **Export backup** to keep a copy of the signing key. If a later patched APK is signed with a different key, Android will not install it as an update over the existing SpotifyPlus installation.

Early testers who already used a manual `spotifyplus.jks` can use **Import existing JKS/P12…** once, preserving update compatibility.

## Build a single self-contained Windows EXE

On the build PC, install:

- Python 3
- Android Studio / Android SDK Build Tools
- Android Studio's JBR or another JDK containing `java`, `jdeps` and `jlink`

Then open PowerShell in this source folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_portable_windows.ps1
```

The script locates `apksigner.jar`, creates a minimal Java runtime with `jlink`, and packages everything with PyInstaller into:

```text
dist\BYDSpotifyPatcher.exe
```

That EXE is self-contained for end users. They do not need Android Studio, the Android SDK, Java, apksigner, zipalign or PowerShell.

### If Android SDK is not auto-detected

Set the SDK path for the current PowerShell session, for example:

```powershell
$env:ANDROID_SDK_ROOT = "$env:LOCALAPPDATA\Android\Sdk"
```

If required, point `JAVA_HOME` at Android Studio's JBR:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
```

Then run the portable build script again.

## Development build

For a smaller developer EXE that uses the build/target PC's installed Android SDK/Java for signing:

```powershell
.\build_windows.ps1
```

Output:

```text
dist\BYDSpotifyPatcher.exe
```

## Run from source

```powershell
py -m pip install -r requirements.txt
py .\byd_spotify_patcher.py --gui
```

## Command line

Analyse:

```powershell
py .\byd_spotify_patcher.py Spotify.apk --analyse
```

Build Left/LHD:

```powershell
py .\byd_spotify_patcher.py Spotify.apk SpotifyPlus_LHD.apk --panel-side left
```

Build Right/RHD:

```powershell
py .\byd_spotify_patcher.py Spotify.apk SpotifyPlus_RHD.apk --panel-side right
```

Unsigned test build:

```powershell
py .\byd_spotify_patcher.py Spotify.apk SpotifyPlus_unsigned.apk --panel-side right --unsigned
```

## Notes

The tiny embedded helper DEX payloads are patcher-authored code for the LTR container and auto-resume service. No Spotify APK, Spotify DEX, Spotify resources, or other Spotify binaries are bundled with the patcher.
