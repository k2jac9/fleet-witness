# ADR-0011: Authenticated managed replay dashboard

- Status: Accepted implementation direction under the owner's 2026-11-08 request; deployment validation pending
- Extends: ADR-0005 and ADR-0009; supersedes none

The owner explicitly requested an externally accessible dashboard, continued
controlled experiments and autonomous implementation within the $100 GCP budget.
Use a separate Cloud Run service for immutable synthetic replay assets. Keep the
NixOS worker host, controller, model gateway and private records separate.

Google IAP with personal accounts needs one-time Console OAuth configuration.
For this bounded pilot use Caddy HTTP Basic authentication over Cloud Run's HTTPS
endpoint with a new random 256-bit password. Retain the password only in the
owner-private operational secrets directory; configure only its bcrypt hash.
This is a shared owner credential, not Google identity or multi-user auditing.
Platform ingress is public; Caddy authenticates every route before serving.
Browsers may retain Basic credentials until closed; rotate the password hash or
withdraw the service to revoke access. Never reuse this credential elsewhere.
Never put either the dashboard password or the Adaption key in image/source/logs.

Serve exactly index.html, styles.css, app.js and replay.json, with no write API,
directory listing or controller access. Disable Caddy administration and automatic
HTTPS inside the container; managed ingress terminates TLS. Use an unprivileged
container identity and dedicated Google service account with no project roles.
Pin the current stable Caddy container by digest. Use max one instance, min zero,
request-based CPU, short request timeouts, and a separately scoped scheduled
service deletion after 24 hours. Reserve at most $5 of the existing $100 envelope
for this initial hosting window; alerts/scaling limits are not hard billing caps.
Retained images and existing disks continue to cost storage after service expiry.

Alternatives: keeping only the SSH tunnel does not meet browser access from other
devices; exposing the worker VM adds unnecessary coupling; Google IAP remains the
preferred later identity upgrade once its Console setup is available.

Run a bounded 32-seed scripted campaign, preserve each replay/database, verify
paired facts and unauthorized/duplicate effect invariants, and show aggregate
findings alongside one representative replay. Seeds change synthetic identities;
they do not create independent empirical model observations. No external scanning,
actor attribution, unsolicited fleet contact or live provider calls is authorized
by this dashboard. ADR-0010 gates still apply to paid model experiments.

Require independent review, full Python/Node suites, actual Caddy HTTP tests,
image inventory, deployed HTTPS/authentication/path/method checks, IAM readbacks,
scheduled-expiry verification and a recorded withdrawal command. Retain old
runtime evidence and record unavailable compatibility/preview lanes honestly.
