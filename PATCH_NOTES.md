# Patch discovery notes

This file records the failures that identified each required transformation.

1. **Coexistence problem** — BYD factory Spotify owns `com.spotify.music`. A second unmodified Spotify APK cannot be installed with the same application ID.
2. **Provider collision** — after changing the app package, Android reported `INSTALL_FAILED_CONFLICTING_PROVIDER` for `com.spotify.mobile.android.mediaapi`. That authority must be unique too.
3. **Do not delete all META-INF** — doing so removed `META-INF/services/kotlinx.coroutines.internal.MainDispatcherFactory`, causing `Module with the Main dispatcher is missing` on startup. Only old signing entries (`MANIFEST.MF`, `.SF`, `.RSA`/`.DSA`/`.EC`) should be stripped.
4. **Spotify process allowlist** — once services were preserved, Spotify aborted with `AssertionError: The process name ... is not allowed to start` in `EarlyInitializationProvider`. Exact DEX string entries equal to the original package must be changed too.
5. **DEX string ordering** — replacement package strings are patched in place and therefore must remain correctly ordered in DEX `string_ids`. Same length alone is not enough.
6. **DEX integrity** — after an in-place DEX string change, recalculate header SHA-1 (`bytes[12:32] = SHA1(bytes[32:])`) and Adler32 (`uint32@8 = adler32(bytes[12:])`).
7. **Android 11+ APK alignment** — Pixel installation initially failed because `resources.arsc` was uncompressed but not aligned to 4 bytes. Output must be aligned before signing.
8. **Signing** — modified APKs need a new signature. Reusing the same per-user signing key is required for in-place updates over an older patched release of the same clone identity.

## Supported clone identities

The patcher exposes two **fixed** internal packages; users do not type arbitrary package names:

- Primary: `com.spotify.musib` — tested DEX-order safe.
- Secondary: `com.spotify.musia` — tested DEX-order safe in the Spotify 8.9.76.538 fixture.

Manifest package-derived strings and the resources provider authority are generated from the selected package. For example, the media API authority becomes `<selected-package>.android.mediaapi_`.

The patcher-authored `LtrFrameLayout` and `AutoResumeService` helper DEX payloads are also retargeted from their original `com.spotify.musib` class path to the selected fixed package, followed by normal helper-DEX SHA-1/Adler32 repair. Their behaviour is otherwise unchanged.

## BYD UI / playback additions

9. **Spotify 8.9.76.538 UI profile** — the stable v9 build changes 40 resource values: compact adaptive margins, larger list artwork/controls and larger Encore text styles/player text.
10. **Right-side panel** — the stable v14 build modifies only `res/layout-w600dp-v13/adaptive_main.xml` plus a tiny patcher-authored `LtrFrameLayout` DEX. The root layout is mirrored for the panel position while dynamically inflated Spotify content is forced back to normal LTR ordering.
11. **Auto-resume** — the unused disabled MediaRoute provider service slot is repurposed as `<selected-package>.AutoResumeService` for `byd.intent.action.RESTORE_PLAYBACK`. The helper connects to Spotify's `SpotifyMediaBrowserService` and calls the media session's play transport control. BYD testing confirmed the supported Primary/Secondary clones resume correctly after vehicle restart; the helper logic remains unchanged.
12. **Branding** — app label resource `0x7f130116` becomes the selected visible name; launcher icons receive a small plus and may be hue-shifted. Adaptive foreground resource `0x7f080782` is redirected from the original XML foreground to a generated PNG.
13. **Static side selection** — LHS/RHS is chosen at patch time. A runtime side-switch experiment was deliberately not retained because it introduced startup instability on the head unit.



## v0.5.2 window-layout changes

- Startup geometry is calculated after widgets are laid out and centered in the usable desktop area.
- On Windows, the work-area calculation excludes the taskbar and compensates for DPI-coordinate differences when necessary.
- The log pane uses fewer default lines on shorter/scaled desktops so the action and signing rows remain visible.
- APK transformation and AutoResume logic are unchanged.

## v0.5.1 UI-only changes

- Live logo preview sourced from the selected APK.
- Preview calls the same `add_plus()` and `shift_hue()` code used for final launcher branding.
- App-instance wording now explains the separate-profile purpose.
- APK patching, package identities, output suffixes and AutoResume logic are unchanged.

## v0.5.3 BYD validation

- Primary (`com.spotify.musib`) launches correctly on the BYD head unit.
- Secondary (`com.spotify.musia`) launches correctly on the BYD head unit.
- Playback restore works across restart: whichever supported clone was playing before shutdown resumes after restart.
- The experimental third (`com.spotify.musid`) crashed on launch and has therefore been removed from the GUI, CLI and supported configuration.
- DEX lexical-order validation is strict for all remaining profiles; there is no unsafe bypass.
