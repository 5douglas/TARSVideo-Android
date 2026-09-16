from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")
APP_VERSION = "0.4.3"


def read(rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ============================================================
# TARSVideo v0.4.3
# - stable Android DeviceId for Jellyfin 12 session identity
# - native Android notifications for TARS Chat while WebView is alive
# ============================================================

# APK/archive version produced by the base v0.4.2 patch.
gradle_rel = "app/build.gradle.kts"
gradle = read(gradle_rel)
if 'base.archivesName.set("TARSVideo-v0.4.2")' not in gradle:
    raise SystemExit("TARSVideo v0.4.2 archive anchor not found")
gradle = gradle.replace(
    'base.archivesName.set("TARSVideo-v0.4.2")',
    f'base.archivesName.set("TARSVideo-v{APP_VERSION}")',
    1,
)
write(gradle_rel, gradle)


# ------------------------------------------------------------
# Session identity fix
# ------------------------------------------------------------
api_rel = "app/src/main/java/org/jellyfin/mobile/app/ApiClientController.kt"
api = read(api_rel)

old_configure = '''    private fun configureApiClientUser(userId: UUID, accessToken: String) {
        apiClient.update(
            accessToken = accessToken,
            // Append user id to device id to ensure uniqueness across sessions
            deviceInfo = baseDeviceInfo.copy(id = baseDeviceInfo.id + userId),
        )
    }'''

new_configure = '''    private fun configureApiClientUser(userId: UUID, accessToken: String) {
        apiClient.update(
            accessToken = accessToken,
            // TARSVideo/Jellyfin 12: the server SessionKey already includes UserId.
            // Keep one stable DeviceId so WebView/native paths share one session.
            deviceInfo = baseDeviceInfo,
        )
    }'''

if old_configure not in api:
    raise SystemExit("ApiClientController configureApiClientUser anchor not found")
api = api.replace(old_configure, new_configure, 1)

old_secondary = '''            deviceInfo = baseDeviceInfo.copy(id = baseDeviceInfo.id + serverUser.user.userId),'''
new_secondary = '''            // TARSVideo/Jellyfin 12: keep the same stable physical-device id.
            deviceInfo = baseDeviceInfo,'''''

if old_secondary not in api:
    raise SystemExit("ApiClientController getApiClient DeviceId anchor not found")
api = api.replace(old_secondary, new_secondary, 1)
write(api_rel, api)


# ------------------------------------------------------------
# Native Android notification bridge
# ------------------------------------------------------------
native_rel = "app/src/main/java/org/jellyfin/mobile/bridge/NativeInterface.kt"
native = read(native_rel)

old_imports = '''import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.media.session.PlaybackState
import android.webkit.JavascriptInterface
import androidx.core.content.ContextCompat'''

new_imports = '''import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.media.session.PlaybackState
import android.os.Build
import android.webkit.JavascriptInterface
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat'''

if old_imports not in native:
    raise SystemExit("NativeInterface import anchor not found")
native = native.replace(old_imports, new_imports, 1)

old_project_imports = '''import org.jellyfin.mobile.BuildConfig
import org.jellyfin.mobile.events.ActivityEvent'''

new_project_imports = '''import org.jellyfin.mobile.BuildConfig
import org.jellyfin.mobile.MainActivity
import org.jellyfin.mobile.R
import org.jellyfin.mobile.events.ActivityEvent'''

if old_project_imports not in native:
    raise SystemExit("NativeInterface project import anchor not found")
native = native.replace(old_project_imports, new_project_imports, 1)

old_utils_import = '''import org.jellyfin.mobile.utils.Constants.EXTRA_TITLE
import org.jellyfin.mobile.webapp.RemotePlayerService'''

new_utils_import = '''import org.jellyfin.mobile.utils.Constants.EXTRA_TITLE
import org.jellyfin.mobile.utils.requestPermission
import org.jellyfin.mobile.webapp.RemotePlayerService'''

if old_utils_import not in native:
    raise SystemExit("NativeInterface requestPermission import anchor not found")
native = native.replace(old_utils_import, new_utils_import, 1)

notification_methods = r'''
    @JavascriptInterface
    fun requestTarsNotificationPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return true
        }

        if (
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            return true
        }

        val activity = context as? Activity ?: return false
        activity.runOnUiThread {
            activity.requestPermission(Manifest.permission.POST_NOTIFICATIONS) { }
        }
        return false
    }

    @JavascriptInterface
    fun showTarsNotification(title: String, text: String, notificationId: String): Boolean {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return false
        }

        val manager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val channelId = "tarsvideo_chat"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    channelId,
                    "TARSVideo",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ).apply {
                    description = "Mensagens e notificações do TARSVideo"
                },
            )
        }

        val launchIntent =
            context.packageManager.getLaunchIntentForPackage(context.packageName)
                ?: Intent(context, MainActivity::class.java)

        launchIntent.addFlags(
            Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP,
        )

        val contentIntent = PendingIntent.getActivity(
            context,
            0,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val safeTitle = title.trim().ifBlank { "TARSVideo" }.take(120)
        val safeText = text.trim().take(2000)

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.tars_notification)
            .setLargeIcon(BitmapFactory.decodeResource(context.resources, R.drawable.tars_icon))
            .setContentTitle(safeTitle)
            .setContentText(safeText.take(240))
            .setStyle(NotificationCompat.BigTextStyle().bigText(safeText))
            .setContentIntent(contentIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        val id =
            if (notificationId.isBlank()) {
                (System.currentTimeMillis() and Int.MAX_VALUE.toLong()).toInt()
            } else {
                notificationId.hashCode() and Int.MAX_VALUE
            }

        manager.notify(id, notification)
        return true
    }

'''

anchor = '''    @JavascriptInterface
    fun openServerSelection() {
        emitEvent(ActivityEvent.SelectServer)
    }

'''
if anchor not in native:
    raise SystemExit("NativeInterface notification insertion anchor not found")
native = native.replace(anchor, anchor + notification_methods, 1)
write(native_rel, native)


# Monochrome small icon used by Android's status bar.
write(
    "app/src/main/res/drawable/tars_notification.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M4,3h16c1.1,0 2,0.9 2,2v11c0,1.1 -0.9,2 -2,2h-9l-5.5,3v-3H4c-1.1,0 -2,-0.9 -2,-2V5c0,-1.1 0.9,-2 2,-2zM7,9.5a1.25,1.25 0,1 0,0 2.5a1.25,1.25 0,0 0,0 -2.5zM12,9.5a1.25,1.25 0,1 0,0 2.5a1.25,1.25 0,0 0,0 -2.5zM17,9.5a1.25,1.25 0,1 0,0 2.5a1.25,1.25 0,0 0,0 -2.5z" />
</vector>
''',
)


# ------------------------------------------------------------
# Expose notification functions to the WebView runtime.
# ------------------------------------------------------------
shell_rel = "app/src/main/assets/native/nativeshell.js"
shell = read(shell_rel)

shell_anchor = '''    openClientSettings() {
        window.NativeInterface.openClientSettings();
    },

'''
shell_insert = '''    openClientSettings() {
        window.NativeInterface.openClientSettings();
    },

    requestTarsNotificationPermission() {
        return window.NativeInterface.requestTarsNotificationPermission();
    },

    showTarsNotification(title, text, notificationId) {
        return window.NativeInterface.showTarsNotification(
            String(title || 'TARSVideo'),
            String(text || ''),
            String(notificationId || '')
        );
    },

'''
if shell_anchor not in shell:
    raise SystemExit("nativeshell notification anchor not found")
shell = shell.replace(shell_anchor, shell_insert, 1)
write(shell_rel, shell)


# Load the TARS notification observer in the Android WebView.
injection_rel = "app/src/main/assets/native/injectionScript.js"
injection = read(injection_rel)
old_scripts = '''        '/native/nativeshell.js',
        '/native/EventEmitter.js',
        document.currentScript.src.concat('?deferred=true&ts=', Date.now())'''
new_scripts = '''        '/native/nativeshell.js',
        '/native/EventEmitter.js',
        '/native/tarsnotifications.js',
        document.currentScript.src.concat('?deferred=true&ts=', Date.now())'''
if old_scripts not in injection:
    raise SystemExit("injectionScript list anchor not found")
write(injection_rel, injection.replace(old_scripts, new_scripts, 1))


# ------------------------------------------------------------
# TARS Chat -> Android local notification adapter.
# ------------------------------------------------------------
write(
    "app/src/main/assets/native/tarsnotifications.js",
    r'''(() => {
    'use strict';

    if (window.__TARS_NATIVE_NOTIFICATIONS_V1__) return;
    window.__TARS_NATIVE_NOTIFICATIONS_V1__ = true;

    const PERMISSION_KEY = 'tarsvideo-native-notification-permission-v1';
    const seenPersistent = new Set();
    const seenMessages = new Set();

    let persistentInitialized = false;
    let observedMessages = null;
    let messageObserver = null;

    function bridge() {
        const shell = window.NativeShell;
        if (!shell || typeof shell.showTarsNotification !== 'function') return null;
        return shell;
    }

    function requestPermissionOnce() {
        const shell = bridge();
        if (!shell || typeof shell.requestTarsNotificationPermission !== 'function') return;

        try {
            if (localStorage.getItem(PERMISSION_KEY) === '1') return;
            localStorage.setItem(PERMISSION_KEY, '1');
            shell.requestTarsNotificationPermission();
        } catch (_) {
            try { shell.requestTarsNotificationPermission(); } catch (_) {}
        }
    }

    function shouldNotify() {
        const chatState = window.__TARS_CHAT__?.state;
        return document.visibilityState !== 'visible' || !chatState?.panelOpen;
    }

    function notify(title, text, id) {
        if (!shouldNotify()) return false;

        const shell = bridge();
        if (!shell) return false;

        try {
            return shell.showTarsNotification(
                String(title || 'TARSVideo'),
                String(text || ''),
                String(id || '')
            ) === true;
        } catch (error) {
            console.debug('[TARSVideo] native notification failed', error);
            return false;
        }
    }

    function persistentFingerprint(item) {
        return String(
            item?.id ||
            [
                item?.title || '',
                item?.text || '',
                item?.time || ''
            ].join('|')
        );
    }

    function syncPersistentNotifications() {
        const notifications = window.__TARS_CHAT__?.state?.notifications;
        if (!Array.isArray(notifications)) return;

        if (!persistentInitialized) {
            for (const item of notifications) {
                seenPersistent.add(persistentFingerprint(item));
            }
            persistentInitialized = true;
            requestPermissionOnce();
            return;
        }

        for (const item of notifications) {
            const key = persistentFingerprint(item);
            if (seenPersistent.has(key)) continue;

            seenPersistent.add(key);

            if (item?.read === true) continue;
            if (String(item?.status || '').toLowerCase() === 'running') continue;

            notify(
                item?.title || 'TARSVideo',
                item?.text || 'Você tem uma nova notificação.',
                `persistent:${key}`
            );
        }
    }

    function messageFingerprint(element) {
        const name =
            element.querySelector('.tars-chat-message-name')?.textContent?.trim() || '';
        const text =
            element.querySelector('.tars-chat-message-bubble')?.textContent?.trim() || '';
        const time =
            element.querySelector('.tars-chat-message-time')?.textContent?.trim() || '';

        return `${name}|${text}|${time}`;
    }

    function rememberExistingMessages(container) {
        container.querySelectorAll('.tars-chat-message').forEach((element) => {
            seenMessages.add(messageFingerprint(element));
        });
    }

    function processMessageElement(element) {
        if (!(element instanceof Element)) return;
        if (!element.classList.contains('tars-chat-message')) return;

        const key = messageFingerprint(element);
        if (!key || seenMessages.has(key)) return;
        seenMessages.add(key);

        if (element.classList.contains('mine')) return;

        const name =
            element.querySelector('.tars-chat-message-name')?.textContent?.trim() || 'TARS Chat';
        const text =
            element.querySelector('.tars-chat-message-bubble')?.textContent?.trim() || '';

        if (!text) return;

        notify(
            `TARS Chat - ${name}`,
            text,
            `chat:${Date.now()}:${key}`
        );
    }

    function attachMessageObserver() {
        const container = document.getElementById('tars-chat-messages');
        if (!container || container === observedMessages) return;

        messageObserver?.disconnect();
        observedMessages = container;

        rememberExistingMessages(container);

        messageObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (!(node instanceof Element)) continue;

                    if (node.classList.contains('tars-chat-message')) {
                        processMessageElement(node);
                    }

                    node.querySelectorAll?.('.tars-chat-message').forEach(
                        processMessageElement
                    );
                }
            }
        });

        messageObserver.observe(container, {
            childList: true,
            subtree: true
        });
    }

    function tick() {
        if (!bridge()) return;
        requestPermissionOnce();
        syncPersistentNotifications();
        attachMessageObserver();
    }

    window.addEventListener('focus', tick);
    document.addEventListener('visibilitychange', tick);

    setInterval(tick, 1000);
    tick();

    console.debug('[TARSVideo] native notifications adapter loaded');
})();
''',
)


print(f"TARSVideo Android v{APP_VERSION} incremental patch applied successfully")
print("ANDROID_DEVICE_ID_MODE=STABLE_BASE_DEVICE_ID")
print("SYNCPLAY_DUPLICATE_SESSION_FIX=ENABLED")
print("TARS_NATIVE_NOTIFICATION_BRIDGE=ENABLED")
print("TARS_CHAT_NATIVE_NOTIFICATION_ADAPTER=ENABLED")
print("NATIVE_NOTIFICATION_SCOPE=APP_PROCESS_ALIVE")
