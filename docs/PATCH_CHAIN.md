# Patch chain

The current TARSVideo build is assembled in this order:

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

## v0.4.3

`patch_tarsvideo.py` adds later client customization and stable Android
DeviceId behavior used by SyncPlay.

## v0.4.4

Adds the permanent `tars.video` package, FCM support and native updater
foundation.

## v0.4.5

Improves FCM saved-session recovery and update/about functionality.

## v0.4.6

Adds visible TARSVideo settings, automatic update control and manual update
checks.

## v0.4.7

Fixes DownloadManager completion handling and adds detailed updater lifecycle
logging while preserving SHA, package, signer and version validation.
