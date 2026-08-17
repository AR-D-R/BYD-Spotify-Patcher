# Changelog

## v0.5.3

- Removed the experimental third `com.spotify.musid` profile after BYD head-unit testing confirmed it crashes on launch.
- Primary `com.spotify.musib` and Secondary `com.spotify.musia` remain the only selectable profiles in both GUI and CLI.
- Removed the unsafe DEX-order bypass path; supported clone packages now always pass strict lexical-order validation.
- BYD testing confirmed AutoResume/restore works with the supported clones: the app that was playing before vehicle shutdown resumes after restart.
- AutoResume/restore logic itself is unchanged.

## v0.5.2

- Centers the GUI on startup instead of opening offset toward the top-left.
- Sizes the window against the usable Windows desktop/work area so it stays above the taskbar.
- Automatically reduces the log pane height on shorter or display-scaled desktops, keeping action and signing controls visible without manual resizing.
- Core patching, branding, signing and AutoResume/restore behavior unchanged.

## v0.5.1

- Added live launcher-logo preview beside the branding controls.
- Preview reads the actual icon from the selected APK and applies the same plus-mark and hue-shift functions used during patching.
- Clarified the App instance label and descriptions for separate Spotify profiles.
- Core patching and AutoResume/restore behavior unchanged.


## v0.5

- Adds three fixed clone identities selectable in the GUI and CLI:
  - Primary: `com.spotify.musib`
  - Secondary: `com.spotify.musia`
  - Third (experimental): `com.spotify.musid`
- Adds editable **visible app name** independent of the internal package, with a 24-character limit.
- Adds a launcher-icon **hue** control (0–359°) while retaining the plus mark.
- Adds distinct default output naming: `_BYD.apk`, `_BYD_S.apk`, and `_BYD_T.apk`.
- Retargets manifest identities, resources authorities, LTR helper DEX and AutoResume helper DEX to the selected fixed package.
- Keeps the v0.4 AutoResume playback logic unchanged.
- Adds package-aware right-layout verification instead of a `musib`-only final hash check.
- Marks `com.spotify.musid` experimental because it violates lexical ordering in some tested stock DEX string tables. The third instance can still be explicitly built for testing.
- Adds CLI options `--instance`, `--app-label`, and `--icon-hue`.

## v0.4

- Restricts the public patch profile to the proven Spotify **8.9.76.538 / versionCode 119017142** build.
- Adds a GUI selector for **Left (LHD)** and **Right (RHD)** side-panel layouts.
- Left profile applies the stable v9 compact/larger-text resource changes.
- Right profile applies the same v9 resource changes plus the stable v14 right-panel layout and LTR child-container helper.
- Adds the proven BYD `RESTORE_PLAYBACK` MediaBrowser auto-resume helper to both profiles.
- Renames the installed app to **SpotifyPlus**.
- Adds a small plus mark to legacy and adaptive launcher icons.
- Keeps the coexistence package `com.spotify.musib` and all provider/process fixes.
- Adds stricter pre-flight checks for the exact version, seven-DEX structure, v9 resource profile, wide-screen layout and branding resources.
- Adds Pillow for local icon generation.
- Reworks `build_portable_windows.ps1` to create a **single self-contained EXE** containing AOSP apksigner and a jlink-generated Java runtime.

## v0.3

- Signing became part of the normal one-click patch flow.
- Automatic per-user signing identity, v1/v2/v3 signing and verification.
- Portable signing runtime support and key backup/import.

## v0.2

- Added pre-flight APK analyser.
- Added DEX lexical-safety validation.
- Added support-safe diagnostics JSON.
