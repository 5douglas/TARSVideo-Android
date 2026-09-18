# Contributing

Thanks for your interest in TARSVideo Android.

## Project model

TARSVideo is a patch-based downstream customization of Jellyfin Android.

Please avoid adding a complete Jellyfin Android source tree to this repository.

Changes should normally be made as:

- a new incremental patch;
- a build workflow change;
- documentation;
- branding or project resources.

## Patch requirements

New patches should:

- use deterministic source anchors;
- fail if an expected anchor is missing or duplicated;
- preserve existing security checks;
- include validation markers when practical;
- be tested against the pinned Jellyfin Android commit.

## Pull requests

A useful pull request should explain:

- the problem being solved;
- which TARSVideo version it targets;
- files changed;
- runtime behavior affected;
- how the change was tested;
- whether signing, Firebase, updater or DeviceId behavior changes.

## Security

Never submit:

- Jellyfin access tokens;
- API credentials;
- Firebase Admin service-account files;
- release keystores;
- signing passwords;
- private server environment files.

See `SECURITY.md` for additional guidance.
