# Isolated pilot signed discovery

This directory belongs only to `sphere-pilot-20260911`. Existing environment
documents are unchanged. `discovery.json` contains signed management routes;
`public-key.txt` is the DER/SPKI RSA verification key encoded as standard Base64.
Neither file contains an enrollment credential or signing private key.

The APK verifies installation, signature, schema, freshness and durable version
before adopting new candidates. Signature algorithm: SHA256withRSA, RSA PKCS#1
v1.5. Public payload uses schema version 1. The pilot document expires 30 days
after issuance; a refreshed document must use a greater configuration version.

The `codex/pilot-bootstrap-20260911` branch is the initial APK bootstrap address.
Do not delete/rename it or replace its document with unsigned legacy JSON while
devices depend on it. Moving the branch/hostname requires an explicit bootstrap
migration; moving a management endpoint only requires publishing a higher signed
configuration version. Merge is not required for this isolated branch's acceptance.

The current backend uses one temporary outbound tunnel. This source lives outside
that tunnel, so its document can advertise a changed backend URL. The second
source is the pilot gateway itself; a second independent permanent external host
and a second working ingress remain deployment work. This is not fleet readiness.
