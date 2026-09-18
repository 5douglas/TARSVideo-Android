# Release process

TARSVideo separates APK compilation from public release publication.

## Test build

A normal push to `main` triggers a build and produces a verified artifact.

The `Publish GitHub Release` step remains skipped.

## Artifact validation

Before publication verify:

    packageName
    versionName
    versionCode
    APK signature
    signing certificate
    APK SHA-256
    update.json

## Runtime validation

Versions that change runtime behavior should also be tested on a real Android
device before publication.

## Publication

Only after validation should the release become public.

Expected public assets include:

    TARSVideo-vX.Y.Z.apk
    TARSVideo-vX.Y.Z.apk.sha256
    update.json

After publication, verify that:

    releases/latest/download/update.json

returns the new release metadata.
