# Security policy

This repository contains public routing metadata, a public verification key, and
legacy configuration-generation code. It must never contain enrollment credentials,
signing private keys, generated device configurations, tokens, or private host data.

If a credential may be present in Git history, treat it as exposed until its owner
confirms otherwise. Contact the Sphere Platform operator through a private channel
with the repository path and commit reference. Do not include the credential in an
issue, pull request, log, or support request. The issuing backend owner must revoke or
rotate an active credential; deleting a file does not remove historical copies.

Report security issues privately to the repository owner. Include reproduction steps
and affected commit references, but redact credentials and device identifiers.
