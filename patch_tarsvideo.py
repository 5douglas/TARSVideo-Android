from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")
SERVER_URL = "https://video.douglas.seg.br"
APP_VERSION = "0.4.1"


def read(rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
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


# Package/application identity and APK name
gradle_rel = "app/build.gradle.kts"
gradle = read(gradle_rel)
old_default = "    defaultConfig {\n        minSdk"
new_default = "    defaultConfig {\n        applicationId = \"br.seg.douglas.tarsvideo\"\n        minSdk"
if old_default not in gradle:
    raise SystemExit("defaultConfig pattern not found")
gradle = gradle.replace(old_default, new_default, 1)

archive_old = 'base.archivesName.set("jellyfin-android-v${project.getVersionName()}")'
archive_new = f'base.archivesName.set("TARSVideo-v{APP_VERSION}")'
if archive_old not in gradle:
    raise SystemExit("archive name pattern not found")
gradle = gradle.replace(archive_old, archive_new, 1)
write(gradle_rel, gradle)


# One-time migration from the old embedded-VLC build back to Jellyfin native.
app_rel = "app/src/main/java/org/jellyfin/mobile/JellyfinApplication.kt"
app = read(app_rel)
old_super = "        super.onCreate()\n\n        // Setup logging"
new_super = '''        super.onCreate()

        // TARSVideo v0.4: migrate old VLC-based installs back to the
        // official Jellyfin native player without resetting server/login data.
        val tarsPreferences = getSharedPreferences(
            "${packageName}_preferences",
            android.content.Context.MODE_PRIVATE,
        )
        if (!tarsPreferences.getBoolean("tarsvideo_native_player_v040", false)) {
            tarsPreferences.edit()
                .remove("pref_video_player_type")
                .putBoolean("tarsvideo_native_player_v040", true)
                .apply()
        }

        // Setup logging'''
if old_super not in app:
    raise SystemExit("JellyfinApplication onCreate anchor not found")
write(app_rel, app.replace(old_super, new_super, 1))


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


# Remove Select Server capability from the web shell.
native_shell_rel = "app/src/main/assets/native/nativeshell.js"
native_shell = read(native_shell_rel)
if '    "multiserver",\n' not in native_shell:
    raise SystemExit("nativeshell multiserver capability anchor not found")
write(native_shell_rel, native_shell.replace('    "multiserver",\n', "", 1))


# JavaScript Injector / TARS Chat compatibility checks.
web_utils_rel = "app/src/main/java/org/jellyfin/mobile/utils/WebViewUtils.kt"
web_utils = read(web_utils_rel)
for required in ("javaScriptEnabled = true", "domStorageEnabled = true"):
    if required not in web_utils:
        raise SystemExit(f"WebView JavaScript compatibility missing: {required}")

web_client_rel = "app/src/main/java/org/jellyfin/mobile/webapp/JellyfinWebViewClient.kt"
web_client = read(web_client_rel)
for required in (
    'assetsPathHandler.inject("native/injectionScript.js")',
    'path.contains("/native/")',
):
    if required not in web_client:
        raise SystemExit(f"Jellyfin native web injection bridge missing: {required}")

webview_rel = "app/src/main/java/org/jellyfin/mobile/webapp/WebViewFragment.kt"
webview = read(webview_rel)
if "settings.applyDefault()" not in webview:
    raise SystemExit("WebView settings.applyDefault missing")
if 'loadUrl("${server.hostname.trimEnd(\'/\')}/")' not in webview:
    raise SystemExit("WebView server loadUrl missing")

old_listener = '''        webViewBinding!!.useDifferentServerButton.setOnClickListener {
            webView.removeCallbacks(timeoutRunnable)
            webView.stopLoading()
            webViewBinding!!.loadingContainer.isVisible = false
            onSelectServer(error = false)
        }'''
if old_listener not in webview:
    raise SystemExit("useDifferentServerButton listener pattern not found")
webview = webview.replace(
    old_listener,
    "        webViewBinding!!.useDifferentServerButton.isVisible = false",
    1,
)

old_settings = "        settings.applyDefault()\n"
new_settings = '''        // TARSVideo: keep the full server web runtime enabled so server-side
        // JavaScript Injector scripts (including TARS Chat) run in this WebView.
        settings.applyDefault()
'''
if old_settings not in webview:
    raise SystemExit("WebView settings.applyDefault anchor not found")
webview = webview.replace(old_settings, new_settings, 1)
write(webview_rel, webview)


# TARSVideo loading overlay.
# v0.4.1 uses the TARS artwork directly, without the old extra inset.
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
            android:src="@drawable/tars_icon"
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


# Launcher + Android splash.
# v0.4.1:
# - no Jellyfin/TARS logo in the Android system splash
# - no extra 24dp inset around the launcher foreground
# - TARS icon fills the adaptive icon area much better
write(
    "app/src/main/res/drawable/tars_empty_splash.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <size
        android:width="1dp"
        android:height="1dp" />
    <solid android:color="@android:color/transparent" />
</shape>
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
    <foreground android:drawable="@drawable/tars_icon" />
</adaptive-icon>
''',
)

write(
    "app/src/main/res/mipmap-anydpi/tars_launcher.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/tars_launcher_background" />
    <item android:drawable="@drawable/tars_icon" />
</layer-list>
''',
)

manifest_rel = "app/src/main/AndroidManifest.xml"
manifest = read(manifest_rel)
if 'android:icon="@mipmap/ic_launcher"' not in manifest:
    raise SystemExit("Manifest launcher icon anchor not found")
manifest = manifest.replace(
    'android:icon="@mipmap/ic_launcher"',
    'android:icon="@mipmap/tars_launcher"',
    1,
)

if 'android:roundIcon="@mipmap/ic_launcher_round"' not in manifest:
    raise SystemExit("Manifest round launcher icon anchor not found")
manifest = manifest.replace(
    'android:roundIcon="@mipmap/ic_launcher_round"',
    'android:roundIcon="@mipmap/tars_launcher"',
    1,
)
write(manifest_rel, manifest)

styles_rel = "app/src/main/res/values/styles.xml"
styles = read(styles_rel)

old_splash = '<item name="windowSplashScreenAnimatedIcon">@drawable/ic_splash</item>'
new_splash = '<item name="windowSplashScreenAnimatedIcon">@drawable/tars_empty_splash</item>'
if old_splash not in styles:
    raise SystemExit("Splash icon anchor not found")

styles = styles.replace(old_splash, new_splash, 1)
write(styles_rel, styles)


print(f"TARSVideo Android v{APP_VERSION} patch applied successfully")
print("PLAYER=JELLYFIN_NATIVE_EXOPLAYER")
print("JAVASCRIPT_INJECTOR_COMPAT=YES")
print("SYSTEM_SPLASH_ICON=REMOVED")
print("LAUNCHER_ICON_PADDING=REMOVED")
print(f"SERVER={SERVER_URL}")
