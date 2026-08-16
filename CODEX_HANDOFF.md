# Codex handoff — BYD Spotify Patcher v0.4

v0.4 intentionally supports only Spotify **8.9.76.538 / versionCode 119017142**. It now combines the proven coexistence patch, v9/v14 BYD UI profiles, SpotifyPlus branding, auto-resume and one-click signing.

Important invariants:

1. Do not globally rename Java/Kotlin implementation class descriptors under `com/spotify/music/...`.
2. Preserve `META-INF/services/*`; deleting those caused the missing Kotlin coroutine Main dispatcher crash.
3. The clone package/process is `com.spotify.musib`. It is same-length and lexically safe in this Spotify DEX string table.
4. Repair DEX SHA-1 + Adler32 after exact package/process string edits.
5. Strip only obsolete signing metadata (`MANIFEST.MF`, `.SF`, `.RSA/.DSA/.EC`), not all of META-INF.
6. Keep APK uncompressed entries 4-byte aligned before signing.
7. Reuse the same per-user signing identity for updates. Never ship a universal private key.
8. The public portable build embeds AOSP `apksigner.jar` plus a jlink Java runtime inside the PyInstaller one-file EXE.
9. Pre-flight must fail closed for any Spotify version/resource/layout that does not match the 8.9.76.538 profile.
10. Common UI resource patch = stable v9 profile (40 resource values).
11. Left/LHD output keeps the stock wide-screen panel position and injects AutoResume as `classes8.dex`.
12. Right/RHD output additionally patches `adaptive_main.xml` to the stable v14 layout, injects `LtrFrameLayout` as `classes8.dex`, and AutoResume as `classes9.dex`.
13. AutoResume repurposes the disabled MediaRoute provider service slot for `byd.intent.action.RESTORE_PLAYBACK` and resumes through Spotify's MediaBrowser/MediaSession without foregrounding the app.
14. Do not reintroduce the experimental runtime side-switch button; it caused a head-unit startup crash. Side position is a static patch-time choice.

Regression fingerprints used by v0.4:

- stock wide layout SHA-256: `9e25d64fdfd097a1fe544af86439fe674942911fc7f6a12a2ea99321a4a7027e`
- right/v14 wide layout SHA-256: `6912316de2ad7de66a222898a1259943a8cbbcae4a2419e6b7699accc9510342`
- LtrFrame helper DEX SHA-256: `9c8d8dd1a633501666486d4580018892deb02e07a7038850a6c6e705bc9d1f04`
- AutoResume helper DEX SHA-256: `6a8070ac18fd288a5f32af1dc244976e197e0ffae2306c9d51d2f962a47a12e2`

Next useful work: build regression tests around a user-supplied fixture, test the single-file EXE on a clean Windows VM, and add new Spotify version profiles only after login + car testing.
