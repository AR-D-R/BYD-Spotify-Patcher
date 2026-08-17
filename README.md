# BYD Spotify Patcher v0.5.3

Experimental Windows tool for patching a **user-supplied Spotify 8.9.76.538 APK** for BYD Android infotainment.

The tool does **not** contain or download Spotify. The user supplies the original `com.spotify.music` APK locally.

## v0.5.3 profile cleanup

- Removes the experimental third (`com.spotify.musid`) clone after BYD head-unit testing showed that it crashes on launch.
- Keeps only the validated **Primary** (`com.spotify.musib`) and **Secondary** (`com.spotify.musia`) profiles.
- BYD testing confirmed the AutoResume/restore behaviour works across the two supported clones: after vehicle restart, the clone that was playing before shutdown resumes.
- AutoResume/restore implementation itself is unchanged.

## v0.5.2 window-layout update

- Centers the patcher window on startup.
- Fits the startup window inside the usable desktop area rather than relying on a fixed 920x840 geometry.
- Adapts the log-pane height to shorter/scaled displays so the bottom action and signing-key controls remain visible.
- No patching, branding, signing or AutoResume/restore logic changed from v0.5.1.

## v0.5.1 UI update

- Adds a live **Logo preview** panel using the launcher artwork from the selected Spotify APK.
- The preview uses the same `+` mark and hue-rotation code as the final APK branding and updates while the hue slider moves.
- Clarifies that **App instance** is used to keep separate Spotify profiles/logins available side-by-side.
- No autoplay/restore or core APK patching logic was changed from v0.5.

## What v0.5 does

Every output gets the common, car-tested patch set from v0.4:

- clones the Spotify package so it can coexist with BYD's factory `com.spotify.music`;
- fixes package-scoped permissions/providers and the media-api provider collision;
- patches Spotify's exact process/package DEX strings and repairs DEX SHA-1/Adler32;
- preserves `META-INF/services/*` runtime metadata;
- applies the proven v9 compact/larger-text BYD resource profile;
- adds a small **+** to the Spotify launcher icon;
- adds the proven `byd.intent.action.RESTORE_PLAYBACK` MediaBrowser auto-resume helper;
- aligns, signs and verifies the final APK.

v0.5.3 exposes two supported clone identities:

| Instance | Fixed internal package | Default visible name | Default output |
|---|---|---|---|
| Primary | `com.spotify.musib` | `SpotifyPlus` | `*_BYD.apk` |
| Secondary | `com.spotify.musia` | `SpotifyPlus-S` | `*_BYD_S.apk` |

The **internal package is fixed** by the selected instance. Users can only change the visible launcher/app-list name (maximum 24 characters).

The launcher icon can also be hue-shifted from 0–359 degrees. This changes the colour while retaining the existing Spotify-style icon and the patcher's plus mark, making multiple installed clones easier to distinguish.

The user can also choose one of two static wide-screen layouts:

- **Left (LHD)** — the stable v9 layout; navigation + mini-player stay on the left.
- **Right (RHD)** — the same v9 text/spacing plus the stable v14 right-side panel transformation. Spotify content remains LTR internally.

There is intentionally no live side-switch button. The static LHS/RHS choice is more reliable on the BYD head unit.

## Supported Spotify version

v0.5.3 is intentionally strict and supports only:

- Spotify **8.9.76.538**
- versionCode **119017142**

Later Spotify 9.x builds are not included in this profile. `ANALYSE APK` refuses an unsupported or structurally different APK rather than producing an untested build.

## Normal user flow

1. Select the original Spotify 8.9.76.538 APK.
2. Select **Primary** or **Secondary**.
3. Optionally change the visible app name and icon hue.
4. Select **Left (LHD)** or **Right (RHD)**.
5. Click **ANALYSE APK**.
6. If the exact profile is supported, click **PATCH + SIGN**.
7. Install the generated APK on the car.

The selected clone package is separate from the factory `com.spotify.music` installation and from the other supported clone identity.

## Signing / updates

The patcher creates a private per-user signing identity on first use and reuses it for future updates. It is stored in:

```text
%LOCALAPPDATA%\BYDSpotifyPatcher
```

Use **Export backup** to keep a copy of the signing key. If a later patched APK is signed with a different key, Android will not install it as an update over the existing clone with the same internal package.

Early testers who already used a manual `spotifyplus.jks` can use **Import existing JKS/P12…** once, preserving update compatibility.

## Build a single self-contained Windows EXE

On the build PC, install:

- Python 3
- Android Studio / Android SDK Build Tools
- A full JDK containing `java`, `jdeps`, `jlink` and the `jmods` directory (Temurin JDK 21 is recommended)

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

The portable build script now auto-detects common full-JDK installs, including Eclipse Adoptium. If required, point `JAVA_HOME` at the actual full JDK folder, for example:

```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot"
```

Do not point `JAVA_HOME` at an Android Studio JBR that lacks `jmods\java.base.jmod`; `jlink` cannot build the bundled runtime from it. Then run the portable build script again.

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

Analyse the primary instance:

```powershell
py .\byd_spotify_patcher.py Spotify.apk --analyse --instance primary
```

Build a secondary/right-side clone with a custom visible name and hue:

```powershell
py .\byd_spotify_patcher.py Spotify.apk --instance secondary --app-label "Spotify Car" --icon-hue 110 --panel-side right
```

If no output path is supplied, the instance controls the output suffix automatically:

```text
Primary   -> Spotify_BYD.apk
Secondary -> Spotify_BYD_S.apk
```


Unsigned test build:

```powershell
py .\byd_spotify_patcher.py Spotify.apk --instance secondary --panel-side right --unsigned
```

## Notes

The tiny embedded helper DEX payloads are patcher-authored code for the LTR container and auto-resume service. They are retargeted to the selected fixed clone package during patching. The auto-resume behaviour itself is unchanged from v0.4.

No Spotify APK, Spotify DEX, Spotify resources, or other Spotify binaries are bundled with the patcher.
