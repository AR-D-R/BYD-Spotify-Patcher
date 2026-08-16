# Patch discovery notes

This file is intended as the hand-off to ChatGPT Codex / another developer. It records the failures that identified each required transformation.

1. **Coexistence problem** — BYD factory Spotify owns `com.spotify.music`. A second unmodified Spotify APK cannot be installed with the same application ID.
2. **Provider collision** — after changing the app package, Android reported `INSTALL_FAILED_CONFLICTING_PROVIDER` for `com.spotify.mobile.android.mediaapi`. That authority must be unique too.
3. **Do not delete all META-INF** — doing so removed `META-INF/services/kotlinx.coroutines.internal.MainDispatcherFactory`, causing `Module with the Main dispatcher is missing` on startup. Only old signing entries (`MANIFEST.MF`, `.SF`, `.RSA`/`.DSA`/`.EC`) should be stripped.
4. **Spotify process allowlist** — once services were preserved, Spotify aborted with `AssertionError: The process name ... is not allowed to start` in `EarlyInitializationProvider`. Exact DEX string entries equal to the original package must be changed too.
5. **DEX string ordering** — changing the exact DEX string to `com.ardr.spotplus` produced `Out-of-order string_ids`. `com.spotify.musib` was selected because it is the same length and remains lexically in a safe position between Spotify's neighbouring DEX strings.
6. **DEX integrity** — after an in-place DEX string change, recalculate header SHA-1 (`bytes[12:32] = SHA1(bytes[32:])`) and Adler32 (`uint32@8 = adler32(bytes[12:])`).
7. **Android 11+ APK alignment** — Pixel installation initially failed because `resources.arsc` was uncompressed but not aligned to 4 bytes. Output must be aligned before signing.
8. **Signing** — modified APKs need a new signature. Reusing the same per-user signing key is required for in-place updates over an older patched release.

Known working alternate package/process name: `com.spotify.musib`.

Known manifest identity strings across tested versions include:
- `com.spotify.music`
- `.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`
- `.permission.C2D_MESSAGE`
- `.permission.INTERNAL_BROADCAST`
- `.permission.SECURED_BROADCAST`
- `.androidx-startup`
- `.share`
- `.imagepicker`
- `.early-initialization`
- `.profile`
- `.vtec`
- `.sso.afterlogindummytask`
- newer build additions `.calimage` and `.pushnotificationsv2`
- `androidx.car.app.connection` is changed to `musibxxx.car.app.connection`

Known resources authority:
- `com.spotify.mobile.android.mediaapi` -> `com.spotify.musib.android.mediaapi_`

## v0.4 BYD UI / playback additions

9. **Spotify 8.9.76.538 UI profile** — the stable v9 build changes 40 resource values: compact adaptive margins, larger list artwork/controls and larger Encore text styles/player text.
10. **Right-side panel** — the stable v14 build modifies only `res/layout-w600dp-v13/adaptive_main.xml` plus a tiny patcher-authored `LtrFrameLayout` DEX. The root layout is mirrored for the panel position while dynamically inflated Spotify content is forced back to normal LTR ordering.
11. **Auto-resume** — the unused disabled MediaRoute provider service slot is repurposed as `com.spotify.musib.AutoResumeService` for `byd.intent.action.RESTORE_PLAYBACK`. The helper connects to Spotify's `SpotifyMediaBrowserService` and calls the media session's play transport control. This reproduces the BYD background-resume behaviour without bringing Spotify to the foreground.
12. **Branding** — app label resource `0x7f130116` becomes `SpotifyPlus`; launcher icons receive a small plus. Adaptive foreground resource `0x7f080782` is redirected from the original XML foreground to a generated PNG.
13. **Static side selection** — LHS/RHS is chosen at patch time. A runtime side-switch experiment was deliberately not retained because it introduced startup instability on the head unit.
