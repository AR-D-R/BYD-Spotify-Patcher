# Codex handoff — BYD Spotify Patcher v0.6

v0.6 intentionally supports only Spotify **8.9.76.538 / versionCode 119017142**. It combines the proven coexistence patch, always-on BYD wide-screen visual fixes, independent stock/moderate/large font sizing, LHD/RHD placement, configurable branding, portrait prevention, AutoResume and one-click signing.

## Important invariants

1. Do not globally rename Java/Kotlin implementation class descriptors under `com/spotify/music/...`.
2. Preserve `META-INF/services/*`; deleting those caused the missing Kotlin coroutine Main dispatcher crash.
3. Clone identities are fixed:
   - primary `com.spotify.musib` — DEX-order safe and BYD launch-tested;
   - secondary `com.spotify.musia` — DEX-order safe and BYD launch-tested.
4. Repair DEX SHA-1 + Adler32 after exact package/process string edits and after helper-DEX retargeting.
5. Strip only obsolete signing metadata (`MANIFEST.MF`, `.SF`, `.RSA/.DSA/.EC`), not all of META-INF.
6. Keep APK uncompressed entries 4-byte aligned before signing.
7. Reuse the same per-user signing identity for updates. Never ship a universal private key.
8. Pre-flight must fail closed for any Spotify version/resource/layout or DEX lexical-order check that does not match the supported 8.9.76.538 profile.
9. The BYD visual/layout patch is always applied. There is no public Stock-layout mode in v0.6.
10. Font sizing is independent of the BYD visual/layout patch:
    - stock: no text-size patch;
    - moderate: 18 established text-size changes;
    - large: moderate plus 18 additional text-only changes.
11. Right/RHD additionally patches `res/layout-w600dp-v13/adaptive_main.xml` and injects the retargeted `LtrFrameLayout`; Left/LHD keeps the stock panel position.
12. AutoResume repurposes the disabled MediaRoute provider service slot for `byd.intent.action.RESTORE_PLAYBACK` and resumes through Spotify's MediaBrowser/MediaSession. Do not alter this logic without a separate test cycle.
13. Portrait prevention is enabled by default and is fingerprinted to the known 8.9.76.538 profile: 12 manifest locks + 3 runtime portrait requests.
14. Visible app label is independent of package identity and limited to 24 characters. Icon hue and `+` badge are branding only.
15. Default output names are `_BYD.apk` (primary) and `_BYD_S.apk` (secondary).
16. Do not reintroduce the failed third `com.spotify.musid` clone or runtime side-switch experiment without a new validated strategy.

## Reference fingerprints

- stock wide layout SHA-256: `9e25d64fdfd097a1fe544af86439fe674942911fc7f6a12a2ea99321a4a7027e`
- original musib right-layout helper DEX SHA-256: `9c8d8dd1a633501666486d4580018892deb02e07a7038850a6c6e705bc9d1f04`
- original musib AutoResume helper DEX SHA-256: `6a8070ac18fd288a5f32af1dc244976e197e0ffae2306c9d51d2f962a47a12e2`

## BYD validation status

Primary and Secondary launch successfully on the BYD head unit. AutoResume restores whichever supported clone was playing before shutdown. The portrait fix and new font-size choices can be regression-tested in the Android 10 / API 29 wide-screen emulator before final car validation.
