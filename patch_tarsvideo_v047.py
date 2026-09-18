from pathlib import Path
import sys

root = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path("upstream")
)

APP_VERSION = "0.4.7"


def read(rel: str) -> str:
    return (
        root / rel
    ).read_text(
        encoding="utf-8",
    )


def write(
    rel: str,
    text: str,
) -> None:
    path = root / rel

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )


def replace_once(
    rel: str,
    old: str,
    new: str,
    label: str,
) -> None:
    text = read(rel)

    count = text.count(old)

    if count != 1:
        raise SystemExit(
            f"{label}: expected 1 anchor "
            f"in {rel}, found {count}"
        )

    write(
        rel,
        text.replace(
            old,
            new,
            1,
        ),
    )


# ============================================================
# TARSVideo v0.4.7
#
# Fix:
# - DownloadManager completion receiver must accept the
#   system-originated ACTION_DOWNLOAD_COMPLETE broadcast.
#
# Diagnostics:
# - explicit updater lifecycle logs
#
# Security preserved:
# - SHA-256
# - package name
# - permanent signing certificate
# - versionCode
# ============================================================


# ------------------------------------------------------------
# VERSION / ARCHIVE
# ------------------------------------------------------------

replace_once(
    "app/build.gradle.kts",
    'base.archivesName.set("TARSVideo-v0.4.6")',
    'base.archivesName.set("TARSVideo-v0.4.7")',
    "v0.4.7 archive name",
)


# ------------------------------------------------------------
# UPDATER
# ------------------------------------------------------------

updater_rel = (
    "app/src/main/java/"
    "org/jellyfin/mobile/tars/"
    "TarsUpdater.kt"
)

updater = read(
    updater_rel
)


# ------------------------------------------------------------
# Log DownloadManager enqueue.
# ------------------------------------------------------------

old = '''        val downloadId = manager.enqueue(request)

        lateinit var receiver: BroadcastReceiver'''

new = '''        val downloadId = manager.enqueue(request)

        Timber.i(
            "TARSVideo DOWNLOAD_ENQUEUED id=%d",
            downloadId,
        )

        lateinit var receiver: BroadcastReceiver'''

if updater.count(old) != 1:
    raise SystemExit(
        "download enqueue anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


# ------------------------------------------------------------
# Log the exact DownloadManager completion broadcast.
# ------------------------------------------------------------

old = '''                if (intent.action != DownloadManager.ACTION_DOWNLOAD_COMPLETE) return
                if (intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L) != downloadId) return

                try {'''

new = '''                if (
                    intent.action !=
                    DownloadManager.ACTION_DOWNLOAD_COMPLETE
                ) {
                    return
                }

                val completedId =
                    intent.getLongExtra(
                        DownloadManager.EXTRA_DOWNLOAD_ID,
                        -1L,
                    )

                if (completedId != downloadId) {
                    return
                }

                Timber.i(
                    "TARSVideo DOWNLOAD_COMPLETE_RECEIVED id=%d",
                    completedId,
                )

                try {'''

if updater.count(old) != 1:
    raise SystemExit(
        "download completion receiver anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


# ------------------------------------------------------------
# DownloadManager is a system component.
#
# RECEIVER_NOT_EXPORTED prevented completion delivery on the
# tested Android/Samsung environment.
#
# Security is still enforced after delivery by validating:
# SHA, package, signer certificate, and versionCode.
# ------------------------------------------------------------

old = '''        ContextCompat.registerReceiver(
            activity,
            receiver,
            IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )'''

new = '''        ContextCompat.registerReceiver(
            activity,
            receiver,
            IntentFilter(
                DownloadManager.ACTION_DOWNLOAD_COMPLETE,
            ),
            ContextCompat.RECEIVER_EXPORTED,
        )

        Timber.i(
            "TARSVideo DOWNLOAD_RECEIVER_REGISTERED=EXPORTED",
        )'''

if updater.count(old) != 1:
    raise SystemExit(
        "DownloadManager receiver export anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


# ------------------------------------------------------------
# Validation lifecycle logs.
# ------------------------------------------------------------

old = '''    private fun validateAndInstall(activity: Activity, update: UpdateInfo, apkFile: File) {
        try {
            if (!apkFile.isFile || apkFile.length() <= 0L) {'''

new = '''    private fun validateAndInstall(activity: Activity, update: UpdateInfo, apkFile: File) {
        try {
            Timber.i(
                "TARSVideo APK_VALIDATION_STARTED",
            )

            if (!apkFile.isFile || apkFile.length() <= 0L) {'''

if updater.count(old) != 1:
    raise SystemExit(
        "validation start anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''            if (!actualSha.equals(update.sha256, ignoreCase = true)) {
                apkFile.delete()
                throw IllegalStateException("sha256_mismatch")
            }

            val archiveFlags'''

new = '''            if (!actualSha.equals(update.sha256, ignoreCase = true)) {
                apkFile.delete()
                throw IllegalStateException("sha256_mismatch")
            }

            Timber.i(
                "TARSVideo APK_SHA_VALID",
            )

            val archiveFlags'''

if updater.count(old) != 1:
    raise SystemExit(
        "SHA validation anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''            if (packageInfo.packageName != BuildConfig.APPLICATION_ID) {
                apkFile.delete()
                throw IllegalStateException("package_mismatch")
            }

            val archiveSigners'''

new = '''            if (packageInfo.packageName != BuildConfig.APPLICATION_ID) {
                apkFile.delete()
                throw IllegalStateException("package_mismatch")
            }

            Timber.i(
                "TARSVideo APK_PACKAGE_VALID",
            )

            val archiveSigners'''

if updater.count(old) != 1:
    raise SystemExit(
        "package validation anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''            if (!signerMatches) {
                apkFile.delete()
                throw IllegalStateException("signer_mismatch")
            }

            val archiveVersionCode'''

new = '''            if (!signerMatches) {
                apkFile.delete()
                throw IllegalStateException("signer_mismatch")
            }

            Timber.i(
                "TARSVideo APK_SIGNER_VALID",
            )

            val archiveVersionCode'''

if updater.count(old) != 1:
    raise SystemExit(
        "signer validation anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''            if (archiveVersionCode != update.versionCode) {
                apkFile.delete()
                throw IllegalStateException("version_code_mismatch")
            }

            activity.runOnUiThread {'''

new = '''            if (archiveVersionCode != update.versionCode) {
                apkFile.delete()
                throw IllegalStateException("version_code_mismatch")
            }

            Timber.i(
                "TARSVideo APK_VERSION_VALID",
            )

            activity.runOnUiThread {'''

if updater.count(old) != 1:
    raise SystemExit(
        "version validation anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''        activity.startActivity(intent)
    }'''

new = '''        Timber.i(
            "TARSVideo INSTALLER_LAUNCH_REQUESTED",
        )

        activity.startActivity(intent)
    }'''

if updater.count(old) != 1:
    raise SystemExit(
        "installer launch anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


write(
    updater_rel,
    updater,
)


# ------------------------------------------------------------
# FINAL VALIDATION
# ------------------------------------------------------------

checks = {
    "app/build.gradle.kts": [
        'applicationId = "tars.video"',
        (
            'base.archivesName.set('
            '"TARSVideo-v0.4.7")'
        ),
    ],

    updater_rel: [
        "ContextCompat.RECEIVER_EXPORTED",
        "DOWNLOAD_ENQUEUED",
        "DOWNLOAD_RECEIVER_REGISTERED=EXPORTED",
        "DOWNLOAD_COMPLETE_RECEIVED",
        "APK_VALIDATION_STARTED",
        "APK_SHA_VALID",
        "APK_PACKAGE_VALID",
        "APK_SIGNER_VALID",
        "APK_VERSION_VALID",
        "INSTALLER_LAUNCH_REQUESTED",

        # Security invariants
        "EXPECTED_SIGNER_SHA256",
        "sha256_mismatch",
        "package_mismatch",
        "signer_mismatch",
        "version_code_mismatch",
        (
            "archiveVersionCode "
            "!= update.versionCode"
        ),

        # v0.4.6 update controls
        "AUTO_UPDATE_CHECK=SKIPPED_DISABLED",
        "AUTO_UPDATE_CHECK=SKIPPED_INTERVAL",
        "AUTO_UPDATE_CHECK=REQUESTED",
        "MANUAL_UPDATE_CHECK=REQUESTED",
    ],
}


for rel, needles in checks.items():
    text = read(rel)
    compact = "".join(
        text.split()
    )

    for needle in needles:
        compact_needle = "".join(
            needle.split()
        )

        if compact_needle not in compact:
            raise SystemExit(
                "v0.4.7 validation failed "
                f"in {rel}: {needle}"
            )


updater_text = read(
    updater_rel
)

if (
    "ContextCompat.RECEIVER_NOT_EXPORTED"
    in updater_text
):
    raise SystemExit(
        "v0.4.7 validation failed: "
        "old DownloadManager receiver mode remains"
    )


print("APPLICATION_ID=tars.video")
print("APP_VERSION=0.4.7")

print(
    "DOWNLOAD_RECEIVER="
    "EXPORTED_FOR_SYSTEM_BROADCAST"
)

print(
    "DOWNLOAD_COMPLETE_LOGGING=ENABLED"
)

print(
    "APK_VALIDATION_LOGGING=ENABLED"
)

print(
    "INSTALLER_LAUNCH_LOGGING=ENABLED"
)

print(
    "UPDATER_SECURITY_CHECKS=PRESERVED"
)

print(
    "AUTO_UPDATE_TOGGLE=PRESERVED"
)

print(
    "MANUAL_UPDATE_CHECK=PRESERVED"
)
