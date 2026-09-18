# Architecture

TARSVideo uses a patch-based build model instead of maintaining a full
permanent fork of Jellyfin Android.

## Build flow

    TARSVideo repository
            |
            v
    pinned Jellyfin Android source
            |
            v
    TARSVideo patch chain
            |
            v
    project resources
            |
            v
    Gradle libreRelease
            |
            v
    signed APK
            |
            v
    package/version/certificate validation
            |
            +--> test artifact
            +--> optional GitHub Release

## Why upstream is pinned

Patch-based builds depend on specific source structures.

The Jellyfin Android commit is pinned so upstream changes cannot silently break
the patch chain.

Updating upstream should be treated as a controlled migration followed by a
full build and runtime validation.

## Runtime integrations

TARSVideo adds project-specific integrations such as:

- Firebase Cloud Messaging administrative notifications
- saved-session FCM recovery
- native updater
- stable Android DeviceId handling for SyncPlay
- JavaScript Injector compatibility

## Updater security

Before installation, the updater validates:

- APK SHA-256
- Android package name
- signing certificate
- versionCode

Build and public release publication are intentionally separate operations.
