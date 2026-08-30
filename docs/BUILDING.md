# Build BYD Spotify Manager v1.0

1. Extract the project and open the folder containing `settings.gradle` in Android Studio.
2. Let Gradle sync finish.
3. Build with **Build > Build App Bundle(s) / APK(s) > Build APK(s)**.
4. Debug APK output is normally `app\build\outputs\apk\debug\app-debug.apk`.

Update the existing Manager with `adb install -r` to preserve its local SpotifyPlus signing identity.
