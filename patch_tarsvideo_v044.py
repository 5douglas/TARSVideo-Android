from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")
APP_VERSION = "0.4.4"
APPLICATION_ID = "tars.video"
FIREBASE_BOM = "34.19.0"
GOOGLE_SERVICES_PLUGIN = "4.5.0"
UPDATE_MANIFEST_URL = "https://github.com/5douglas/TARSVideo-Android/releases/latest/download/update.json"


def read(rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_once(rel: str, old: str, new: str, label: str) -> None:
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 anchor in {rel}, found {count}")
    write(rel, text.replace(old, new, 1))


# ============================================================
# TARSVideo v0.4.4
# - permanent application id: tars.video
# - release signing is supplied by CI through Gradle env properties
# - Firebase Cloud Messaging admin push (works with UI closed)
# - removes the v0.4.3 WebView/chat-message notification observer
# - built-in signed APK updater using GitHub Releases
# - keeps the v0.4.3 stable DeviceId / SyncPlay fix
# ============================================================


# ------------------------------------------------------------
# Gradle: package, version/archive, Firebase plugin/dependency
# ------------------------------------------------------------
gradle_rel = "app/build.gradle.kts"
gradle = read(gradle_rel)

old_app_id = '        applicationId = "br.seg.douglas.tarsvideo"'
new_app_id = f'        applicationId = "{APPLICATION_ID}"'
if old_app_id not in gradle:
    raise SystemExit("v0.4.2 applicationId anchor not found")
gradle = gradle.replace(old_app_id, new_app_id, 1)

old_archive = 'base.archivesName.set("TARSVideo-v0.4.3")'
new_archive = f'base.archivesName.set("TARSVideo-v{APP_VERSION}")'
if old_archive not in gradle:
    raise SystemExit("v0.4.3 archive anchor not found")
gradle = gradle.replace(old_archive, new_archive, 1)

plugins_anchor = '''    alias(libs.plugins.android.junit5)\n}'''
plugins_new = f'''    alias(libs.plugins.android.junit5)\n    id("com.google.gms.google-services") version "{GOOGLE_SERVICES_PLUGIN}"\n}}'''
if plugins_anchor not in gradle:
    raise SystemExit("Gradle plugins anchor not found")
gradle = gradle.replace(plugins_anchor, plugins_new, 1)

deps_anchor = '''    // Monitoring\n    implementation(libs.slf4j.timber)'''
firebase_deps = f'''    // TARSVideo v0.4.4 - Firebase Cloud Messaging\n    implementation(platform("com.google.firebase:firebase-bom:{FIREBASE_BOM}"))\n    implementation("com.google.firebase:firebase-messaging")\n\n    // Monitoring\n    implementation(libs.slf4j.timber)'''
if deps_anchor not in gradle:
    raise SystemExit("Gradle dependency anchor not found")
gradle = gradle.replace(deps_anchor, firebase_deps, 1)

write(gradle_rel, gradle)


# ------------------------------------------------------------
# Remove v0.4.3 WebView notification observer.
# Push is now FCM-only and admin-notification-only.
# ------------------------------------------------------------
injection_rel = "app/src/main/assets/native/injectionScript.js"
injection = read(injection_rel)
observer_line = "        '/native/tarsnotifications.js',\n"
if observer_line not in injection:
    raise SystemExit("v0.4.3 notification observer anchor not found")
injection = injection.replace(observer_line, "", 1)
write(injection_rel, injection)

write(
    "app/src/main/assets/native/tarsnotifications.js",
    """(() => {
    'use strict';
    // v0.4.4: WebView/chat-message notifications intentionally disabled.
    // Administrative notifications are delivered by Firebase Cloud Messaging.
})();
""",
)


# ------------------------------------------------------------
# Expose the currently configured ApiClient to TARS push code.
# The v0.4.3 stable DeviceId patch remains untouched.
# ------------------------------------------------------------
api_rel = "app/src/main/java/org/jellyfin/mobile/app/ApiClientController.kt"
api = read(api_rel)
api_anchor = '''    fun getApiClient(server: Long, user: Long): ApiClient {'''
api_insert = '''    fun currentApiClient(): ApiClient = apiClient\n\n    fun getApiClient(server: Long, user: Long): ApiClient {'''
if api_anchor not in api:
    raise SystemExit("ApiClientController currentApiClient anchor not found")
api = api.replace(api_anchor, api_insert, 1)
write(api_rel, api)


# ------------------------------------------------------------
# Register FCM token whenever Jellyfin Web provides a valid user token.
# ------------------------------------------------------------
vm_rel = "app/src/main/java/org/jellyfin/mobile/MainViewModel.kt"
vm = read(vm_rel)

vm_import_anchor = '''import org.jellyfin.mobile.data.entity.UserEntity\nimport java.util.UUID'''
vm_import_new = '''import org.jellyfin.mobile.data.entity.UserEntity\nimport org.jellyfin.mobile.tars.TarsPushManager\nimport java.util.UUID'''
if vm_import_anchor not in vm:
    raise SystemExit("MainViewModel import anchor not found")
vm = vm.replace(vm_import_anchor, vm_import_new, 1)

vm_setup_anchor = '''    suspend fun setupUser(serverId: Long, userId: UUID, accessToken: String) {\n        apiClientController.setupUser(serverId, userId, accessToken)\n        refreshUser()\n    }'''
vm_setup_new = '''    suspend fun setupUser(serverId: Long, userId: UUID, accessToken: String) {\n        apiClientController.setupUser(serverId, userId, accessToken)\n        TarsPushManager.register(\n            context = getApplication(),\n            apiClient = apiClientController.currentApiClient(),\n        )\n        refreshUser()\n    }'''
if vm_setup_anchor not in vm:
    raise SystemExit("MainViewModel setupUser anchor not found")
vm = vm.replace(vm_setup_anchor, vm_setup_new, 1)
write(vm_rel, vm)


# ------------------------------------------------------------
# Application initialization: admin notification channel + FCM auto-init.
# ------------------------------------------------------------
app_rel = "app/src/main/java/org/jellyfin/mobile/JellyfinApplication.kt"
app = read(app_rel)

app_import_anchor = '''import org.jellyfin.mobile.data.databaseModule\nimport org.jellyfin.mobile.utils.JellyTree'''
app_import_new = '''import org.jellyfin.mobile.data.databaseModule\nimport org.jellyfin.mobile.tars.TarsPushManager\nimport org.jellyfin.mobile.utils.JellyTree'''
if app_import_anchor not in app:
    raise SystemExit("JellyfinApplication import anchor not found")
app = app.replace(app_import_anchor, app_import_new, 1)

# Base v0.4.2 inserts its migration immediately after super.onCreate().
app_oncreate_anchor = '''        super.onCreate()\n\n        // TARSVideo v0.4: migrate old VLC-based installs back to the'''
app_oncreate_new = '''        super.onCreate()\n\n        TarsPushManager.initialize(this)\n\n        // TARSVideo v0.4: migrate old VLC-based installs back to the'''
if app_oncreate_anchor not in app:
    raise SystemExit("JellyfinApplication onCreate anchor not found")
app = app.replace(app_oncreate_anchor, app_oncreate_new, 1)
write(app_rel, app)


# ------------------------------------------------------------
# MainActivity: notification permission + updater lifecycle.
# ------------------------------------------------------------
main_rel = "app/src/main/java/org/jellyfin/mobile/MainActivity.kt"
main = read(main_rel)

main_import_anchor = '''import org.jellyfin.mobile.setup.ConnectFragment\nimport org.jellyfin.mobile.utils.AndroidVersion'''
main_import_new = '''import org.jellyfin.mobile.setup.ConnectFragment\nimport org.jellyfin.mobile.tars.TarsPushManager\nimport org.jellyfin.mobile.tars.TarsUpdater\nimport org.jellyfin.mobile.utils.AndroidVersion'''
if main_import_anchor not in main:
    raise SystemExit("MainActivity TARS import anchor not found")
main = main.replace(main_import_anchor, main_import_new, 1)

main_content_anchor = '''        super.onCreate(savedInstanceState)\n        setContentView(R.layout.activity_main)\n\n        // Check WebView support'''
main_content_new = '''        super.onCreate(savedInstanceState)\n        setContentView(R.layout.activity_main)\n\n        TarsPushManager.requestNotificationPermission(this)\n        TarsUpdater.checkForUpdates(this)\n\n        // Check WebView support'''
if main_content_anchor not in main:
    raise SystemExit("MainActivity onCreate anchor not found")
main = main.replace(main_content_anchor, main_content_new, 1)

main_start_anchor = '''    override fun onStart() {\n        super.onStart()\n        orientationListener.enable()\n    }'''
main_start_new = '''    override fun onResume() {\n        super.onResume()\n        TarsUpdater.resumePendingUpdate(this)\n    }\n\n    override fun onStart() {\n        super.onStart()\n        orientationListener.enable()\n    }'''
if main_start_anchor not in main:
    raise SystemExit("MainActivity onStart anchor not found")
main = main.replace(main_start_anchor, main_start_new, 1)
write(main_rel, main)


# ------------------------------------------------------------
# Manifest: updater permission/provider + Firebase service/defaults.
# ------------------------------------------------------------
manifest_rel = "app/src/main/AndroidManifest.xml"
manifest = read(manifest_rel)

internet_anchor = '''    <uses-permission android:name="android.permission.INTERNET" />'''
internet_new = '''    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />'''
if internet_anchor not in manifest:
    raise SystemExit("Manifest INTERNET permission anchor not found")
manifest = manifest.replace(internet_anchor, internet_new, 1)

app_open_anchor = '''    <application\n        android:name=".JellyfinApplication"'''
if app_open_anchor not in manifest:
    raise SystemExit("Manifest application anchor not found")

remote_service_anchor = '''        <service\n            android:name=".webapp.RemotePlayerService"'''
services_new = '''        <service\n            android:name=".tars.TarsFirebaseMessagingService"\n            android:exported="false">\n            <intent-filter>\n                <action android:name="com.google.firebase.MESSAGING_EVENT" />\n            </intent-filter>\n        </service>\n\n        <provider\n            android:name="androidx.core.content.FileProvider"\n            android:authorities="${applicationId}.update-provider"\n            android:exported="false"\n            android:grantUriPermissions="true">\n            <meta-data\n                android:name="android.support.FILE_PROVIDER_PATHS"\n                android:resource="@xml/tars_update_paths" />\n        </provider>\n\n        <meta-data\n            android:name="com.google.firebase.messaging.default_notification_icon"\n            android:resource="@drawable/tars_notification" />\n        <meta-data\n            android:name="com.google.firebase.messaging.default_notification_channel_id"\n            android:value="tarsvideo_admin" />\n\n        <service\n            android:name=".webapp.RemotePlayerService"'''
if remote_service_anchor not in manifest:
    raise SystemExit("Manifest RemotePlayerService anchor not found")
manifest = manifest.replace(remote_service_anchor, services_new, 1)
write(manifest_rel, manifest)

write(
    "app/src/main/res/xml/tars_update_paths.xml",
    '''<?xml version="1.0" encoding="utf-8"?>\n<paths xmlns:android="http://schemas.android.com/apk/res/android">\n    <external-files-path\n        name="tars_updates"\n        path="Download/" />\n</paths>\n''',
)


# ------------------------------------------------------------
# FCM native implementation.
# ------------------------------------------------------------
write(
    "app/src/main/java/org/jellyfin/mobile/tars/TarsPushManager.kt",
    r'''package org.jellyfin.mobile.tars

import android.Manifest
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessaging
import org.jellyfin.mobile.BuildConfig
import org.jellyfin.mobile.MainActivity
import org.jellyfin.mobile.R
import org.jellyfin.mobile.utils.requestPermission
import org.jellyfin.sdk.api.client.ApiClient
import org.json.JSONObject
import timber.log.Timber
import java.net.HttpURLConnection
import java.net.URL

object TarsPushManager {
    const val CHANNEL_ID = "tarsvideo_admin"
    private const val CHANNEL_NAME = "TARSVideo - Administração"
    private const val CHANNEL_DESCRIPTION = "Notificações administrativas do TARSVideo"

    fun initialize(context: Context) {
        ensureNotificationChannel(context)
        FirebaseMessaging.getInstance().isAutoInitEnabled = true
    }

    fun requestNotificationPermission(activity: Activity) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return

        if (
            ContextCompat.checkSelfPermission(
                activity,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        activity.requestPermission(Manifest.permission.POST_NOTIFICATIONS) { }
    }

    fun ensureNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = CHANNEL_DESCRIPTION
            },
        )
    }

    fun register(
        context: Context,
        apiClient: ApiClient,
        tokenOverride: String? = null,
    ) {
        val accessToken = apiClient.accessToken?.trim().orEmpty()
        val baseUrl = apiClient.baseUrl?.trim()?.trimEnd('/').orEmpty()

        if (accessToken.isBlank() || baseUrl.isBlank()) return

        if (!tokenOverride.isNullOrBlank()) {
            registerToken(
                context = context.applicationContext,
                apiClient = apiClient,
                token = tokenOverride,
            )
            return
        }

        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Timber.w(task.exception, "Unable to obtain TARSVideo FCM token")
                return@addOnCompleteListener
            }

            val token = task.result?.trim().orEmpty()
            if (token.isBlank()) return@addOnCompleteListener

            registerToken(
                context = context.applicationContext,
                apiClient = apiClient,
                token = token,
            )
        }
    }

    private fun registerToken(
        context: Context,
        apiClient: ApiClient,
        token: String,
    ) {
        val accessToken = apiClient.accessToken?.trim().orEmpty()
        val baseUrl = apiClient.baseUrl?.trim()?.trimEnd('/').orEmpty()

        if (accessToken.isBlank() || baseUrl.isBlank() || token.isBlank()) return

        val payload = JSONObject().apply {
            put("token", token)
            put("device_id", apiClient.deviceInfo.id)
            put("app_version", BuildConfig.VERSION_NAME)
        }.toString()

        Thread {
            var connection: HttpURLConnection? = null

            try {
                connection = URL("$baseUrl/tars-chat/admin/push/register")
                    .openConnection() as HttpURLConnection

                connection.requestMethod = "POST"
                connection.connectTimeout = 10000
                connection.readTimeout = 10000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.setRequestProperty("X-Emby-Token", accessToken)

                connection.outputStream.use { output ->
                    output.write(payload.toByteArray(Charsets.UTF_8))
                }

                val code = connection.responseCode
                if (code in 200..299) {
                    context.getSharedPreferences("tarsvideo_push", Context.MODE_PRIVATE)
                        .edit()
                        .putString("registered_token", token)
                        .putString("registered_version", BuildConfig.VERSION_NAME)
                        .apply()
                    Timber.i("TARSVideo FCM registration succeeded")
                } else {
                    Timber.w("TARSVideo FCM registration HTTP %d", code)
                }
            } catch (error: Exception) {
                Timber.w(error, "TARSVideo FCM registration failed")
            } finally {
                connection?.disconnect()
            }
        }.apply {
            name = "tars-fcm-register"
            isDaemon = true
            start()
        }
    }

    fun showNotification(
        context: Context,
        title: String,
        body: String,
        notificationId: String,
    ) {
        ensureNotificationChannel(context)

        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val launchIntent = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            putExtra("tars_notification_id", notificationId)
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationId.hashCode(),
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val safeTitle = title.trim().ifBlank { "TARSVideo" }.take(180)
        val safeBody = body.trim().take(1500)

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.tars_notification)
            .setLargeIcon(BitmapFactory.decodeResource(context.resources, R.drawable.tars_icon))
            .setContentTitle(safeTitle)
            .setContentText(safeBody.take(240))
            .setStyle(NotificationCompat.BigTextStyle().bigText(safeBody))
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(notificationId.hashCode() and Int.MAX_VALUE, notification)
    }
}
''',
)

write(
    "app/src/main/java/org/jellyfin/mobile/tars/TarsFirebaseMessagingService.kt",
    r'''package org.jellyfin.mobile.tars

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.jellyfin.mobile.app.ApiClientController
import org.koin.core.component.KoinComponent
import org.koin.core.component.inject
import timber.log.Timber

class TarsFirebaseMessagingService : FirebaseMessagingService(), KoinComponent {
    private val apiClientController: ApiClientController by inject()

    override fun onNewToken(token: String) {
        super.onNewToken(token)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val serverUser = apiClientController.loadSavedServerUser()
                if (serverUser?.user?.accessToken.isNullOrBlank()) return@launch

                TarsPushManager.register(
                    context = applicationContext,
                    apiClient = apiClientController.currentApiClient(),
                    tokenOverride = token,
                )
            } catch (error: Exception) {
                Timber.w(error, "Unable to refresh TARSVideo FCM registration")
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)

        // Notification+data messages are displayed by Android automatically while
        // the app is backgrounded/killed. This branch handles foreground delivery.
        val title = message.notification?.title
            ?: message.data["title"]
            ?: "TARSVideo"

        val body = message.notification?.body
            ?: message.data["body"]
            ?: "Você tem uma nova notificação administrativa."

        val notificationId = message.data["notification_id"]
            ?.takeIf { it.isNotBlank() }
            ?: message.messageId
            ?: System.currentTimeMillis().toString()

        TarsPushManager.showNotification(
            context = applicationContext,
            title = title,
            body = body,
            notificationId = notificationId,
        )
    }
}
''',
)


# ------------------------------------------------------------
# In-app updater.
# ------------------------------------------------------------
write(
    "app/src/main/java/org/jellyfin/mobile/tars/TarsUpdater.kt",
    rf'''package org.jellyfin.mobile.tars

import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import org.jellyfin.mobile.BuildConfig
import org.json.JSONObject
import timber.log.Timber
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

object TarsUpdater {{
    private const val UPDATE_URL = "{UPDATE_MANIFEST_URL}"
    private const val PREFS = "tarsvideo_updater"
    private const val LAST_CHECK = "last_check"
    private const val CHECK_INTERVAL_MS = 6L * 60L * 60L * 1000L
    private const val PENDING_JSON = "pending_update"

    data class UpdateInfo(
        val versionName: String,
        val versionCode: Long,
        val apkUrl: String,
        val sha256: String,
        val releaseNotes: String,
    ) {{
        fun toJson(): String = JSONObject().apply {{
            put("versionName", versionName)
            put("versionCode", versionCode)
            put("apkUrl", apkUrl)
            put("sha256", sha256)
            put("releaseNotes", releaseNotes)
        }}.toString()

        companion object {{
            fun fromJson(value: String): UpdateInfo {{
                val json = JSONObject(value)
                return UpdateInfo(
                    versionName = json.getString("versionName"),
                    versionCode = json.getLong("versionCode"),
                    apkUrl = json.getString("apkUrl"),
                    sha256 = json.getString("sha256"),
                    releaseNotes = json.optString("releaseNotes", ""),
                )
            }}
        }}
    }}

    fun checkForUpdates(activity: Activity, force: Boolean = false) {{
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val last = prefs.getLong(LAST_CHECK, 0L)

        if (!force && now - last < CHECK_INTERVAL_MS) return
        prefs.edit().putLong(LAST_CHECK, now).apply()

        Thread {{
            try {{
                val update = fetchUpdateInfo() ?: return@Thread
                if (update.versionCode <= BuildConfig.VERSION_CODE.toLong()) return@Thread

                activity.runOnUiThread {{
                    showUpdateDialog(activity, update)
                }}
            }} catch (error: Exception) {{
                Timber.w(error, "TARSVideo update check failed")
            }}
        }}.apply {{
            name = "tars-update-check"
            isDaemon = true
            start()
        }}
    }}

    fun resumePendingUpdate(activity: Activity) {{
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !activity.packageManager.canRequestPackageInstalls()
        ) {{
            return
        }}

        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = prefs.getString(PENDING_JSON, null) ?: return

        try {{
            val update = UpdateInfo.fromJson(raw)
            prefs.edit().remove(PENDING_JSON).apply()
            downloadUpdate(activity, update)
        }} catch (error: Exception) {{
            prefs.edit().remove(PENDING_JSON).apply()
            Timber.w(error, "Unable to resume pending TARSVideo update")
        }}
    }}

    private fun fetchUpdateInfo(): UpdateInfo? {{
        var connection: HttpURLConnection? = null

        return try {{
            connection = URL(UPDATE_URL).openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = true
            connection.connectTimeout = 10000
            connection.readTimeout = 10000
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", "TARSVideo/${{BuildConfig.VERSION_NAME}}")

            if (connection.responseCode !in 200..299) return null

            val raw = connection.inputStream.bufferedReader().use {{ it.readText() }}
            val json = JSONObject(raw)

            UpdateInfo(
                versionName = json.getString("versionName"),
                versionCode = json.getLong("versionCode"),
                apkUrl = json.getString("apkUrl"),
                sha256 = json.getString("sha256").lowercase(),
                releaseNotes = json.optString("releaseNotes", ""),
            )
        }} finally {{
            connection?.disconnect()
        }}
    }}

    private fun showUpdateDialog(activity: Activity, update: UpdateInfo) {{
        if (activity.isFinishing || activity.isDestroyed) return

        val message = buildString {{
            append("TARSVideo ")
            append(update.versionName)
            append(" está disponível.")

            if (update.releaseNotes.isNotBlank()) {{
                append("\n\n")
                append(update.releaseNotes)
            }}
        }}

        AlertDialog.Builder(activity)
            .setTitle("Atualização disponível")
            .setMessage(message)
            .setNegativeButton("Agora não", null)
            .setPositiveButton("Atualizar") {{ _, _ ->
                prepareUpdate(activity, update)
            }}
            .show()
    }}

    private fun prepareUpdate(activity: Activity, update: UpdateInfo) {{
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !activity.packageManager.canRequestPackageInstalls()
        ) {{
            activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(PENDING_JSON, update.toJson())
                .apply()

            val intent = Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:${{BuildConfig.APPLICATION_ID}}"),
            )
            activity.startActivity(intent)
            return
        }}

        downloadUpdate(activity, update)
    }}

    private fun downloadUpdate(activity: Activity, update: UpdateInfo) {{
        val downloadsDir = activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
            ?: run {{
                showError(activity, "Não foi possível acessar a pasta de atualização.")
                return
            }}

        val apkFile = File(downloadsDir, "TARSVideo-v${{update.versionName}}.apk")
        if (apkFile.exists()) apkFile.delete()

        val manager = activity.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val request = DownloadManager.Request(Uri.parse(update.apkUrl))
            .setTitle("TARSVideo ${{update.versionName}}")
            .setDescription("Baixando atualização")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setAllowedOverMetered(true)
            .setAllowedOverRoaming(false)
            .setDestinationInExternalFilesDir(
                activity,
                Environment.DIRECTORY_DOWNLOADS,
                apkFile.name,
            )

        val downloadId = manager.enqueue(request)

        lateinit var receiver: BroadcastReceiver
        receiver = object : BroadcastReceiver() {{
            override fun onReceive(context: Context, intent: Intent) {{
                if (intent.action != DownloadManager.ACTION_DOWNLOAD_COMPLETE) return
                if (intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L) != downloadId) return

                try {{
                    activity.unregisterReceiver(this)
                }} catch (_: Exception) {{
                }}

                Thread {{
                    validateAndInstall(activity, update, apkFile)
                }}.apply {{
                    name = "tars-update-verify"
                    isDaemon = true
                    start()
                }}
            }}
        }}

        ContextCompat.registerReceiver(
            activity,
            receiver,
            IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
    }}

    private fun validateAndInstall(activity: Activity, update: UpdateInfo, apkFile: File) {{
        try {{
            if (!apkFile.isFile || apkFile.length() <= 0L) {{
                throw IllegalStateException("download_missing")
            }}

            val actualSha = sha256(apkFile)
            if (!actualSha.equals(update.sha256, ignoreCase = true)) {{
                apkFile.delete()
                throw IllegalStateException("sha256_mismatch")
            }}

            val packageInfo = activity.packageManager.getPackageArchiveInfo(
                apkFile.absolutePath,
                0,
            ) ?: throw IllegalStateException("invalid_apk")

            if (packageInfo.packageName != BuildConfig.APPLICATION_ID) {{
                apkFile.delete()
                throw IllegalStateException("package_mismatch")
            }}

            val archiveVersionCode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {{
                packageInfo.longVersionCode
            }} else {{
                @Suppress("DEPRECATION")
                packageInfo.versionCode.toLong()
            }}

            if (archiveVersionCode != update.versionCode) {{
                apkFile.delete()
                throw IllegalStateException("version_code_mismatch")
            }}

            activity.runOnUiThread {{
                launchInstaller(activity, apkFile)
            }}
        }} catch (error: Exception) {{
            Timber.w(error, "TARSVideo update validation failed")
            activity.runOnUiThread {{
                showError(activity, "A atualização baixada não passou na validação de segurança.")
            }}
        }}
    }}

    private fun launchInstaller(activity: Activity, apkFile: File) {{
        val uri = FileProvider.getUriForFile(
            activity,
            "${{BuildConfig.APPLICATION_ID}}.update-provider",
            apkFile,
        )

        val intent = Intent(Intent.ACTION_VIEW).apply {{
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }}

        activity.startActivity(intent)
    }}

    private fun sha256(file: File): String {{
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use {{ input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {{
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }}
        }}

        return digest.digest().joinToString("") {{ byte -> "%02x".format(byte) }}
    }}

    private fun showError(activity: Activity, message: String) {{
        if (activity.isFinishing || activity.isDestroyed) return

        AlertDialog.Builder(activity)
            .setTitle("TARSVideo")
            .setMessage(message)
            .setPositiveButton("OK", null)
            .show()
    }}
}}
''',
)


# ------------------------------------------------------------
# Final patch invariants.
# ------------------------------------------------------------
checks = {
    "app/build.gradle.kts": [
        'applicationId = "tars.video"',
        'base.archivesName.set("TARSVideo-v0.4.4")',
        'id("com.google.gms.google-services") version "4.5.0"',
        'com.google.firebase:firebase-messaging',
    ],
    "app/src/main/AndroidManifest.xml": [
        'android.permission.REQUEST_INSTALL_PACKAGES',
        '.tars.TarsFirebaseMessagingService',
        '${applicationId}.update-provider',
        'tarsvideo_admin',
    ],
    "app/src/main/java/org/jellyfin/mobile/tars/TarsPushManager.kt": [
        '/tars-chat/admin/push/register',
        'FirebaseMessaging.getInstance().token',
    ],
    "app/src/main/java/org/jellyfin/mobile/tars/TarsUpdater.kt": [
        UPDATE_MANIFEST_URL,
        'getPackageArchiveInfo',
        'MessageDigest.getInstance("SHA-256")',
    ],
}

for rel, markers in checks.items():
    content = read(rel)
    for marker in markers:
        if marker not in content:
            raise SystemExit(f"Missing v0.4.4 marker in {rel}: {marker}")

if "br.seg.douglas.tarsvideo" in read("app/build.gradle.kts"):
    raise SystemExit("Old br.seg.douglas application id still present")

if "'/native/tarsnotifications.js'" in read("app/src/main/assets/native/injectionScript.js"):
    raise SystemExit("Legacy WebView notification observer is still injected")

print(f"TARSVideo Android v{APP_VERSION} incremental patch applied successfully")
print(f"APPLICATION_ID={APPLICATION_ID}")
print("BUILD_VARIANT=LIBRE_RELEASE")
print("FCM_ADMIN_PUSH=ENABLED")
print("FCM_BACKGROUND_DELIVERY=ENABLED")
print("CHAT_MESSAGE_PUSH=DISABLED")
print("SYNCPLAY_STABLE_DEVICE_ID=PRESERVED")
print("IN_APP_UPDATER=ENABLED")
print(f"UPDATE_MANIFEST={UPDATE_MANIFEST_URL}")
