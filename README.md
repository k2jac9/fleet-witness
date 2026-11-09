<p align="center">
  <img src="docs/assets/fleet-witness-hero.svg" alt="Fleet Witness. Swarms can agree. Evidence has to hold. A controlled research lab for inspecting evidence, authority and effects." width="100%">
</p>

<p align="center">
  <strong>🛰️ SWARM ALIGNMENT HACKATHON · MISSION CONTROL FOR AGENT AUTHORITY</strong><br>
  <a href="docs/report/latest.pdf">Read the latest paper</a> ·
  <a href="docs/submission/latest-submission.zip">Get the submission package</a> ·
  <a href="docs/submission/media/fleet-witness-demo.mp4">Watch the three-minute walkthrough</a> ·
  <a href="#-launch-the-local-lab">Launch the lab</a> ·
  <a href="docs/experiments/2026-11-09-openrouter-paired-pilot.md">Inspect the live pilot</a> ·
  <a href="docs/README.md">Browse the docs</a>
</p>

# Fleet Witness

**Swarms can agree. Evidence has to hold.** Fleet Witness is a research testbed for the moment an AI fleet turns a recommendation into an action. Follow a proposal through its evidence, its permission check and its final audit trail. The trusted controller alone can commit a release: a local database record with an audit event in the same transaction.

Built by **Alejandro Castellanos** (Independent researcher) and **Ignatius Pio Binawan** (University of Toronto, [IPBin](https://github.com/IPBin)). AI development agents are tools; the experimental agents are a separate system. [Contributions and AI assistance](docs/AI_ASSISTANCE.md).

## 🧭 Your mission: follow the authority

![Three checks: is the evidence authentic, does it apply to this action, and is execution currently authorized? The controller commits effect and audit together.](docs/assets/fleet-witness-mission.svg)

A genuine build receipt proves a build happened. A release also needs applicable safety evidence and current permission. The lab lets you inspect three distinct outcomes:

| Checkpoint | The question |
| --- | --- |
| **Decision** | Was the recommendation valid at its original snapshot? |
| **Execution** | Was the action authorized when the controller attempted it? |
| **Effect** | Did a release actually commit? |

Permission can be revoked after a valid approval. An invalid approval stays invalid even when the controller blocks it. Repeating an already committed authorized release is a no-op. These distinctions are the heart of the experiment.

## 🔬 The experiment log

![Separate evidence: 32,830 historical logical responses, 160 requests in the new live-supervisor pilot, and 30 valid local effects in that pilot.](docs/assets/fleet-witness-results.svg)

| Evidence | What happened | What it supports |
| --- | --- | --- |
| **Bounded institution check** | 23,376 states, 105,708 transitions; all seven injected mutants caught | Agreement with the project specification inside the explored bounds |
| **Historical swarm study** | 32,830 completed logical responses; two models; 50-agent swarms | A comparison of majority and committee rules on retained, shared outputs; original provider-attempt totals remain unknown |
| **New controlled pilot** | 160 requests, 80 pairs, one live supervisor; synthetic workers and reviewers | Raw instructions yielded 18 invalid approvals. Explicit instructions denied every case, including 40 valid ones |
| **Pilot enforcement** | 30 valid local releases, 28 denied attempts, ten duplicate no-ops | No invalid or revoked attempt produced an effect in this cohort |
| **Pilot accounting** | $0.2605526 reconciled provider charge; $0.288090 conservative settlement | This cohort's cost only; calibration and historical records are separate |

**The plot twist:** removing unsafe approvals by refusing everything is not useful model judgment. The pilot exposes that failure while showing the controller's enforcement boundary. The new [paper](docs/report/latest.pdf), [public trial table](data/paired-pilot-2026-11-09.json) and [evidence guide](docs/submission/latest/EVIDENCE.md) retain both results. No uncontrolled web swarms were observed.

## 🎥 Step inside mission control

[Watch the captioned three-minute walkthrough](docs/submission/media/fleet-witness-demo.mp4) ([captions](docs/submission/media/fleet-witness-demo.vtt), [media provenance](docs/submission/media/README.md)). It shows actual scripted viewer states, followed by the separately recorded live-supervisor findings.

![Actual seed-42 Fleet Witness viewer, clearly labeled Scripted demo: 10 evidence pairs, seven invalid recommendations, nine denied attempts and four local effects.](docs/assets/fleet-witness-viewer.png)

Verify the portable submission from this checkout with one offline command:

```sh
python3 -m scripts.verify_submission
```

This checks the allowlist, checksums, repository bytes, publication metadata and recomputed pilot totals. It does not authenticate private provider execution. The [evidence guide](docs/submission/latest/EVIDENCE.md) also covers the standalone package.

## 🚀 Launch the local lab

Use the [current pinned runtime matrix](ci/runtime-matrix.json). Python 3.11+ and Node 24 remain supported consumers. The application uses the Python standard library; Node runs viewer tests. The default demo is **scripted**, works offline and requires no API key or cloud account.

```sh
git clone https://github.com/k2jac9/fleet-witness.git
cd fleet-witness
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 -m fleet_witness demo --output runs/demo --seed 42
python3 -m fleet_witness serve --directory runs/demo --port 8765
```

Open **http://127.0.0.1:8765**. Pick a decision, follow its receipt scope, compare `raw` with `scope_explicit`, and inspect the ordered audit events. Stop with Ctrl-C. Each run needs a fresh output directory; existing databases are never overwritten. Linux/POSIX serving is supported. The viewer is read-only and loopback-only by default, with an asset allowlist, text-only trace rendering and no CDN or telemetry.

With Nix and flakes enabled, `nix develop` provides the pinned development shell. The [development guide](docs/DEVELOPMENT.md) covers setup; [testing](docs/TESTING.md) explains what each check establishes.

<a id="handbook"></a>

## 🎬 Choose your next scene

The [documentation map](docs/README.md) connects the guides and defines the shared vocabulary.

| Destination | Open this |
| --- | --- |
| **Research desk** | [Latest manuscript source](docs/report/latest.md), [PDF](docs/report/latest.pdf), [verified references](docs/report/latest.references.json), [provenance](docs/report/latest.provenance.json) |
| **Submission bay** | [Portable package](docs/submission/latest-submission.zip), [submission guide](docs/SUBMISSION.md), [copy-ready form details](docs/submission/latest/SUBMISSION.md), [three-minute demo script](docs/submission/latest/DEMO.md) |
| **Archive room** | [Preserved earlier report](docs/report/REPORT.pdf), [corrections and reproduction](docs/report/CORRECTIONS-2026-11-09.md), [historical experiment archive](data/fleet-witness-runs-2026-11-08.zip) |
| **Engine room** | [Architecture](docs/architecture.md), [accepted ADRs](docs/adr/README.md), [contributing](CONTRIBUTING.md), [agent contract](AGENTS.md) |
| **Flight recorder** | [Observed build status](docs/BUILD_STATUS.md), [current gates](docs/GATES.md), [runtime adoption](docs/RUNTIME_ADOPTION.md) |
| **Fleet workshop** | [Reviewed task workflow](fleet/README.md), [NixOS workers](docs/NIXOS_FLEET.md), [roadmap](docs/ROADMAP.md) |
| **Cloud operations** | [GCP deployment](docs/DEPLOY_GCP.md), [operations](docs/OPERATIONS.md), [configuration example](deploy/gcp.env.example), [costs](docs/COSTS.md) |
| **Security desk** | [Security and research policy](docs/SECURITY_POLICY.md), [resource map](docs/RESOURCES.md), [Adaption qualification](docs/ADAPTION.md) |

## 🛡️ Keep the boundary visible

The scripted demo, historical swarm study and new live-supervisor pilot are distinct evidence sources. Evaluator labels are for human inspection and stay outside supervisor inputs. The institutional study relies on auditors for semantic judgments; the new pilot uses a stricter synthetic evidence contract. Their results are not pooled.

The prototype uses in-process HMAC authentication and SQLite. Saved databases are inspection artifacts; ephemeral issuer keys are not persisted. Worktrees and containers do not establish isolation from hostile operating-system processes. Finite checks do not establish an unbounded proof. No live sensor, public honeypot or global fleet map is implemented.

Native GCP boot, four offline verification workers and an authenticated read-only Cloud Run dashboard have historical execution receipts. Current availability and expiry require fresh checks; this README is not a live status monitor. Deployment, paid calls and new observation scopes use the [documented gates](docs/GATES.md), separate authorization and explicit budgets. Provider keys never belong in source, a Nix image or the public submission package.

## 🪪 Credits and provenance

The repository began on 8 November 2026. Earlier conceptual work informed the initial design; the institutional study and original manuscript were contributed by Ignatius Pio Binawan. The new pilot and publication package preserve original records and failed-run evidence. See the [AI assistance disclosure](docs/AI_ASSISTANCE.md) for attribution and the [submission guide](docs/SUBMISSION.md) for sprint rules.

Original code: [MIT](LICENSE). Preparing this repository and package does not submit an entry to the event.
