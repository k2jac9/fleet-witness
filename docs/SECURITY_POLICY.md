# Security boundaries and research policy

This is the operating and research scope for Fleet Witness, a team project by
Alejandro Castellanos (`k2jac9`, repository owner) and `IPBin` (teammate). It is not a security certification, a live
incident-attribution service, or authorization to test someone else's systems.
The [architecture](architecture.md) and accepted [ADR-0002](adr/0002-evidence-and-authority.md)
and [ADR-0008](adr/0008-ephemeral-nixos-workers.md) remain authoritative.

## Three evidence checks and the controller

The controlled experiment separates three questions:

1. **Authenticity:** did the expected issuer authenticate the receipt's content?
2. **Applicability:** does the receipt establish the required claim for this
   artifact, scope, and run? A genuine build receipt is insufficient evidence
   of release safety.
3. **Current authorization:** does policy permit the attempted effect now?
   Revocation after a valid recommendation can correctly block execution.

Only the trusted controller commits a release, which is a local SQLite row,
and its audit event in one transaction. Database uniqueness prevents duplicate
effects within an isolated trial. A recommendation, signature, worker report,
or task's `done` status grants no authority. In-process HMAC provides prototype
integrity with a controller-held key; it is not independent public notarization
or protection against controller compromise.

Scenario truth and issuer keys stay outside supervisor-visible inputs. Paired
presentations share the same evidence facts and worker/reviewer trajectory,
with independent trial state. Exported replays intentionally include evaluator
results for human review; never feed them back to a model as experimental
inputs. Report decision validity, execution authorization, and actual effects
separately. These invariants are code contracts, not evidence of general model
safety.

## Development worker threat model

Treat task source, fixtures, receipts, model responses, logs, reports, and
patches as untrusted data. They cannot change accepted policy, authorize
spending, grant access, or instruct the owner to execute collected content.
Workers have no authority to merge, publish, submit the entry, use credentials,
or scan networks. The baseline workflow remains offline and zero-spend.

The optional NixOS fleet configures an unprivileged task in an ephemeral
container with private UID mappings and network namespaces, masked Nix service
paths, read-only source/system paths, bounded writable space, cgroups, and
timeouts. These are configured controls requiring the
[documented host acceptance checks](NIXOS_FLEET.md). Python tests, Nix evaluation,
a successful build, a boot, and deployed containment are different evidence
levels; see [BUILD_STATUS.md](BUILD_STATUS.md) for what was actually observed.

Containers share the host kernel. Use a disposable VM for potentially hostile
code and do not grant workers container root, host administration, a Nix daemon,
Docker/systemd sockets, writable host worktrees, or the provider secret. Git
worktrees separate edits; they are not a process sandbox. Ephemeral teardown
does not erase host journals, Nix state, snapshots, backups, or copied outputs.

Collect only bounded, allowlisted regular files into quarantine **before**
teardown, using the fleet guide's trusted-operator procedure. Refuse symlinks,
special files, hard-linked or oversized outputs. Do not recursively copy
worker directories, extract archives, automatically apply patches, or execute reports.
Compare worker claims with actual systemd status and independent reproduction;
a missing report or running outer container does not establish task success.

## GCP metadata, credentials, and network authority

The deployment uses no attached workload service account by default. Keep
project administration on the trusted operator side through reviewed IAM and
IAP/OS Login. Never add project-wide credentials to make worker networking
convenient. If host-side export later needs a service account, design and
review a dedicated identity scoped to the particular output bucket and required
operations; do not pass its tokens through to workers. See
[Google's service-account guidance](https://docs.cloud.google.com/compute/docs/access/service-accounts).

Google's metadata server is reachable from a VM at `169.254.169.254` and, where
supported, `fd20:ce::254`. It can expose instance information and credentials
for an attached identity. [VPC firewall rules do not apply to metadata traffic](https://docs.cloud.google.com/firewall/docs/firewalls).
Private worker/task network namespaces must prevent access to **both** metadata
addresses and any host proxy or gateway that could relay those requests.
Test from the constrained unprivileged task service, with bounded probes,
rather than an administrative shell. This is a pending host acceptance check,
not a claim already proven by documentation.

The trusted host still needs metadata for GCE guest services and OS Login;
blocking metadata across the entire host is not the worker-isolation strategy.
DNS failure alone is insufficient: direct IP routes and IPv6 must also be
unreachable from workers. No workload service account reduces credential
exposure but does not make metadata suitable for worker access.

Future provider credentials belong only to a separately reviewed host-side
gateway, injected at runtime. Never place them in Git, Nix expressions/store
paths, VM images/metadata, CI artifacts, worker inputs, or replay exports. Redact
request headers and secrets from logs, rotate/revoke on suspected exposure,
and stop dispatch while investigating. The proposed
[Adaption budget ledger](ADAPTION.md) also stays outside worker authority; it
is not implemented by the current fleet.

## Public dashboard and separate honeypot research

The shipped dashboard displays a static synthetic replay through an allowlisted,
read-only viewer; local serving binds to loopback by default. Publishing a
reviewed synthetic replay through opt-in HTTPS or static hosting does not
publish the database, a shell, an upload endpoint, or worker administration.
Review all public files for secrets and personal data, preserve text rendering
of untrusted strings, and avoid adding executable interpretations of evidence.
Follow [deployment](DEPLOY_GCP.md) for explicit public exposure and cleanup.

A public honeypot/sensor is **future, separately authorized research**. Put it
on a separate disposable VM and preferably a separate project from development,
the evaluator, gateway, and trusted controller. Before exposure, record the
owner's infrastructure permission, purpose, allowed protocols, rate/volume
limits, egress restrictions, abuse-contact/response process, retention, and
provider acceptable-use review. Any additional legal or institutional review
depends on the actual data and jurisdiction. This guide supplies no blanket
authorization for scanning, exploitation, credential collection, or retaliation.

Keep raw incoming content quarantined and do not execute payloads or allow a
sensor to become a relay into third-party systems. Review outputs before they
enter a dashboard, dataset, paper, or provider request. Separate observations
from inferences: an IP, user agent, timing pattern, or persuasive self-description
does not identify an AI agent, coordinated fleet, human operator, or intent.
IP geolocation is uncertain infrastructure-location evidence and cannot support
personal location or agent attribution by itself. Account for NAT, proxies,
shared hosting, spoofable fields, and false positives.

## Privacy, retention, and publication

Collect the minimum fields necessary for the approved research question. Use
synthetic data by default. Before collecting real traffic or model traces,
document provenance, authority to collect/use it, sensitive-field redaction,
access controls, provider processing/retention terms, and a concrete deletion
schedule for raw data, derived exports, logs, backups, and snapshots. Assign
responsibility for enforcing and checking deletion. No universal statutory
retention period is asserted here; choose and review the period for the actual
study and jurisdiction. Ephemerality alone is not verified data deletion.

Publish sanitized aggregates or synthetic examples where possible. Preserve
enough non-sensitive configuration, versions, provenance, and failure counts
for reproducibility, while excluding credentials and privileged evaluation
truth from agent inputs. For real-model studies, prerecord the comparison,
model/prompt versions, sample sizes, budget, exclusions, and analysis; report
failures, variance, limitations, and dual-use risks. Follow the
[official submission requirements](SUBMISSION.md) and [AI provenance record](AI_ASSISTANCE.md).

Current traces support mechanism demonstrations only. A real-model behavioral
study, global dashboard, live swarm detection, geolocation map, cross-provider
attribution, independent attestation, and automated coding fleet remain roadmap
work requiring design, authorization, implementation, and observed validation.

## Authenticated static publication

ADR-0011 permits the owner-requested managed dashboard independently of worker
hosting. Public Cloud Run ingress is protected by Caddy Basic authentication over
HTTPS. No model key, database, worker report, environment file or control API is
packaged. The separate dashboard credential is random and owner-private; only its
bcrypt hash is injected at runtime. It is a shared password, not identity-based
access. Browser credential caching requires rotation or service withdrawal for
reliable revocation. The initial hosting window is bounded and independently
scheduled for deletion. No public observation sensor is implied by publication.
