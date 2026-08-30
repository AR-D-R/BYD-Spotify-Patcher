# BYD Spotify Manager

Unofficial Android manager for creating BYD-friendly Spotify installations from user-supplied Spotify APKs.

## What changed in v1.0

This project has changed quite a bit from the old Windows patcher.

The main change is that the patching process has now moved **onto Android itself**. Instead of preparing the Spotify APK on a Windows PC, copying it over and installing it manually, the Manager can now patch and install Spotify directly on the BYD/Android system.

The idea was simply to make the whole process easier to use and maintain.

Compared with the previous Windows version, v1.0 adds:

- Android-native patching and installation.
- Support for both Spotify `9.1.78.2215` and `8.9.76.538`.
- Separate Spotify 9.1 and Spotify 8.9 settings inside the same Manager.
- Primary and Secondary installation slots.
- Direct Spotify 8.9 → 9.1 upgrades without uninstalling the slot first.
- Spotify 9.1 interface scaling: 100%, 120%, 140% and 160%.
- Spotify 9.1 left or right player positioning.
- BYD wide-screen fixes for Spotify 9.1.
- Spotify 8.9 Stock, Moderate and Large font options.
- Spotify 8.9 left/right side-panel layouts.
- Spotify 8.9 landscape/orientation fix.
- Custom app names.
- Launcher icon hue adjustment and optional `+` badge.
- Playback restoration after vehicle restart.
- Visible patching and installation progress.

The old Windows/Python patcher is still preserved as release/tag `v0.6` and on the `legacy/windows-v0.6` branch.

> **Spotify is not included with this project.**
> You need to provide your own original supported Spotify APK. The Manager patches it locally.

---

## Supported Spotify versions

| Profile | Supported version |
|---|---|
| Spotify 9.1 | `9.1.78.2215` | This is the version with the new UI and it seem to run a lot laggier and slower, might not be the best experience on older systems.
| Spotify 8.9 | `8.9.76.538` | This one still has most of the bells and wistles and is much quicker and lighter interface.

The Manager uses the following installation slots:

| Installation | Package |
|---|---|
| Official / OEM Spotify | `com.spotify.music` |
| Primary | `com.spotify.musia` |
| Secondary | `com.spotify.musib` |

Spotify 8.9 and 9.1 intentionally share the same Primary and Secondary packages.

This means you can have:

- OEM Spotify
- one Primary patched Spotify
- one Secondary patched Spotify

at the same time.

If a slot currently contains Spotify 8.9, it can be upgraded directly to Spotify 9.1.

Going from Spotify 9.1 back to 8.9 requires uninstalling that slot first because Android normally blocks app version downgrades.

---

## Spotify 9.1 options

Spotify 9.1 currently supports:

- BYD wide-screen layout fixes
- Interface scale: 100%, 120%, 140% or 160%
- 120% default interface scale
- Player position: LHS or RHS
- Custom visible app name
- Launcher icon hue adjustment
- Optional `+` launcher badge
- Optional optimised performance profile
- Optional playback restoration after vehicle restart

---

## Spotify 8.9 options

Spotify 8.9 currently supports:

- Stock, Moderate or Large font size
- Left / LHD side panel
- Right / RHD side panel
- BYD landscape/orientation fix
- Custom visible app name
- Launcher icon hue adjustment
- Optional `+` launcher badge
- Playback restoration after vehicle restart

---

# Installation

## 1. Install BYD Spotify Manager

Download the latest `BYDSpotifyManager-vX.X.apk` from the GitHub Releases page and install it on the BYD/Android system.

If Android asks for permission to install unknown apps, allow it for the app you are using to open the APK.

## 2. Open the Manager and choose the Spotify version

At the top of the Manager select either:

- **Spotify 9.1**
- **Spotify 8.9**

The settings shown below will change depending on the selected Spotify version.

<!-- IMAGE PLACEHOLDER: docs/images/02-select-profile.jpg -->

---

## 3. Choose Primary or Secondary

Select the slot you want to create or update.

- **Primary** installs as `com.spotify.musia`
- **Secondary** installs as `com.spotify.musib`

The two slots are independent, so they can use different names, icons and Spotify versions.

---

## 4. Supply the original Spotify APK

Press **Browse APK** and select the original supported Spotify APK.

If you dont have the file downloaded yet you can click **APKMIRROR**. This will open your browser and direct you to the page where you can download the correct version.
For this to work you need to install a 3rd party browser Firefox, or similar because the native browser wont let you download apk files.

The Manager will verify that the APK matches the selected Spotify profile before allowing it to be patched.

The Spotify APK is not bundled with this project and is not downloaded by the Manager.

---

## 5. Choose your settings

Configure the app name, icon and display options you want.

For Spotify 9.1 this includes interface scaling and player position.

For Spotify 8.9 this includes font size, panel side and the optional orientation fix.

---

## 6. Patch and install

Press the main button at the bottom of the Manager.

Depending on the current slot this may say something like:

- **Apply Changes**
- **Patch & Install**
- **Upgrade Slot to 9.1**

The Manager will patch, rebuild and prepare the APK locally.

---

## 7. Confirm the Android installation prompt

When Android shows the installation confirmation, approve it.

After pressing Install, return to the Manager and wait for the installation to complete. The Manager may remain at around 98% while Android is finishing the install.

---

## 8. Open SpotifyPlus

Once installation is complete, the new app will appear in the BYD application list using the name and icon you selected.

The default names are:

- Primary: **SpotifyPlus**
- Secondary: **SpotifyPlus2**

<!-- IMAGE PLACEHOLDER: docs/images/08-app-list.jpg -->

<!-- IMAGE PLACEHOLDER: docs/images/08-app-list2.jpg -->

---

# Updating Spotify

## 8.9 → 9.1

This can normally be done directly.

Select Spotify 9.1 in the Manager, select the same slot and patch/install it. Android should treat 9.1 as an update and preserve the app data for that slot.

## 9.1 → 8.9

This is a version downgrade, so Android normally blocks it.

The Manager will ask you to uninstall the current slot first. After uninstalling it, select Spotify 8.9 and install it again.

---

# Updating BYD Spotify Manager

Install newer Manager versions **over the existing Manager** rather than uninstalling it.

The Manager maintains local signing information used for the patched Spotify installations, so uninstalling the Manager during normal upgrades is not recommended.

---

# Building from source

See [docs/BUILDING.md](docs/BUILDING.md).

---

# Legacy Windows version

Versions before v1.0 used a Windows/Python patcher.

The final Windows release is still available as:

- release/tag `v0.6`
- branch `legacy/windows-v0.6`

The Windows version is kept for reference and for anyone who still wants to use the old workflow.

---

# Disclaimer

This is an unofficial independent project and is not affiliated with, endorsed by or sponsored by Spotify or BYD.

This repository does not distribute Spotify APKs or Spotify content. Users provide their own supported original Spotify APK and modifications are performed locally.

Spotify and the Spotify logo are trademarks of Spotify AB. BYD is a trademark of BYD Company Ltd.

## License

See [LICENSE](LICENSE).
