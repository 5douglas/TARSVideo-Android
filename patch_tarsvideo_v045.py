from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")

APP_VERSION = "0.4.5"
APPLICATION_ID = "tars.video"
PROJECT_URL = "https://github.com/5douglas/TARSVideo-Android"
RELEASES_URL = PROJECT_URL + "/releases/latest"
DEFAULT_SERVER = "https://video.douglas.seg.br"


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


replace_once(
    "app/build.gradle.kts",
    'base.archivesName.set("TARSVideo-v0.4.4")',
    'base.archivesName.set("TARSVideo-v0.4.5")',
    "v0.4.5 archive name",
)

replace_once(
    "app/src/main/java/org/jellyfin/mobile/MainViewModel.kt",
    '''    private suspend fun refreshUser() {
        val userEntity = apiClientController.loadSavedUser()
        _userState.value = userEntity?.let { entity -> UserState.Available(entity) } ?: UserState.Unset
    }''',
    '''    private suspend fun refreshUser() {
        val serverUser = apiClientController.loadSavedServerUser()
        val userEntity = serverUser?.user

        _userState.value = userEntity
            ?.let { entity -> UserState.Available(entity) }
            ?: UserState.Unset

        if (!serverUser?.user?.accessToken.isNullOrBlank()) {
            TarsPushManager.register(
                context = getApplication(),
                apiClient = apiClientController.currentApiClient(),
            )
        }
    }''',
    "saved-session FCM registration",
)

push_rel = "app/src/main/java/org/jellyfin/mobile/tars/TarsPushManager.kt"
push = read(push_rel)

old = '''import android.graphics.BitmapFactory
import android.os.Build'''
new = '''import android.graphics.BitmapFactory
import android.os.Build
import android.os.Handler
import android.os.Looper'''
if push.count(old) != 1:
    raise SystemExit("TarsPushManager imports anchor mismatch")
push = push.replace(old, new, 1)

old = '''    private const val CHANNEL_NAME = "TARSVideo - Administração"
    private const val CHANNEL_DESCRIPTION = "Notificações administrativas do TARSVideo"'''
new = '''    private const val CHANNEL_NAME = "TARSVideo - Administração"
    private const val CHANNEL_DESCRIPTION = "Notificações administrativas do TARSVideo"

    private const val PUSH_PREFS = "tarsvideo_push"
    private const val REGISTERED_TOKEN = "registered_token"
    private const val REGISTERED_VERSION = "registered_version"
    private const val REGISTERED_AT = "registered_at"

    private const val MAX_REGISTER_ATTEMPTS = 4
    private const val REGISTER_RETRY_BASE_MS = 4000L
    private const val TOKEN_REQUEST_TIMEOUT_MS = 12000L'''
if push.count(old) != 1:
    raise SystemExit("TarsPushManager constants anchor mismatch")
push = push.replace(old, new, 1)

old = '''    fun register(
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

        val tokenTask = FirebaseMessaging.getInstance().token

        Handler(Looper.getMainLooper()).postDelayed(
            {
                if (!tokenTask.isComplete) {
                    Timber.w("TARSVideo FCM token request timed out")
                    scheduleRetry(appContext, apiClient, attempt)
                }
            },
            TOKEN_REQUEST_TIMEOUT_MS,
        )

        tokenTask.addOnCompleteListener { task ->
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
    }'''
new = '''    fun register(
        context: Context,
        apiClient: ApiClient,
        tokenOverride: String? = null,
        attempt: Int = 1,
    ) {
        val appContext = context.applicationContext
        val accessToken = apiClient.accessToken?.trim().orEmpty()
        val baseUrl = apiClient.baseUrl?.trim()?.trimEnd('/').orEmpty()

        if (accessToken.isBlank() || baseUrl.isBlank()) {
            Timber.i("TARSVideo FCM registration skipped: session not ready")
            return
        }

        Timber.i("TARSVideo FCM registration requested attempt=%d", attempt)

        if (!tokenOverride.isNullOrBlank()) {
            registerToken(
                context = appContext,
                apiClient = apiClient,
                token = tokenOverride,
                attempt = attempt,
            )
            return
        }

        val tokenTask = FirebaseMessaging.getInstance().token

        Handler(Looper.getMainLooper()).postDelayed(
            {
                if (!tokenTask.isComplete) {
                    Timber.w("TARSVideo FCM token request timed out")
                    scheduleRetry(appContext, apiClient, attempt)
                }
            },
            TOKEN_REQUEST_TIMEOUT_MS,
        )

        tokenTask.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Timber.w(task.exception, "Unable to obtain TARSVideo FCM token")
                scheduleRetry(appContext, apiClient, attempt)
                return@addOnCompleteListener
            }

            val token = task.result?.trim().orEmpty()
            if (token.isBlank()) {
                Timber.w("TARSVideo FCM token was blank")
                scheduleRetry(appContext, apiClient, attempt)
                return@addOnCompleteListener
            }

            registerToken(
                context = appContext,
                apiClient = apiClient,
                token = token,
                attempt = attempt,
            )
        }
    }

    private fun scheduleRetry(
        context: Context,
        apiClient: ApiClient,
        attempt: Int,
    ) {
        if (attempt >= MAX_REGISTER_ATTEMPTS) {
            Timber.w("TARSVideo FCM registration retries exhausted")
            return
        }

        val nextAttempt = attempt + 1
        val delayMs = REGISTER_RETRY_BASE_MS * attempt

        Timber.i(
            "TARSVideo FCM registration retry scheduled attempt=%d delayMs=%d",
            nextAttempt,
            delayMs,
        )

        Handler(Looper.getMainLooper()).postDelayed(
            {
                register(
                    context = context.applicationContext,
                    apiClient = apiClient,
                    attempt = nextAttempt,
                )
            },
            delayMs,
        )
    }

    private fun registerToken(
        context: Context,
        apiClient: ApiClient,
        token: String,
        attempt: Int,
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
                    context.getSharedPreferences(PUSH_PREFS, Context.MODE_PRIVATE)
                        .edit()
                        .putString(REGISTERED_TOKEN, token)
                        .putString(REGISTERED_VERSION, BuildConfig.VERSION_NAME)
                        .putLong(REGISTERED_AT, System.currentTimeMillis())
                        .apply()

                    Timber.i("TARSVideo FCM registration succeeded")
                } else {
                    Timber.w("TARSVideo FCM registration HTTP %d", code)

                    if (code >= 500) {
                        scheduleRetry(context, apiClient, attempt)
                    }
                }
            } catch (error: Exception) {
                Timber.w(error, "TARSVideo FCM registration failed")
                scheduleRetry(context, apiClient, attempt)
            } finally {
                connection?.disconnect()
            }
        }.apply {
            name = "tars-fcm-register"
            isDaemon = true
            start()
        }
    }

    fun notificationsEnabled(context: Context): Boolean {
        return (
            Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS,
                ) == PackageManager.PERMISSION_GRANTED
        )
    }

    fun isRegistered(context: Context): Boolean {
        return !context
            .getSharedPreferences(PUSH_PREFS, Context.MODE_PRIVATE)
            .getString(REGISTERED_TOKEN, null)
            .isNullOrBlank()
    }

    fun registeredVersion(context: Context): String? {
        return context
            .getSharedPreferences(PUSH_PREFS, Context.MODE_PRIVATE)
            .getString(REGISTERED_VERSION, null)
    }

    fun registeredAt(context: Context): Long {
        return context
            .getSharedPreferences(PUSH_PREFS, Context.MODE_PRIVATE)
            .getLong(REGISTERED_AT, 0L)
    }'''
if push.count(old) != 1:
    raise SystemExit("TarsPushManager registration block anchor mismatch")
push = push.replace(old, new, 1)
write(push_rel, push)

updater_rel = "app/src/main/java/org/jellyfin/mobile/tars/TarsUpdater.kt"
updater = read(updater_rel)

old = '''        Thread {
            try {
                val update = fetchUpdateInfo() ?: return@Thread
                if (update.versionCode <= BuildConfig.VERSION_CODE.toLong()) return@Thread

                activity.runOnUiThread {
                    showUpdateDialog(activity, update)
                }
            } catch (error: Exception) {
                Timber.w(error, "TARSVideo update check failed")
            }
        }.apply {'''
new = '''        Thread {
            try {
                val update = fetchUpdateInfo()

                if (update == null) {
                    if (force) {
                        activity.runOnUiThread {
                            showError(
                                activity,
                                "Não foi possível consultar atualizações agora.",
                            )
                        }
                    }
                    return@Thread
                }

                if (update.versionCode <= BuildConfig.VERSION_CODE.toLong()) {
                    if (force) {
                        activity.runOnUiThread {
                            showUpToDate(activity)
                        }
                    }
                    return@Thread
                }

                activity.runOnUiThread {
                    showUpdateDialog(activity, update)
                }
            } catch (error: Exception) {
                Timber.w(error, "TARSVideo update check failed")

                if (force) {
                    activity.runOnUiThread {
                        showError(
                            activity,
                            "Não foi possível verificar atualizações agora.",
                        )
                    }
                }
            }
        }.apply {'''
if updater.count(old) != 1:
    raise SystemExit("TarsUpdater checkForUpdates anchor mismatch")
updater = updater.replace(old, new, 1)

old = '''    fun resumePendingUpdate(activity: Activity) {'''
new = '''    fun lastCheckTimestamp(context: Context): Long {
        return context
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong(LAST_CHECK, 0L)
    }

    fun resumePendingUpdate(activity: Activity) {'''
if updater.count(old) != 1:
    raise SystemExit("TarsUpdater last-check anchor mismatch")
updater = updater.replace(old, new, 1)

old = '''    private fun showUpdateDialog(activity: Activity, update: UpdateInfo) {'''
new = '''    private fun showUpToDate(activity: Activity) {
        if (activity.isFinishing || activity.isDestroyed) return

        AlertDialog.Builder(activity)
            .setTitle("TARSVideo atualizado")
            .setMessage(
                "Você já está usando a versão ${BuildConfig.VERSION_NAME}.",
            )
            .setPositiveButton("OK", null)
            .show()
    }

    private fun showUpdateDialog(activity: Activity, update: UpdateInfo) {'''
if updater.count(old) != 1:
    raise SystemExit("TarsUpdater up-to-date dialog anchor mismatch")
updater = updater.replace(old, new, 1)
write(updater_rel, updater)

settings_rel = "app/src/main/java/org/jellyfin/mobile/settings/SettingsFragment.kt"
settings = read(settings_rel)

old = '''import android.content.Intent
import android.os.Bundle'''
new = '''import android.content.Intent
import android.net.Uri
import android.os.Bundle'''
if settings.count(old) != 1:
    raise SystemExit("Settings Uri import anchor mismatch")
settings = settings.replace(old, new, 1)

old = '''import de.Maxr1998.modernpreferences.helpers.screen
import de.Maxr1998.modernpreferences.helpers.singleChoice'''
new = '''import de.Maxr1998.modernpreferences.helpers.screen
import de.Maxr1998.modernpreferences.helpers.singleChoice
import de.Maxr1998.modernpreferences.helpers.subScreen'''
if settings.count(old) != 1:
    raise SystemExit("Settings subScreen import anchor mismatch")
settings = settings.replace(old, new, 1)

old = '''import org.jellyfin.mobile.R
import org.jellyfin.mobile.app.AppPreferences'''
new = '''import org.jellyfin.mobile.BuildConfig
import org.jellyfin.mobile.R
import org.jellyfin.mobile.app.AppPreferences'''
if settings.count(old) != 1:
    raise SystemExit("Settings BuildConfig import anchor mismatch")
settings = settings.replace(old, new, 1)

old = '''import org.jellyfin.mobile.downloads.DownloadMethod
import org.jellyfin.mobile.utils.BackPressInterceptor'''
new = '''import org.jellyfin.mobile.downloads.DownloadMethod
import org.jellyfin.mobile.tars.TarsPushManager
import org.jellyfin.mobile.tars.TarsUpdater
import org.jellyfin.mobile.utils.BackPressInterceptor'''
if settings.count(old) != 1:
    raise SystemExit("Settings TARS imports anchor mismatch")
settings = settings.replace(old, new, 1)

old = '''        downloadLocationPreference = pref(Constants.PREF_STORAGE_LOCATION) {
            val location = storageManager.getStorageLocation()

            titleRes = R.string.pref_download_location
            summary = location?.name ?: getString(R.string.menu_item_none)

            onClick {
                storageLocationPicker.launch(location?.uri ?: storageManager.defaultStorageLocation)
                false
            }
        }
    }

    companion object {'''
new = '''        downloadLocationPreference = pref(Constants.PREF_STORAGE_LOCATION) {
            val location = storageManager.getStorageLocation()

            titleRes = R.string.pref_download_location
            summary = location?.name ?: getString(R.string.menu_item_none)

            onClick {
                storageLocationPicker.launch(location?.uri ?: storageManager.defaultStorageLocation)
                false
            }
        }

        subScreen(PREF_TARS_ABOUT) {
            title = "Sobre o App"
            summary = "TARSVideo ${BuildConfig.VERSION_NAME}"
            collapseIcon = true

            categoryHeader(PREF_TARS_ABOUT_INFO) {
                title = "TARSVideo"
            }

            pref(PREF_TARS_VERSION) {
                title = "Versão"
                summary = "${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})"
            }

            pref(PREF_TARS_PACKAGE) {
                title = "Pacote"
                summary = BuildConfig.APPLICATION_ID
            }

            pref(PREF_TARS_SERVER) {
                title = "Servidor padrão"
                summary = "https://video.douglas.seg.br"
            }

            pref(PREF_TARS_BASE) {
                title = "Base do aplicativo"
                summary = "Baseado no Jellyfin Android"
            }

            categoryHeader(PREF_TARS_ABOUT_STATUS) {
                title = "Status"
            }

            pref(PREF_TARS_NOTIFICATIONS) {
                title = "Notificações"
                summary = if (TarsPushManager.notificationsEnabled(requireContext())) {
                    "Permitidas"
                } else {
                    "Não permitidas"
                }
            }

            pref(PREF_TARS_PUSH) {
                title = "Push administrativo"

                val registered = TarsPushManager.isRegistered(requireContext())
                val registeredVersion = TarsPushManager.registeredVersion(requireContext())

                summary = if (registered) {
                    if (registeredVersion.isNullOrBlank()) {
                        "Registrado"
                    } else {
                        "Registrado pela versão $registeredVersion"
                    }
                } else {
                    "Não registrado"
                }
            }

            pref(PREF_TARS_LAST_UPDATE_CHECK) {
                title = "Última verificação de atualização"

                val timestamp = TarsUpdater.lastCheckTimestamp(requireContext())
                summary = if (timestamp <= 0L) {
                    "Ainda não verificado"
                } else {
                    java.text.DateFormat
                        .getDateTimeInstance(
                            java.text.DateFormat.SHORT,
                            java.text.DateFormat.SHORT,
                        )
                        .format(java.util.Date(timestamp))
                }
            }

            categoryHeader(PREF_TARS_ABOUT_ACTIONS) {
                title = "Atualizações"
            }

            pref(PREF_TARS_CHECK_UPDATE) {
                title = "Procurar atualizações"
                summary = "Verificar agora"

                onClick {
                    TarsUpdater.checkForUpdates(
                        activity = requireActivity(),
                        force = true,
                    )
                    false
                }
            }

            pref(PREF_TARS_RELEASE_NOTES) {
                title = "Notas da versão"
                summary = "Abrir a versão mais recente no GitHub"

                onClick {
                    startActivity(
                        Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse("https://github.com/5douglas/TARSVideo-Android/releases/latest"),
                        ),
                    )
                    false
                }
            }

            pref(PREF_TARS_PROJECT) {
                title = "Página do projeto"
                summary = "https://github.com/5douglas/TARSVideo-Android"

                onClick {
                    startActivity(
                        Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse("https://github.com/5douglas/TARSVideo-Android"),
                        ),
                    )
                    false
                }
            }
        }
    }

    companion object {'''
if settings.count(old) != 1:
    raise SystemExit("Settings About screen anchor mismatch")
settings = settings.replace(old, new, 1)

old = '''        const val PREF_CATEGORY_MUSIC_PLAYER = "pref_category_music"
        const val PREF_CATEGORY_VIDEO_PLAYER = "pref_category_video"
        const val PREF_CATEGORY_DOWNLOADS = "pref_category_downloads"'''
new = '''        const val PREF_CATEGORY_MUSIC_PLAYER = "pref_category_music"
        const val PREF_CATEGORY_VIDEO_PLAYER = "pref_category_video"
        const val PREF_CATEGORY_DOWNLOADS = "pref_category_downloads"

        const val PREF_TARS_ABOUT = "pref_tars_about"
        const val PREF_TARS_ABOUT_INFO = "pref_tars_about_info"
        const val PREF_TARS_ABOUT_STATUS = "pref_tars_about_status"
        const val PREF_TARS_ABOUT_ACTIONS = "pref_tars_about_actions"
        const val PREF_TARS_VERSION = "pref_tars_version"
        const val PREF_TARS_PACKAGE = "pref_tars_package"
        const val PREF_TARS_SERVER = "pref_tars_server"
        const val PREF_TARS_BASE = "pref_tars_base"
        const val PREF_TARS_NOTIFICATIONS = "pref_tars_notifications"
        const val PREF_TARS_PUSH = "pref_tars_push"
        const val PREF_TARS_LAST_UPDATE_CHECK = "pref_tars_last_update_check"
        const val PREF_TARS_CHECK_UPDATE = "pref_tars_check_update"
        const val PREF_TARS_RELEASE_NOTES = "pref_tars_release_notes"
        const val PREF_TARS_PROJECT = "pref_tars_project"'''
if settings.count(old) != 1:
    raise SystemExit("Settings companion constants anchor mismatch")
settings = settings.replace(old, new, 1)
write(settings_rel, settings)

checks = {
    "app/build.gradle.kts": [
        'applicationId = "tars.video"',
        'base.archivesName.set("TARSVideo-v0.4.5")',
    ],
    "app/src/main/java/org/jellyfin/mobile/MainViewModel.kt": [
        "loadSavedServerUser()",
        "TarsPushManager.register(",
    ],
    push_rel: [
        "MAX_REGISTER_ATTEMPTS = 4",
        "TOKEN_REQUEST_TIMEOUT_MS = 12000L",
        "TARSVideo FCM registration requested",
        "TARSVideo FCM token request timed out",
        "registration retry scheduled",
        "fun isRegistered(context: Context): Boolean",
        "fun notificationsEnabled(context: Context): Boolean",
    ],
    updater_rel: [
        "fun lastCheckTimestamp(context: Context): Long",
        'setTitle("TARSVideo atualizado")',
    ],
    settings_rel: [
        'title = "Sobre o App"',
        'title = "Procurar atualizações"',
        "TarsUpdater.checkForUpdates(",
        "TarsPushManager.isRegistered(",
        "https://github.com/5douglas/TARSVideo-Android",
    ],
}

for rel, markers in checks.items():
    content = read(rel)
    for marker in markers:
        if marker not in content:
            raise SystemExit(f"Missing v0.4.5 marker in {rel}: {marker}")

print(f"TARSVideo Android v{APP_VERSION} incremental patch applied successfully")
print(f"APPLICATION_ID={APPLICATION_ID}")
print("FCM_SAVED_SESSION_RETRY=ENABLED")
print("FCM_RETRY_BACKOFF=ENABLED")
print("ABOUT_APP_SCREEN=ENABLED")
print("MANUAL_UPDATE_CHECK=ENABLED")
print("MANUAL_UPDATE_FEEDBACK=ENABLED")
