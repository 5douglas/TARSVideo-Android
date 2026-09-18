<p align="center">
  <img src="tars_icon.png" alt="TARSVideo" width="120">
</p>

<h1 align="center">TARSVideo Android</h1>

<p align="center">
Custom Android client built on top of Jellyfin Android using a reproducible patch-based build pipeline.
</p>

> 🇧🇷 [Documentação em Português (Brasil)](docs/README.pt-BR.md)

## About

TARSVideo Android is an independent customization of the official
[Jellyfin Android](https://github.com/jellyfin/jellyfin-android) client.

Instead of maintaining a complete permanent fork, this repository uses GitHub
Actions to checkout a pinned Jellyfin Android commit and apply the TARSVideo
patch chain on top of it.

This repository is also intended as a reference for people building their own
custom Jellyfin Android clients.

## Main customizations

- TARSVideo branding and launcher icon
- fixed/default Jellyfin server integration
- JavaScript Injector compatibility
- native Jellyfin/ExoPlayer playback
- stable Android DeviceId behavior for SyncPlay
- Firebase Cloud Messaging administrative notifications
- saved-session FCM registration and retry
- native in-app updater
- automatic and manual update checks
- native About the App settings
- APK SHA-256 validation
- package-name validation
- signing-certificate validation
- versionCode validation before installation
- detailed updater diagnostics

## Build architecture

    TARSVideo repository
            |
            v
    GitHub Actions
            |
            v
    Pinned Jellyfin Android source
            |
            v
    TARSVideo patch chain
            |
            v
    Gradle libreRelease
            |
            v
    Sign + verify APK
            |
            +--> test artifact
            |
            +--> optional GitHub Release

## Patch chain

    immutable v0.4.2 base
            |
            v
    patch_tarsvideo.py
            |
            v
    patch_tarsvideo_v044.py
            |
            v
    patch_tarsvideo_v045.py
            |
            v
    patch_tarsvideo_v046.py
            |
            v
    patch_tarsvideo_v047.py

## Building your own version

If you use this project as a reference, replace the TARSVideo-specific values:

- application ID
- application name and branding
- default server URL
- Firebase project and google-services.json
- release signing key
- GitHub Actions signing secrets
- updater URLs
- notification backend endpoints

Never reuse private TARSVideo credentials.

## Releases

Normal pushes can build and validate an APK without publishing it.

Public release publication is intentionally separated from compilation so the
exact signed artifact can be audited before becoming the update target.

## Security

Never publish Jellyfin access tokens, Firebase Admin credentials, signing
keystores, passwords, backend credentials or credential-bearing logs.

## Upstream and License

TARSVideo is based on:
https://github.com/jellyfin/jellyfin-android

Jellyfin Android is licensed under GNU GPL v2. TARSVideo is an independent
customization and is not an official Jellyfin project.
