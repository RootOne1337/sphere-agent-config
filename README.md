# Sphere Agent Configuration

Public repository for the Android pilot's signed discovery document and a small,
legacy generator for manually provisioned agent configurations. This repository
does not deploy Sphere, publish APKs, or grant a device access to the backend.

> [!CAUTION]
> Never commit an enrollment credential, signing private key, generated device
> configuration, or production secret. Public Git history is permanent even after a
> file is removed from the current branch.

## Current Android bootstrap

The current pilot flow is documented in
[`pilots/sphere-pilot-20260911/README.md`](pilots/sphere-pilot-20260911/README.md).
The APK verifies the signed discovery envelope with the checked-in public key before
accepting management routes. The private signing key stays on the publishing host.
The discovery document carries routing metadata; it is not an enrollment credential
and does not by itself prove that a route is reachable or highly available.

The pilot uses a stable branch path because installed APKs fetch updates from it. Do
not rename or delete `codex/pilot-bootstrap-20260911` while devices depend on that
path. Keep signed configuration changes versioned and monotonically increasing, and
test both publication and device recovery before relying on a new route.

GitHub Raw is one distribution path. A signature protects integrity and authenticity,
but it does not make GitHub available during an outage or regional block. The pilot
documentation records the current mirror and recovery limits; do not describe this
single-source setup as independent-ingress HA.

**Pilot verification (25 September 2026):** the signed discovery v24 fetched from
the stable branch and the pilot gateway's `/bootstrap/agent.signed.json` endpoint
returned byte-identical documents (HTTP 200). This verifies both configured fetch
paths at that time; it does not prove a browser video stream or long-term tunnel
availability. The current `main` branch's legacy development document still routes
through a Serveo URL that returned HTTP 502. New pilot builds must use the signed
discovery URL and pinned public key from the pilot directory, not fall back to that
legacy document. See the pilot guide for the measured scope and recovery limits.

## Legacy manual configuration

`schema.json`, `environments/`, `templates/`, and
[`scripts/generate_device_config.py`](scripts/generate_device_config.py) are retained
for compatibility and local experiments. They are **not** the current signed
discovery flow, do not update an installed APK, and do not perform `adb push` or
enrollment themselves. Endpoint values are intentionally unset until an operator
supplies a verified address for the target network.

Use Python 3.10 or newer. Provide the endpoint and enrollment key only through the
process environment, then write generated output to the ignored `output/` directory.
For PowerShell:

```powershell
$env:SPHERE_SERVER_URL = "https://your-verified-sphere-host"
$env:SPHERE_ENROLLMENT_API_KEY = "sphr_<issued-device-register-key>"
python scripts/generate_device_config.py `
  --env development `
  --workstation-id ws-lab-01 `
  --instance-index 0 `
  --location lab `
  --output-dir .\output
Remove-Item Env:SPHERE_SERVER_URL, Env:SPHERE_ENROLLMENT_API_KEY
```

For a batch, use `--count N --start-index 0`; each generated file contains a
credential and must be handled as a secret. Restrict local file access, deliver it
through a protected channel, and delete it when no longer needed. Never upload the
output folder or paste generated configs into issues or logs. The generator refuses
to print credential contents on validation errors.

The generator is a compatibility utility, not a fleet manager. It does not create
unique Android identities, install apps, verify a backend enrollment, or provide
remote update/recovery. See the Sphere Platform documentation for the supported
device lifecycle and current pilot gates.

## Repository map

| Path | Purpose |
| --- | --- |
| `pilots/sphere-pilot-20260911/` | Signed route bootstrap and pilot operating guide |
| `public-key.txt` in the pilot directory | Public verification key; safe to distribute |
| `schema.json` | Legacy manual configuration schema |
| `environments/` | Non-secret defaults; deployment endpoints may be blank |
| `templates/` | Examples for legacy local configuration |
| `scripts/` | Compatibility configuration generator |
| `tests/` | Regression tests for secret handling and generation |

## Validation and change process

Every pull request runs the dependency-free Python regression suite and syntax
checks. Keep generated output out of Git. For a signed discovery update, review the
pilot guide, verify the detached signature and version, exercise the publisher and
recovery path, and record the exact tested result in the pull request. Do not publish
or merge a route change solely because CI passed.

If a credential may have been committed previously, removing it from the current
tree is insufficient. Confirm its owner and validity, revoke or rotate it at the
issuing backend if active, and document that action without copying the value into
GitHub.
