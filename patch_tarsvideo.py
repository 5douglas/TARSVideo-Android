from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")
SERVER_URL = "https://video.douglas.seg.br"


def read(rel):
    return (root / rel).read_text(encoding="utf-8")


def write(rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    if old not in text:
        raise SystemExit(f"Pattern not found in {rel}:\n{old}")
    write(rel, text.replace(old, new, 1))


# Branding
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


# Composite build: official VLC Android 3.7.1 UI
settings_path = root / "settings.gradle.kts"
settings = settings_path.read_text(encoding="utf-8")
vlc_composite = '''
includeBuild("../vlc-android-source") {
    dependencySubstitution {
        substitute(module("org.videolan.tars:vlc-android"))
            .using(project(":application:vlc-android"))
    }
}
'''
if 'includeBuild("../vlc-android-source")' not in settings:
    settings += "\n" + vlc_composite.strip() + "\n"
settings_path.write_text(settings, encoding="utf-8")


# App Gradle
gradle_path = root / "app/build.gradle.kts"
gradle = gradle_path.read_text(encoding="utf-8")
old_default = """    defaultConfig {
        minSdk"""
new_default = """    defaultConfig {
        applicationId = "br.seg.douglas.tarsvideo"
        minSdk"""
if old_default not in gradle:
    raise SystemExit("defaultConfig pattern not found")
gradle = gradle.replace(old_default, new_default, 1)

old_libass = "    implementation(libs.libass.media)"
new_libass = '''    implementation(libs.libass.media)

    // Full official VLC Android player UI (composite build)
    implementation("org.videolan.tars:vlc-android:3.7.1")'''
if old_libass not in gradle:
    raise SystemExit("libass dependency pattern not found")
gradle = gradle.replace(old_libass, new_libass, 1)

old_features = """    buildFeatures {
        buildConfig = true
        viewBinding = true
        compose = true
    }

    compileOptions {"""
new_features = """    buildFeatures {
        buildConfig = true
        viewBinding = true
        compose = true
    }

    packaging {
        jniLibs {
            pickFirsts += "**/libc++_shared.so"
        }
        resources {
            pickFirsts += "META-INF/*"
        }
    }

    compileOptions {"""
if old_features not in gradle:
    raise SystemExit("buildFeatures pattern not found")
gradle = gradle.replace(old_features, new_features, 1)

archive_old = 'base.archivesName.set("jellyfin-android-v${project.getVersionName()}")'
archive_new = 'base.archivesName.set("TARSVideo-v0.3")'
if archive_old not in gradle:
    raise SystemExit("archive name pattern not found")
gradle = gradle.replace(archive_old, archive_new, 1)
gradle_path.write_text(gradle, encoding="utf-8")


# Default player = external bridge (which now points to embedded VLC)
prefs_rel = "app/src/main/java/org/jellyfin/mobile/app/AppPreferences.kt"
prefs = read(prefs_rel)
old_pref = (
    "get() = sharedPreferences.getString("
    "Constants.PREF_VIDEO_PLAYER_TYPE, "
    "VideoPlayerType.EXO_PLAYER)!!"
)
new_pref = (
    "get() = sharedPreferences.getString("
    "Constants.PREF_VIDEO_PLAYER_TYPE, "
    "VideoPlayerType.EXTERNAL_PLAYER)!!"
)
if old_pref not in prefs:
    raise SystemExit("Video player preference pattern not found")
write(prefs_rel, prefs.replace(old_pref, new_pref, 1))

settings_rel = "app/src/main/java/org/jellyfin/mobile/settings/SettingsFragment.kt"
settings_text = read(settings_rel)
settings_text = settings_text.replace(
    "initialSelection = VideoPlayerType.EXO_PLAYER",
    "initialSelection = VideoPlayerType.EXTERNAL_PLAYER",
    1,
)
write(settings_rel, settings_text)


# Jellyfin -> official VLC VideoPlayerActivity
external_rel = "app/src/main/java/org/jellyfin/mobile/bridge/ExternalPlayer.kt"
external = read(external_rel)
anchor = "import org.jellyfin.mobile.player.interaction.PlayOptions\n"
vlc_import = (
    "import org.jellyfin.mobile.player.interaction.PlayOptions\n"
    "import org.videolan.vlc.gui.video.VideoPlayerActivity\n"
)
if "import org.videolan.vlc.gui.video.VideoPlayerActivity" not in external:
    if anchor not in external:
        raise SystemExit("ExternalPlayer import anchor not found")
    external = external.replace(anchor, vlc_import, 1)

old_intent = '''val playerIntent = Intent(Intent.ACTION_VIEW).apply {
            if (context.packageManager.isPackageInstalled(appPreferences.externalPlayerApp)) {
                component = getComponent(appPreferences.externalPlayerApp)
            }
            setDataAndType(url.toUri(), "video/*")'''
new_intent = '''val playerIntent = Intent(
            context,
            VideoPlayerActivity::class.java
        ).apply {
            action = Intent.ACTION_VIEW
            setDataAndType(url.toUri(), "video/*")'''
if old_intent not in external:
    raise SystemExit("ExternalPlayer intent block not found")
external = external.replace(old_intent, new_intent, 1)
write(external_rel, external)


# Initialize embedded VLC core inside TARSVideo Application
app_rel = "app/src/main/java/org/jellyfin/mobile/JellyfinApplication.kt"
app = read(app_rel)
import_anchor = "import android.webkit.WebView\n"
imports = '''import android.webkit.WebView
import org.videolan.libvlc.FactoryManager
import org.videolan.libvlc.LibVLCFactory
import org.videolan.libvlc.MediaFactory
import org.videolan.libvlc.interfaces.ILibVLCFactory
import org.videolan.libvlc.interfaces.IMediaFactory
import org.videolan.resources.AppContextProvider
'''
if "import org.videolan.resources.AppContextProvider" not in app:
    if import_anchor not in app:
        raise SystemExit("JellyfinApplication import anchor not found")
    app = app.replace(import_anchor, imports, 1)

old_super = '''        super.onCreate()

        // Setup logging'''
new_super = '''        super.onCreate()

        // Initialize the embedded official VLC Android stack.
        AppContextProvider.init(this)
        FactoryManager.registerFactory(IMediaFactory.factoryId, MediaFactory())
        FactoryManager.registerFactory(ILibVLCFactory.factoryId, LibVLCFactory())

        // Setup logging'''
if old_super not in app:
    raise SystemExit("JellyfinApplication onCreate anchor not found")
app = app.replace(old_super, new_super, 1)
write(app_rel, app)


# Fixed TARSVideo server
connect_rel = "app/src/main/java/org/jellyfin/mobile/ui/screens/connect/ConnectScreen.kt"
connect = read(connect_rel)
old_connect = '''    Surface(color = MaterialTheme.colors.background) {
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
    }'''
new_connect = f'''    androidx.compose.runtime.LaunchedEffect(Unit) {{
        mainViewModel.switchServer("{SERVER_URL}")
    }}

    Surface(color = MaterialTheme.colors.background) {{
        androidx.compose.foundation.layout.Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = androidx.compose.ui.Alignment.Center,
        ) {{
            androidx.compose.material.CircularProgressIndicator()
        }}
    }}'''
if old_connect not in connect:
    raise SystemExit("ConnectScreen body pattern not found")
write(connect_rel, connect.replace(old_connect, new_connect, 1))


# Web app: no MultiServer capability => no Select Server menu
native_shell_rel = "app/src/main/assets/native/nativeshell.js"
native_shell = read(native_shell_rel)
native_shell = native_shell.replace('    "multiserver",\n', "", 1)
write(native_shell_rel, native_shell)


# Native server-change fallback disabled + mask web loading logo
webview_rel = "app/src/main/java/org/jellyfin/mobile/webapp/WebViewFragment.kt"
webview = read(webview_rel)
old_listener = '''        webViewBinding!!.useDifferentServerButton.setOnClickListener {
            webView.removeCallbacks(timeoutRunnable)
            webView.stopLoading()
            webViewBinding!!.loadingContainer.isVisible = false
            onSelectServer(error = false)
        }'''
new_listener = '''        webViewBinding!!.useDifferentServerButton.isVisible = false'''
if old_listener not in webview:
    raise SystemExit("useDifferentServerButton listener pattern not found")
webview = webview.replace(old_listener, new_listener, 1)

old_connected = '''                runOnUiThread {
                    webViewBinding.loadingContainer.isVisible = false
                    webView.fadeIn()
                }'''
new_connected = '''                runOnUiThread {
                    webViewBinding.loadingContainer.isVisible = true
                    webView.postDelayed({
                        webViewBinding?.loadingContainer?.isVisible = false
                        webViewBinding?.webView?.fadeIn()
                    }, 1400L)
                }'''
if old_connected not in webview:
    raise SystemExit("WebView connected block not found")
webview = webview.replace(old_connected, new_connected, 1)
write(webview_rel, webview)


# Native web loading overlay uses TARS icon
fragment_rel = "app/src/main/res/layout/fragment_webview.xml"
fragment = read(fragment_rel)
fragment = fragment.replace(
    'android:visibility="gone"\n        tools:visibility="visible">',
    'android:visibility="visible"\n        tools:visibility="visible">',
    1,
)
old_progress = '''        <com.google.android.material.progressindicator.CircularProgressIndicator
            android:id="@+id/progress_indicator"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="center"
            android:indeterminate="true"
            app:indicatorColor="@color/jellyfin_accent"
            app:layout_constraintBottom_toBottomOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintTop_toTopOf="parent" />'''
new_progress = '''        <ImageView
            android:id="@+id/progress_indicator"
            android:layout_width="132dp"
            android:layout_height="132dp"
            android:contentDescription="@string/app_name"
            android:scaleType="centerInside"
            android:src="@drawable/tars_icon_padded"
            app:layout_constraintBottom_toBottomOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintTop_toTopOf="parent" />'''
if old_progress not in fragment:
    raise SystemExit("WebView progress indicator pattern not found")
fragment = fragment.replace(old_progress, new_progress, 1)
fragment = fragment.replace(
    'android:text="@string/button_use_different_server"',
    'android:text="@string/button_use_different_server"\n            android:visibility="gone"',
    1,
)
write(fragment_rel, fragment)


# Adaptive launcher + splash padding
write(
    "app/src/main/res/drawable/tars_icon_padded.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<inset xmlns:android="http://schemas.android.com/apk/res/android"
    android:drawable="@drawable/tars_icon"
    android:insetLeft="18dp"
    android:insetTop="18dp"
    android:insetRight="18dp"
    android:insetBottom="18dp" />
''',
)
write(
    "app/src/main/res/values/tars_colors.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="tars_launcher_background">#101014</color>
</resources>
''',
)
write(
    "app/src/main/res/mipmap-anydpi-v26/tars_launcher.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/tars_launcher_background" />
    <foreground android:drawable="@drawable/tars_icon_padded" />
</adaptive-icon>
''',
)
write(
    "app/src/main/res/mipmap-anydpi/tars_launcher.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/tars_launcher_background" />
    <item android:drawable="@drawable/tars_icon_padded" />
</layer-list>
''',
)

manifest_rel = "app/src/main/AndroidManifest.xml"
manifest = read(manifest_rel)
manifest = manifest.replace(
    'android:icon="@mipmap/ic_launcher"',
    'android:icon="@mipmap/tars_launcher"',
    1,
)
manifest = manifest.replace(
    'android:roundIcon="@mipmap/ic_launcher_round"',
    'android:roundIcon="@mipmap/tars_launcher"',
    1,
)
write(manifest_rel, manifest)

styles_rel = "app/src/main/res/values/styles.xml"
styles = read(styles_rel)
styles = styles.replace(
    '<item name="windowSplashScreenAnimatedIcon">@drawable/ic_splash</item>',
    '<item name="windowSplashScreenAnimatedIcon">@drawable/tars_icon_padded</item>',
    1,
)
write(styles_rel, styles)

print("TARSVideo v0.3 patch applied successfully")
