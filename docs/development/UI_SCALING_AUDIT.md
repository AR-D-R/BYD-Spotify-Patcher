# BYD Spotify Manager v1.0 — UI notes

## Spotify 9.1 scaling

The supported presets are 100%, 120%, 140% and 160%. New 9.1 slot settings default to 120%.

Modern Spotify/Compose typography is scaled through the Android-backed Compose density creation path, while classic Android resource dimensions are scaled from the stock resource baseline. At 100%, those scale patches are not applied.

The BYD wide-screen dimension map is applied separately. The playlist/content width uses the 960dp setting.

## Queue shuffle icon

The Queue Shuffle/Smart Shuffle vectors retain their stock 24dp intrinsic size so the Shuffle action does not become larger than Repeat and Timer at enlarged interface scales.

## Player position

RHS keeps Spotify's normal large-screen placement. LHS uses the runtime outer-coordinate mirror hook while preserving each child's normal LTR rendering. This lets Spotify keep ownership of its expanded/collapsed state machine and animations while moving the player/navigation surfaces to the opposite side.

## Launcher badge

When hue or the + badge is enabled, the 9.1 adaptive foreground is generated as a raster drawable using the same badge rendering path as 8.9. This avoids launcher-specific clipping/placement differences on BYD systems.
