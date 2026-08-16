# Third-party notices

Portable builds of BYD Spotify Patcher may include Android's `apksigner` / `apksig` code from the Android Open Source Project.

`apksig` and `apksigner` are licensed under the Apache License, Version 2.0. The AOSP source is available from the Android Open Source Project `platform/tools/apksig` repository.

Portable builds may also include a `jlink`-generated Java runtime derived from the developer's OpenJDK/Android Studio JetBrains Runtime. The generated runtime keeps the applicable `legal` material produced by `jlink`.

The Windows executable also bundles Python dependencies used by the patcher, including `cryptography` and Pillow. Their upstream licences apply to those components.

The patcher does **not** contain Spotify APKs, Spotify DEX files, Spotify resources, or downloaded Spotify content. Users supply their own Spotify APK locally. The two tiny embedded helper DEX payloads are BYD Spotify Patcher-authored code for the right-panel LTR container and BYD playback auto-resume service.
