# Verify the institution, not the agents

The swarm extension was added on 2026-11-08 by IPBin (with Claude Code).
The 2026-11-09 stabilization preserves those experimental records and repairs
spending, provenance and reproduction. Earlier scripted mechanism studies remain
separate. Start with the [latest synthesis](report/latest.md); see the preserved
[earlier report](report/REPORT.md),
[artifact provenance](report/ARTIFACT_PROVENANCE-2026-11-09.json) and
[current gates](GATES.md).

## Components and evidence boundaries

The institution kernel checks integrity, binding, seating, quorum, policy and
uniqueness, and commits each local release with its audit event in SQLite. Auditor
models provide semantic judgements. A majority or model answer cannot override
the controller. Releases here are local database records, not publications.

The runner assigns a colluding cell inside a synthetic release task. Reviewers
vote in waves under hidden or visible boards; seven seated auditors then judge
these cases. This is instructed coordination in a controlled setting. It does
not observe autonomous swarms on the public web or establish external identities.

Eight regimes consume the same votes and attestations: `direct`,
`gated-majority`, `auditor-1of1`, `committee-2of3`, `committee-3of5`,
`committee-4of7`, `unanimous-7of7`, and `hybrid-maj+4of7`. The zero-seat
`gated-majority` control now executes the actual kernel with majority, integrity,
policy, uniqueness and transactional audit checks. It is not a case-label filter.
The cost of collecting a run is N + 7 logical requests per case/condition;
regime comparisons reuse those observations.

Archived cases are reconstructed with fresh local signing keys and the current
synthetic case generator. Reproduction validates case identities, seating,
votes, denominators and recorded outcomes before producing tables. This is not
historical signature verification or new model data. Paired model/board outcomes
reuse seating draws and must not be treated as independent binomial trials.

## Offline execution

```sh
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 -m fleet_witness swarm --provider fake --agents 7 --cases 6 --output runs/fake-new
python3 -m fleet_witness.verify_institution --depth 6 --mutants
python3 scripts/extract_run_archive.py --archive data/fleet-witness-runs-2026-11-08.zip \
  --destination /absolute/fresh/extracted
python3 scripts/reproduce_tables.py --input-root /absolute/fresh/extracted/runs \
  --output-root /absolute/fresh/derived
```

Use fresh output paths and storage admission for retained reproduction output.
The extractor normalizes the archive's Windows separators and refuses traversal,
links, collisions, unsafe sizes and overwrites. Reproduction writes separately,
checks input hashes before/after, and emits strict JSON (`null` for undefined
statistics). The default reproduction includes the depth-six checker and mutants.

## Paid execution remains gated

A clean committed checkout and an owner-private, singly-linked regular
`--authorization` file are required before paid CLI entrypoints create a ledger.
No command issues an authorization or treats a credit balance as qualification.
The operator must first verify the account, applicable USD conversion, pricing,
all billable token bounds, retention, transport and accepted source. Confirmatory
records additionally require accepted, reconciled calibration. These are operator
attestations, not cryptographic proof of external provider facts. The accepted
ADRs and the separately predeclared supervisor pilot remain in force; these swarm
observations do not substitute for that pilot or its acceptance checks.

Each record uses schema `swarm-paid-v1` and names:

- Authorization ID, approving operator, purpose (`calibration` or `confirmatory`),
  issue/expiry timestamps, exact source commit and package-source digest.
- Provider, model, fixed endpoint, canonical absolute ledger path and stable run ID.
- Immutable run/provider USD caps, request count, input bytes, output tokens,
  response bytes and deadline (at most 30 seconds; record lifetime at most one day).
- Verified pricing with evidence hash, rate timestamp, USD input/output rates and
  an assertion covering all billable tokens.
- Qualification flags and an evidence hash for access, handling, transport and
  calibration. See `fleet_witness/swarm/authorization.py` for the exact closed schema.

Multiple model records use a `swarm-authorizations-v1` bundle. Review/speed-test
jobs require a shared run envelope across every selected model. Keep records and
private supporting evidence outside Git. `--max-usd` and token flags, if supplied,
must match the record; they cannot silently raise a cap. A paid `--dry-run` also
requires qualification, but reads no key and makes no provider request.

```sh
python3 -m fleet_witness swarm --provider adaption --model VERIFIED_MODEL \
  --authorization /private/path/qualified-record.json --output runs/live-new --dry-run
```

`VERIFIED_MODEL` and the path are placeholders, not a runnable qualification.
Keys are read lazily from `ADAPTION_API_KEY` or `OPENROUTER_API_KEY` at dispatch.
No key is placed in a worker, repository, image, prompt or public receipt.

## Spending and run records

One SQLite database holds shared reservations, provider totals, immutable run
caps and audit events. The default is `~/.fleet_witness/spend-ledger.sqlite3`;
operator records must designate the same canonical ledger for all related jobs.
Tags are metadata, not separate balances. Host/operator filesystem access remains
a trust boundary: selecting unrelated databases is not global account enforcement.
A legacy `spend-ledger*.json` beside the chosen database stops initialization.
There is no automatic migration, reset, cap increase or hold-release command.
Reconcile old records against the provider account before issuing a new record;
never remove or rename historical ledgers merely to clear this gate.

Requests reserve a conservative bound and record dispatch transactionally. Paid
runner calls are sequential; competing processes fail closed. There is one attempt,
no rate-limit retry and no truncation escalation. Redirects and inherited proxies
are disabled, response bytes/parse depth are bounded, and a transport deadline
bounds the caller. A sent request may still finish remotely after timeout.
Unknown usage, malformed responses, timeouts, persistence failures and overruns
retain liability and halt further dispatch. No failure is assumed free. Larger
known liabilities are preserved even when they exceed a cap.

New `swarm-run-2` manifests distinguish logical completions, provider attempts,
settled costs, held liabilities and ledger snapshots. They bind source files,
Python runtime, model configuration and authorization identity. Public events
contain allowlisted accounting metadata and prompt hashes. Raw bounded prompts,
responses and failures are retained in owner-private `private/requests.jsonl`;
the ledger retains private provider request/response receipts. Neither belongs in
the dashboard or a public archive. Ground truth and keys remain outside detector
inputs. Review and speed-test scripts also retain private receipts and refuse
existing outputs.

## Limits

Historical totals are retained response costs, not verified account bills or
proven HTTP-attempt counts. Missing retry records cannot be reconstructed by
assumption. The depth-six checker covers bounded configurations, not every world
size; the new zero-seat mode also has targeted behavioral tests. Runtime matrix
configuration and local success alone do not establish hosted execution, cloud
security, provider qualification, deployment or live-study acceptance.
