from pathlib import Path
import sys


root = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path("upstream")
)

APP_VERSION = "0.4.8"


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
# TARSVideo v0.4.8
#
# Minimal release used to validate the updater shipped in
# TARSVideo v0.4.7.
#
# Functional change: none.
#
# The v0.4.7 updater implementation remains intact.
# ============================================================


replace_once(
    "app/build.gradle.kts",
    'base.archivesName.set("TARSVideo-v0.4.7")',
    'base.archivesName.set("TARSVideo-v0.4.8")',
    "v0.4.8 archive name",
)


updater_rel = (
    "app/src/main/java/"
    "org/jellyfin/mobile/tars/"
    "TarsUpdater.kt"
)


checks = {
    "app/build.gradle.kts": [
        'applicationId = "tars.video"',
        'base.archivesName.set("TARSVideo-v0.4.8")',
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

        "EXPECTED_SIGNER_SHA256",
        "sha256_mismatch",
        "package_mismatch",
        "signer_mismatch",
        "version_code_mismatch",
        "archiveVersionCode != update.versionCode",

        "AUTO_UPDATE_CHECK=SKIPPED_DISABLED",
        "AUTO_UPDATE_CHECK=SKIPPED_INTERVAL",
        "AUTO_UPDATE_CHECK=REQUESTED",
        "MANUAL_UPDATE_CHECK=REQUESTED",
    ],
}


for rel, needles in checks.items():
    text = read(rel)
    compact = "".join(text.split())

    for needle in needles:
        compact_needle = "".join(
            needle.split()
        )

        if compact_needle not in compact:
            raise SystemExit(
                "v0.4.8 validation failed "
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
        "v0.4.8 validation failed: "
        "old receiver mode remains"
    )


print("APPLICATION_ID=tars.video")
print("APP_VERSION=0.4.8")
print("FUNCTIONAL_CHANGE=NONE")
print("UPDATE_TEST_SOURCE=v0.4.7")
print(
    "DOWNLOAD_RECEIVER="
    "EXPORTED_FOR_SYSTEM_BROADCAST"
)
print(
    "UPDATER_SECURITY_CHECKS=PRESERVED"
)
