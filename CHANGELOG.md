# Changelog

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
