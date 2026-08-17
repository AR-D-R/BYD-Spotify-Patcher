# Codex handoff — BYD Spotify Patcher v0.5.3

v0.5.3 intentionally supports only Spotify **8.9.76.538 / versionCode 119017142**. It combines the proven coexistence patch, v9/v14 BYD UI profiles, configurable branding, AutoResume and one-click signing.

v0.5.3 removes the failed experimental third clone after BYD testing. Startup sizing/centering, GUI preview, core patching and AutoResume behavior otherwise remain unchanged.

Important invariants:

1. Do not globally rename Java/Kotlin implementation class descriptors under `com/spotify/music/...`.
2. Preserve `META-INF/services/*`; deleting those caused the missing Kotlin coroutine Main dispatcher crash.
3. Clone identities are fixed profiles, not user-entered package names:
   - primary `com.spotify.musib` — DEX-order safe and BYD launch-tested;
   - secondary `com.spotify.musia` — DEX-order safe and BYD launch-tested.
   The former experimental `com.spotify.musid` profile crashed on BYD launch and must not be reintroduced without a different safe patch strategy.
4. Repair DEX SHA-1 + Adler32 after exact package/process string edits and after helper-DEX retargeting.
5. Strip only obsolete signing metadata (`MANIFEST.MF`, `.SF`, `.RSA/.DSA/.EC`), not all of META-INF.
6. Keep APK uncompressed entries 4-byte aligned before signing.
7. Reuse the same per-user signing identity for updates. Never ship a universal private key.
8. The public portable build embeds AOSP `apksigner.jar` plus a jlink Java runtime inside the PyInstaller one-file EXE.
9. Pre-flight must fail closed for any Spotify version/resource/layout or DEX lexical-order check that does not match the supported 8.9.76.538 profiles. There is no unsafe DEX-order bypass.
10. Common UI resource patch = stable v9 profile (40 resource values).
11. Left/LHD output keeps the stock wide-screen panel position and injects retargeted AutoResume as `classes8.dex`.
12. Right/RHD output additionally patches `adaptive_main.xml`, injects the retargeted `LtrFrameLayout` as `classes8.dex`, and retargeted AutoResume as `classes9.dex`.
13. AutoResume repurposes the disabled MediaRoute provider service slot for `byd.intent.action.RESTORE_PLAYBACK` and resumes through Spotify's MediaBrowser/MediaSession without foregrounding the app. Do not alter this logic without a separate test cycle.
14. Right-layout output validation must be package-aware because the layout contains the selected helper class path; do not compare every clone to the original `musib`-specific right-layout hash.
15. Visible app label is independent of package identity and is limited to 24 characters. Icon hue is branding only.
16. Default output names are `_BYD.apk` (primary) and `_BYD_S.apk` (secondary).
17. Do not reintroduce the experimental runtime side-switch button; it caused a head-unit startup crash. Side position is a static patch-time choice.

Reference fingerprints from the original v0.4/musib profile:

- stock wide layout SHA-256: `9e25d64fdfd097a1fe544af86439fe674942911fc7f6a12a2ea99321a4a7027e`
- musib right/v14 wide layout SHA-256: `6912316de2ad7de66a222898a1259943a8cbbcae4a2419e6b7699accc9510342`
- original musib LtrFrame helper DEX SHA-256: `9c8d8dd1a633501666486d4580018892deb02e07a7038850a6c6e705bc9d1f04`
- original musib AutoResume helper DEX SHA-256: `6a8070ac18fd288a5f32af1dc244976e197e0ffae2306c9d51d2f962a47a12e2`

For the secondary profile the helper DEX and right-layout hashes necessarily differ after package retargeting.

BYD validation status: Primary and Secondary launch successfully; AutoResume restores whichever supported clone was playing before shutdown after vehicle restart. The former third `musid` clone crashed and was removed. Next useful work: continue testing the two supported profiles and add new Spotify version profiles only after login + car testing.
