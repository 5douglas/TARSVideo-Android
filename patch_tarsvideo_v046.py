from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")

APP_VERSION = "0.4.6"
APPLICATION_ID = "tars.video"


def read(rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
# TARSVideo v0.4.6
#
# - Sobre do app visível diretamente nas Configurações
# - toggle de atualização automática
# - atualização automática ligada por padrão
# - atualização manual continua independente do toggle
# - logs explícitos para teste do updater
# - preserva FCM, assinatura, SHA, package/version guards
# - preserva DeviceId estável / SyncPlay
# ============================================================


# ------------------------------------------------------------
# VERSION / ARCHIVE
# ------------------------------------------------------------

replace_once(
    "app/build.gradle.kts",
    'base.archivesName.set("TARSVideo-v0.4.5")',
    'base.archivesName.set("TARSVideo-v0.4.6")',
    "v0.4.6 archive name",
)


# ------------------------------------------------------------
# UPDATER
# ------------------------------------------------------------

updater_rel = (
    "app/src/main/java/"
    "org/jellyfin/mobile/tars/"
    "TarsUpdater.kt"
)

updater = read(updater_rel)


old = '''    private const val PREFS = "tarsvideo_updater"
    private const val LAST_CHECK = "last_check"
    private const val CHECK_INTERVAL_MS = 6L * 60L * 60L * 1000L
    private const val PENDING_JSON = "pending_update"'''

new = '''    private const val PREFS = "tarsvideo_updater"
    private const val LAST_CHECK = "last_check"
    private const val CHECK_INTERVAL_MS = 6L * 60L * 60L * 1000L
    private const val PENDING_JSON = "pending_update"

    const val AUTO_UPDATE_PREF_KEY = "pref_tars_auto_updates"'''

if updater.count(old) != 1:
    raise SystemExit(
        "TarsUpdater constants anchor mismatch"
    )

updater = updater.replace(
    old,
    new,
    1,
)


old = '''    fun checkForUpdates(activity: Activity, force: Boolean = false) {
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val last = prefs.getLong(LAST_CHECK, 0L)

        if (!force && now - last < CHECK_INTERVAL_MS) return
        prefs.edit().putLong(LAST_CHECK, now).apply()'''

new = '''    fun automaticUpdatesEnabled(
        context: Context,
    ): Boolean {
        return context
            .getSharedPreferences(
                "${context.packageName}_preferences",
                Context.MODE_PRIVATE,
            )
            .getBoolean(
                AUTO_UPDATE_PREF_KEY,
                true,
            )
    }

    fun checkForUpdates(
        activity: Activity,
        force: Boolean = false,
    ) {
        val prefs = activity.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE,
        )

        val now = System.currentTimeMillis()

        val last = prefs.getLong(
            LAST_CHECK,
            0L,
        )

        if (
            !force &&
            !automaticUpdatesEnabled(activity)
        ) {
            Timber.i(
                "TARSVideo AUTO_UPDATE_CHECK=SKIPPED_DISABLED",
            )

            return
        }

        if (
            !force &&
            now - last < CHECK_INTERVAL_MS
        ) {
            Timber.i(
                "TARSVideo AUTO_UPDATE_CHECK=SKIPPED_INTERVAL",
            )

            return
        }

        if (force) {
            Timber.i(
                "TARSVideo MANUAL_UPDATE_CHECK=REQUESTED",
            )
        } else {
            Timber.i(
                "TARSVideo AUTO_UPDATE_CHECK=REQUESTED",
            )
        }

        prefs.edit()
            .putLong(
                LAST_CHECK,
                now,
            )
            .apply()'''

if updater.count(old) != 1:
    raise SystemExit(
        "TarsUpdater checkForUpdates "
        "anchor mismatch"
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
# SETTINGS
#
# A v0.4.5 colocou o Sobre em subScreen.
# O código compilou, mas a entrada não apareceu no app real.
#
# v0.4.6 substitui isso por itens diretamente na raiz da
# SettingsFragment, usando os mesmos helpers que as opções
# já visíveis do Jellyfin.
# ------------------------------------------------------------

settings_rel = (
    "app/src/main/java/"
    "org/jellyfin/mobile/settings/"
    "SettingsFragment.kt"
)

settings = read(settings_rel)


about_start_marker = '''        subScreen(PREF_TARS_ABOUT) {
'''

about_end_marker = '''    }

    companion object {'''


start_count = settings.count(
    about_start_marker
)

if start_count != 1:
    raise SystemExit(
        "Settings v0.4.5 About "
        "start marker mismatch: "
        f"{start_count}"
    )


about_start = settings.index(
    about_start_marker
)

about_end = settings.index(
    about_end_marker,
    about_start,
)


if about_end <= about_start:
    raise SystemExit(
        "Settings About boundaries invalid"
    )


new_root_settings = '''        categoryHeader(
            PREF_TARS_ABOUT_INFO,
        ) {
            title = "TARSVideo"
        }

        checkBox(
            TarsUpdater.AUTO_UPDATE_PREF_KEY,
        ) {
            title =
                "Verificar atualizações automaticamente"

            summary =
                "Consultar novas versões ao abrir o TARSVideo"

            defaultValue = true
        }

        pref(
            PREF_TARS_CHECK_UPDATE,
        ) {
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

        pref(
            PREF_TARS_ABOUT,
        ) {
            title = "Sobre o App"

            summary =
                "TARSVideo ${BuildConfig.VERSION_NAME}"

            onClick {
                val context =
                    requireContext()

                val notifications =
                    if (
                        TarsPushManager
                            .notificationsEnabled(
                                context,
                            )
                    ) {
                        "Permitidas"
                    } else {
                        "Não permitidas"
                    }

                val pushRegistered =
                    TarsPushManager
                        .isRegistered(
                            context,
                        )

                val pushVersion =
                    TarsPushManager
                        .registeredVersion(
                            context,
                        )

                val push =
                    when {
                        !pushRegistered ->
                            "Não registrado"

                        pushVersion
                            .isNullOrBlank() ->
                            "Registrado"

                        else ->
                            (
                                "Registrado pela versão " +
                                    pushVersion
                            )
                    }

                val automaticUpdates =
                    if (
                        TarsUpdater
                            .automaticUpdatesEnabled(
                                context,
                            )
                    ) {
                        "Ativadas"
                    } else {
                        "Desativadas"
                    }

                val lastCheck =
                    TarsUpdater
                        .lastCheckTimestamp(
                            context,
                        )

                val lastCheckText =
                    if (lastCheck <= 0L) {
                        "Ainda não verificado"
                    } else {
                        java.text.DateFormat
                            .getDateTimeInstance(
                                java.text.DateFormat.SHORT,
                                java.text.DateFormat.SHORT,
                            )
                            .format(
                                java.util.Date(
                                    lastCheck,
                                ),
                            )
                    }

                val message =
                    buildString {
                        appendLine(
                            "Versão: " +
                                "${BuildConfig.VERSION_NAME} " +
                                "(${BuildConfig.VERSION_CODE})",
                        )

                        appendLine(
                            "Pacote: " +
                                BuildConfig.APPLICATION_ID,
                        )

                        appendLine(
                            "Servidor: " +
                                "https://video.douglas.seg.br",
                        )

                        appendLine(
                            "Base: Jellyfin Android",
                        )

                        appendLine()

                        appendLine(
                            "Notificações: " +
                                notifications,
                        )

                        appendLine(
                            "Push administrativo: " +
                                push,
                        )

                        appendLine(
                            "Atualizações automáticas: " +
                                automaticUpdates,
                        )

                        append(
                            "Última verificação: " +
                                lastCheckText,
                        )
                    }

                androidx.appcompat.app.AlertDialog
                    .Builder(
                        context,
                    )
                    .setTitle(
                        "Sobre o App",
                    )
                    .setMessage(
                        message,
                    )
                    .setPositiveButton(
                        "OK",
                        null,
                    )
                    .show()

                false
            }
        }

        pref(
            PREF_TARS_RELEASE_NOTES,
        ) {
            title = "Notas da versão"

            summary =
                "Abrir a versão mais recente no GitHub"

            onClick {
                startActivity(
                    Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse(
                            "https://github.com/" +
                                "5douglas/" +
                                "TARSVideo-Android/" +
                                "releases/latest",
                        ),
                    ),
                )

                false
            }
        }
'''


settings = (
    settings[:about_start]
    + new_root_settings
    + settings[about_end:]
)


write(
    settings_rel,
    settings,
)


# ------------------------------------------------------------
# GENERATED SOURCE VALIDATION
# ------------------------------------------------------------

checks = {
    "app/build.gradle.kts": [
        'applicationId = "tars.video"',
        (
            'base.archivesName.set('
            '"TARSVideo-v0.4.6")'
        ),
    ],

    updater_rel: [
        (
            'AUTO_UPDATE_PREF_KEY = '
            '"pref_tars_auto_updates"'
        ),
        (
            "fun automaticUpdatesEnabled("
        ),
        (
            "AUTO_UPDATE_CHECK="
            "SKIPPED_DISABLED"
        ),
        (
            "AUTO_UPDATE_CHECK="
            "SKIPPED_INTERVAL"
        ),
        (
            "AUTO_UPDATE_CHECK="
            "REQUESTED"
        ),
        (
            "MANUAL_UPDATE_CHECK="
            "REQUESTED"
        ),
        "EXPECTED_SIGNER_SHA256",
        (
            "archiveVersionCode "
            "!= update.versionCode"
        ),
    ],

    settings_rel: [
        'title = "TARSVideo"',
        (
            '"Verificar atualizações '
            'automaticamente"'
        ),
        'title = "Procurar atualizações"',
        'title = "Sobre o App"',
        "TarsUpdater.AUTO_UPDATE_PREF_KEY",
        (
            "TarsUpdater"
            ".automaticUpdatesEnabled("
        ),
        "TarsUpdater.checkForUpdates(",
        "force = true",
        (
            "TarsPushManager"
            ".isRegistered("
        ),
    ],
}


for rel, needles in checks.items():
    text = read(rel)

    # Kotlin formatting may split receivers/methods across lines.
    # Validation is intentionally whitespace-insensitive.
    compact_text = "".join(text.split())

    for needle in needles:
        compact_needle = "".join(needle.split())

        if compact_needle not in compact_text:
            raise SystemExit(
                "v0.4.6 validation failed "
                f"in {rel}: {needle}"
            )


settings_text = read(
    settings_rel
)


if (
    "subScreen(PREF_TARS_ABOUT)"
    in settings_text
):
    raise SystemExit(
        "v0.4.6 validation failed: "
        "old About subScreen still present"
    )


print(
    "APPLICATION_ID=tars.video"
)

print(
    "APP_VERSION=0.4.6"
)

print(
    "ROOT_TARS_SETTINGS=ENABLED"
)

print(
    "ABOUT_APP_DIALOG=ENABLED"
)

print(
    "AUTO_UPDATE_TOGGLE=ENABLED"
)

print(
    "AUTO_UPDATE_DEFAULT=ON"
)

print(
    "MANUAL_UPDATE_CHECK=ENABLED"
)

print(
    "UPDATER_SECURITY_CHECKS=PRESERVED"
)
