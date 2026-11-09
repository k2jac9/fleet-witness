# Fleet Witness documentation

Start with the [project overview](../README.md) or choose a path below. The default
lab is offline and scripted. The historical swarm study and completed live-model
pilot have separate methods, denominators and provenance.

| I want to… | Start here |
| --- | --- |
| Read the findings | [Latest paper](report/latest.pdf), [editable manuscript](report/latest.md), [public trial data](../data/paired-pilot-2026-11-09.json) |
| Run the local lab | [Development](DEVELOPMENT.md), [testing](TESTING.md) |
| Understand the design | [Architecture](architecture.md), [accepted decisions](adr/README.md) |
| Reproduce the research | [Evidence guide](submission/latest/EVIDENCE.md), [historical data guide](../data/README.md), [swarm methods](SWARM.md) |
| Understand the live pilot | [Observed experiment](experiments/2026-11-09-openrouter-paired-pilot.md), [operator runbook](CONTROLLED_PILOT.md) |
| Contribute a change | [Contributing](../CONTRIBUTING.md), [development fleet](../fleet/README.md), [runtime matrix](RUNTIME_ADOPTION.md) |
| Check progress and open work | [Current gates](GATES.md), [roadmap](ROADMAP.md), [dated build evidence](BUILD_STATUS.md) |
| Operate infrastructure | [NixOS workers](NIXOS_FLEET.md), [GCP deployment](DEPLOY_GCP.md), [operations](OPERATIONS.md), [costs](COSTS.md) |
| Review security and provider boundaries | [Security policy](SECURITY_POLICY.md), [Adaption qualification](ADAPTION.md), [resource references](RESOURCES.md) |
| Prepare the event entry | [Submission guide](SUBMISSION.md), [portable ZIP](submission/latest-submission.zip), [AI assistance and contributions](AI_ASSISTANCE.md) |

## A shared vocabulary

| Term | Meaning here |
| --- | --- |
| Development fleet | Tools and optional offline workers used to build and test the repository |
| Experimental fleet | Synthetic roles or instructed model agents inside a controlled study |
| Supervisor | Proposes an approval or denial; cannot directly commit an effect |
| Controller | Checks the applicable contract and current permission, then commits a release and audit together |
| Release / effect | A committed local SQLite record; not a deployment or external publication |
| Decision validity | Whether the recommendation was correct at its original snapshot |
| Execution authorization | Whether the attempted action was permitted at execution time |
| Receipt authentication | An in-process HMAC integrity check; not a public-key signature or independent notarization |
| Replay | An inspection export; not permission to resume an experiment or a new model input |

## Read evidence in context

The [latest report](report/latest.md) is the maintained synthesis. The original
[manuscript](report/REPORT.pdf), [scripted-study draft](research-report.md),
experiment records, reviews and older build entries retain their dated claims.
Accepted ADRs are historical decisions: later acceptance can implement a decision
without rewriting its original status paragraph. Use the gates and observed
records together to determine what has actually passed.

An old successful cloud check does not establish current availability. A budget
is not a current account balance. A configured check is not an executed check.
