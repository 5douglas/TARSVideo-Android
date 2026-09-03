from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")


def replace_once(relative_path, old, new):
    path = root / relative_path
    text = path.read_text(encoding="utf-8")

    if old not in text:
        raise SystemExit(
            f"Pattern not found in {relative_path}:\n{old}"
        )

    path.write_text(
        text.replace(old, new, 1),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------

replace_once(
    "app/src/main/res/values/strings_donottranslate.xml",
    '<string name="app_name" translatable="false">Jellyfin</string>',
    '<string name="app_name" translatable="false">TARSVideo</string>',
)

replace_once(
    "app/src/main/res/values/strings_donottranslate.xml",
    '<string name="app_name_short" translatable="false">Jellyfin</string>',
    '<string name="app_name_short" translatable="false">TARSVideo</string>',
)

replace_once(
    "app/src/debug/res/values/strings_donottranslate.xml",
    '<string name="app_name" translatable="false">Jellyfin Debug</string>',
    '<string name="app_name" translatable="false">TARSVideo</string>',
)


# ---------------------------------------------------------------------
# Gradle: package, LibVLC, native-lib conflict, APK name
# ---------------------------------------------------------------------

gradle_path = root / "app/build.gradle.kts"
gradle_text = gradle_path.read_text(encoding="utf-8")

old_default_config = """    defaultConfig {
        minSdk"""

new_default_config = """    defaultConfig {
        applicationId = "br.seg.douglas.tarsvideo"
        minSdk"""

if old_default_config not in gradle_text:
    raise SystemExit("defaultConfig pattern not found")

gradle_text = gradle_text.replace(
    old_default_config,
    new_default_config,
    1,
)

old_libass = """    implementation(libs.libass.media)"""

new_libass = """    implementation(libs.libass.media)
    implementation("org.videolan.android:libvlc-all:3.7.5")"""

if old_libass not in gradle_text:
    raise SystemExit("libass dependency pattern not found")

gradle_text = gradle_text.replace(
    old_libass,
    new_libass,
    1,
)

old_build_features = """    buildFeatures {
        buildConfig = true
        viewBinding = true
        compose = true
    }

    compileOptions {"""

new_build_features = """    buildFeatures {
        buildConfig = true
        viewBinding = true
        compose = true
    }

    packaging {
        jniLibs {
            pickFirsts += "**/libc++_shared.so"
        }
    }

    compileOptions {"""

if old_build_features not in gradle_text:
    raise SystemExit("buildFeatures pattern not found")

gradle_text = gradle_text.replace(
    old_build_features,
    new_build_features,
    1,
)

old_archive_name = (
    'base.archivesName.set('
    '"jellyfin-android-v${project.getVersionName()}"'
    ')'
)

new_archive_name = (
    'base.archivesName.set('
    '"TARSVideo-v${project.getVersionName()}"'
    ')'
)

if old_archive_name not in gradle_text:
    raise SystemExit("archive name pattern not found")

gradle_text = gradle_text.replace(
    old_archive_name,
    new_archive_name,
    1,
)

gradle_path.write_text(
    gradle_text,
    encoding="utf-8",
)


# ---------------------------------------------------------------------
# Default player = internal VLC bridge
# ---------------------------------------------------------------------

preferences_path = (
    root
    / "app/src/main/java/org/jellyfin/mobile/app/AppPreferences.kt"
)

preferences_text = preferences_path.read_text(
    encoding="utf-8"
)

old_preference = (
    "get() = sharedPreferences.getString("
    "Constants.PREF_VIDEO_PLAYER_TYPE, "
    "VideoPlayerType.EXO_PLAYER)!!"
)

new_preference = (
    "get() = sharedPreferences.getString("
    "Constants.PREF_VIDEO_PLAYER_TYPE, "
    "VideoPlayerType.EXTERNAL_PLAYER)!!"
)

if old_preference not in preferences_text:
    raise SystemExit(
        "Video player preference pattern not found"
    )

preferences_text = preferences_text.replace(
    old_preference,
    new_preference,
    1,
)

preferences_path.write_text(
    preferences_text,
    encoding="utf-8",
)


settings_path = (
    root
    / "app/src/main/java/org/jellyfin/mobile/settings/SettingsFragment.kt"
)

settings_text = settings_path.read_text(
    encoding="utf-8"
)

if (
    "initialSelection = VideoPlayerType.EXO_PLAYER"
    in settings_text
):
    settings_text = settings_text.replace(
        "initialSelection = VideoPlayerType.EXO_PLAYER",
        "initialSelection = VideoPlayerType.EXTERNAL_PLAYER",
        1,
    )

settings_path.write_text(
    settings_text,
    encoding="utf-8",
)


# ---------------------------------------------------------------------
# Redirect Jellyfin external player bridge to embedded VLC.
# Also pass Jellyfin item ID so the player can search remote subtitles.
# ---------------------------------------------------------------------

external_path = (
    root
    / "app/src/main/java/org/jellyfin/mobile/bridge/ExternalPlayer.kt"
)

external = external_path.read_text(
    encoding="utf-8"
)

import_anchor = (
    "import org.jellyfin.mobile.player.interaction.PlayOptions\n"
)

new_import = (
    "import org.jellyfin.mobile.player.interaction.PlayOptions\n"
    "import org.jellyfin.mobile.player.vlc.InternalVlcPlayerActivity\n"
)

if (
    "import org.jellyfin.mobile.player.vlc."
    "InternalVlcPlayerActivity"
    not in external
):
    if import_anchor not in external:
        raise SystemExit(
            "ExternalPlayer import anchor not found"
        )

    external = external.replace(
        import_anchor,
        new_import,
        1,
    )


old_intent = """val playerIntent = Intent(Intent.ACTION_VIEW).apply {
            if (context.packageManager.isPackageInstalled(appPreferences.externalPlayerApp)) {
                component = getComponent(appPreferences.externalPlayerApp)
            }
            setDataAndType(url.toUri(), "video/*")
            putExtra("title", source.getName(context))
            putExtra("position", source.startTime.inWholeMilliseconds.toInt())"""

new_intent = """val playerIntent = Intent(
            context,
            InternalVlcPlayerActivity::class.java
        ).apply {
            setDataAndType(url.toUri(), "video/*")
            putExtra("title", source.getName(context))
            putExtra("item_id", source.itemId.toString())
            putExtra("media_source_id", source.id)
            putExtra("position", source.startTime.inWholeMilliseconds.toInt())"""

if old_intent not in external:
    raise SystemExit(
        "ExternalPlayer intent block not found"
    )

external = external.replace(
    old_intent,
    new_intent,
    1,
)

external_path.write_text(
    external,
    encoding="utf-8",
)


# ---------------------------------------------------------------------
# Skip server selection: fixed TARSVideo server.
# Clean installs go directly to this server.
# ---------------------------------------------------------------------

connect_path = (
    root
    / "app/src/main/java/org/jellyfin/mobile/ui/screens/connect/ConnectScreen.kt"
)

connect = connect_path.read_text(
    encoding="utf-8"
)

old_connect_body = """    Surface(color = MaterialTheme.colors.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .padding(horizontal = 16.dp),
        ) {
            LogoHeader()
            ServerSelection(
                showExternalConnectionError = showExternalConnectionError,
                onConnected = { hostname ->
                    mainViewModel.switchServer(hostname)
                },
            )
            StyledTextButton(
                onClick = { activityEventHandler.emit(ActivityEvent.OpenDownloads) },
                text = stringResource(R.string.view_downloads),
            )
        }
    }"""

new_connect_body = """    androidx.compose.runtime.LaunchedEffect(Unit) {
        mainViewModel.switchServer("https://video.douglas.seg.br")
    }

    Surface(color = MaterialTheme.colors.background) {
        androidx.compose.foundation.layout.Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = androidx.compose.ui.Alignment.Center,
        ) {
            androidx.compose.material.CircularProgressIndicator()
        }
    }"""

if old_connect_body not in connect:
    raise SystemExit(
        "ConnectScreen body pattern not found"
    )

connect = connect.replace(
    old_connect_body,
    new_connect_body,
    1,
)

connect_path.write_text(
    connect,
    encoding="utf-8",
)


# ---------------------------------------------------------------------
# App icon + splash
# ---------------------------------------------------------------------

manifest_path = (
    root
    / "app/src/main/AndroidManifest.xml"
)

manifest = manifest_path.read_text(
    encoding="utf-8"
)

manifest = manifest.replace(
    'android:icon="@mipmap/ic_launcher"',
    'android:icon="@drawable/tars_icon"',
    1,
)

manifest = manifest.replace(
    'android:roundIcon="@mipmap/ic_launcher_round"',
    'android:roundIcon="@drawable/tars_icon"',
    1,
)


# Register internal VLC Activity
activity_marker = (
    '        <activity\n'
    '            android:name=".MainActivity"'
)

vlc_activity = (
    '        <activity\n'
    '            android:name=".player.vlc.InternalVlcPlayerActivity"\n'
    '            android:configChanges="orientation|screenSize|keyboardHidden"\n'
    '            android:exported="false"\n'
    '            android:screenOrientation="sensorLandscape"\n'
    '            android:supportsPictureInPicture="true"\n'
    '            android:theme="@style/Theme.AppCompat.NoActionBar" />\n\n'
    '        <activity\n'
    '            android:name=".MainActivity"'
)

if "InternalVlcPlayerActivity" not in manifest:
    if activity_marker not in manifest:
        raise SystemExit(
            "MainActivity manifest marker not found"
        )

    manifest = manifest.replace(
        activity_marker,
        vlc_activity,
        1,
    )

manifest_path.write_text(
    manifest,
    encoding="utf-8",
)


styles_path = (
    root
    / "app/src/main/res/values/styles.xml"
)

styles = styles_path.read_text(
    encoding="utf-8"
)

if (
    '<item name="windowSplashScreenAnimatedIcon">'
    '@drawable/ic_splash</item>'
    in styles
):
    styles = styles.replace(
        '<item name="windowSplashScreenAnimatedIcon">'
        '@drawable/ic_splash</item>',
        '<item name="windowSplashScreenAnimatedIcon">'
        '@drawable/tars_icon</item>',
        1,
    )

styles_path.write_text(
    styles,
    encoding="utf-8",
)


print(
    "TARSVideo v0.2 patch applied successfully"
)
