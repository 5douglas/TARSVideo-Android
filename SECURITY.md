# Security policy

## Sensitive information

Do not publish the following in issues, pull requests or CI logs:

- Jellyfin access tokens
- privileged API keys
- Firebase Admin service-account JSON
- private signing keys or keystores
- signing passwords
- backend authentication headers
- server `.env` files

If a diagnostic log contains an authenticated Jellyfin session token, redact it
before posting.

## Android signing

The release signing keystore must remain outside the repository.

GitHub Actions receives signing material through encrypted repository secrets.

## Firebase

The Android `google-services.json` file is client configuration.

Firebase Admin credentials are privileged server-side credentials and must
never be committed.

## Updater

TARSVideo validates the following before requesting installation of an update:

- SHA-256
- package name
- signing certificate
- versionCode

Changes that weaken or bypass these checks should receive explicit security
review.
