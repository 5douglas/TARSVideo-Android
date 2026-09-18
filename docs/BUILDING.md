# Building

The recommended build method is GitHub Actions.

Workflow:

    .github/workflows/build-tarsvideo.yml

## Patch inputs

The current build uses:

    patch_tarsvideo.py
    patch_tarsvideo_v044.py
    patch_tarsvideo_v045.py
    patch_tarsvideo_v046.py
    patch_tarsvideo_v047.py

The immutable v0.4.2 base patch is restored from a pinned historical commit.

## Firebase

Custom forks should use their own Firebase project and their own
`google-services.json`.

Never place Firebase Admin service-account credentials in this repository.

## Signing

Release signing uses GitHub Actions secrets:

    TARSVIDEO_KEYSTORE_BASE64
    TARSVIDEO_KEYSTORE_PASSWORD
    TARSVIDEO_KEY_ALIAS
    TARSVIDEO_KEY_PASSWORD

The private keystore is not stored in the repository.

## Build verification

CI validates:

- application ID
- versionName
- versionCode
- APK signature
- signing certificate

A successful build produces the APK, SHA-256 file, update manifest and signing
audit information.
