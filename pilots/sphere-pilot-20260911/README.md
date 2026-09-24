# Isolated pilot signed discovery

This directory belongs only to `sphere-pilot-20260911`. Existing environment
documents are unchanged. `discovery.json` contains signed management routes;
`public-key.txt` is the DER/SPKI RSA verification key encoded as standard Base64.
Neither file contains an enrollment credential or signing private key.

The APK verifies installation, signature, schema, freshness and durable version
before adopting new candidates. Signature algorithm: SHA256withRSA, RSA PKCS#1
v1.5. Public payload uses schema version 1. The pilot document expires 30 days
after issuance; a refreshed document must use a greater configuration version.

The pilot host now publishes changes automatically using the
[scoped discovery publisher](https://github.com/RootOne1337/sphere-platform/blob/codex/enterprise-audit-20260905/scripts/discovery_publisher.py).
It verifies the candidate installation and readiness, signs the next version,
updates this file using its expected Git blob SHA, verifies the result and updates
the local mirror. Failed probes preserve the previous signed document. Unchanged
routes do not produce repeated commits. Renewal starts seven days before expiry.
The signing private key remains on the publisher host, outside the public gateway.

The current Windows task runs every minute and at user logon; it requires that
user's Windows session, Docker Desktop and GitHub CLI credentials. Host reboot
acceptance and a live multi-day renewal drill remain open. A connector restart
was accepted with automatic publication in 39.97 seconds and a real Android
command after route recovery in 250.83 seconds; this is one pilot observation,
not a recovery-time guarantee. See the
[operating contract and evidence](https://github.com/RootOne1337/sphere-platform/blob/codex/enterprise-audit-20260905/docs/operations/DISCOVERY-PUBLISHER.md).

The `codex/pilot-bootstrap-20260911` branch is the initial APK bootstrap address.
Do not delete/rename it or replace its document with unsigned legacy JSON while
devices depend on it. Moving the branch/hostname requires an explicit bootstrap
migration; moving a management endpoint only requires publishing a higher signed
configuration version. Merge is not required for this isolated branch's acceptance.

The current backend uses one temporary outbound tunnel. This source lives outside
that tunnel, so its document can advertise a changed backend URL. The second
source is the pilot gateway itself; a second independent permanent external host
and a second working ingress remain deployment work. This is not fleet readiness.

## Runtime route check — 25 September 2026

The currently published signed discovery document is version 24. On the pilot host,
the stable GitHub Raw URL and `https://<verified-pilot-route>/bootstrap/agent.signed.json`
both returned HTTP 200 and the same SHA-256 for the 872-byte envelope. The route's
`/api/v1/health/readyz` returned HTTP 200. This is a point-in-time bootstrap and
readiness check; it does not establish that Android video frames reach a browser.

The same check found configuration drift outside this repository: the host's local
pilot environment pointed at a name that did not resolve, and the legacy development
document on the repository's `main` branch advertised a Serveo endpoint returning
HTTP 502. The signed pilot envelope and its gateway copy were healthy. New pilot APKs
must embed the stable signed-discovery source, installation ID, and pinned public key;
they must not silently use the legacy environment document as a fallback. Keep the
old route until an APK has accepted and used the verified signed route, then test
reconnect and frame delivery separately.
