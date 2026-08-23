# Patch discovery notes

This file records the failures and tests that identified the required transformations.

1. **Coexistence problem** — BYD factory Spotify owns `com.spotify.music`. A second unmodified Spotify APK cannot be installed with the same application ID.
2. **Provider collision** — after changing the app package, Android reported `INSTALL_FAILED_CONFLICTING_PROVIDER` for `com.spotify.mobile.android.mediaapi`. That authority must be unique too.
3. **Do not delete all META-INF** — doing so removed `META-INF/services/kotlinx.coroutines.internal.MainDispatcherFactory`, causing `Module with the Main dispatcher is missing` on startup. Only old signing entries should be stripped.
4. **Spotify process allowlist** — Spotify aborted with `AssertionError: The process name ... is not allowed to start` until exact DEX string entries equal to the original package were changed.
5. **DEX string ordering** — replacement package strings are patched in place and must remain correctly ordered in DEX `string_ids`.
6. **DEX integrity** — after in-place DEX edits, recalculate header SHA-1 and Adler32.
7. **Android 11+ APK alignment** — output must keep uncompressed entries 4-byte aligned before signing.
8. **Signing** — modified APKs need a new signature; the same per-user key must be reused for updates.

## Supported clone identities

- Primary: `com.spotify.musib` — tested DEX-order safe and BYD launch-tested.
- Secondary: `com.spotify.musia` — tested DEX-order safe and BYD launch-tested.

Manifest package-derived strings, the media API authority, the LTR helper and AutoResume helper are retargeted to the selected package.

## v0.6 BYD UI profile

- The proven BYD wide-screen visual/layout profile is always applied.
- The visual profile contains 22 non-font resource changes for car-friendly artwork/control sizing and spacing.
- Font sizing is independent:
  - **Stock**: original Spotify text sizes;
  - **Moderate**: 18 established BYD text-size changes;
  - **Large**: Moderate plus 18 additional text-only changes.
- Right/RHD modifies `res/layout-w600dp-v13/adaptive_main.xml` plus the patcher-authored `LtrFrameLayout` helper. Left/LHD leaves the panel on the left.
- The GUI includes visual LHD/RHD previews and uses a compact two-column layout for lower-resolution Windows displays.

## Portrait prevention

Testing in an Android 10 / API 29 1920x1080 emulator reproduced the same rotation seen on BYD hardware.

- `com.spotify.nowplayingqueue.queue.NowPlayingQueueActivity` is explicitly portrait-locked in the manifest.
- `com.spotify.lyrics.fullscreenview.page.LyricsFullscreenPageActivity` requests portrait at runtime.
- The supported Spotify 8.9.76.538 profile contains 12 known manifest portrait locks and 3 known runtime portrait requests.
- v0.6 fingerprints and replaces those portrait-family requests with `SCREEN_ORIENTATION_UNSPECIFIED` so the screens follow the current BYD landscape orientation.

## Branding

- Visible app name is independent of package identity.
- Launcher-icon hue can be adjusted 0–359 degrees.
- The `+` badge is optional and independent of hue.
- If the badge is off and hue is 0°, the original launcher artwork is preserved.

## AutoResume

The unused disabled MediaRoute provider service slot is repurposed as `<selected-package>.AutoResumeService` for `byd.intent.action.RESTORE_PLAYBACK`. The helper connects to Spotify's MediaBrowser service and calls the media session play transport control. BYD testing confirmed restore works for both supported clones; the helper logic is unchanged in v0.6.
