# Adaption access and qualification

**Adaption inference remains unqualified.** The completed live-supervisor pilot
used OpenRouter, not Adaption. Its [operator runbook](CONTROLLED_PILOT.md) and
[observed results](experiments/2026-11-09-openrouter-paired-pilot.md) describe that
separate provider path. The default scripted lab still needs no key or SDK.

## Recorded access and budget

The owner supplied an account statement showing **1,500 credits**, **$1 per
credit**, with **no expiry**. This is recorded owner evidence, not a fresh balance
query. An earlier authenticated model-list request returned seven hosted model
IDs; it did not make an inference request or establish billing semantics.
The verified key was stored outside the repository in an owner-private host file.
Team membership does not pool accounts or grant credential access.

Adaption credit, the OpenRouter allowance and the $100 GCP ceiling are separate.
The authorized calibration ceiling was raised to **up to $15 when required**;
that ceiling does not remove qualification checks or automatically authorize a
larger cohort. See [costs](COSTS.md) for the recorded amounts and their limits.

## Before the first Adaption inference

[ADR-0010](adr/0010-trusted-live-model-gateway.md) requires applicable account and
source evidence, bounded transport and accounting, and an accepted activation
record. Resolve the provider-specific facts before issuing that record:

- Confirm applicable model/revision, rates, all billable reasoning/output bounds,
  extra charges or minimums, and the account's per-request reconciliation source.
- Establish applicable retention, deletion, training and upstream handling terms.
  Request controls alone do not establish zero retention.
- Qualify the actual host, credential loading, runtime, trust and egress boundary
  for this provider; keep workers and supervisor inputs outside secret authority.
- Use the canonical shared ledger, preserve outstanding liabilities, and reconcile
  the bounded calibration before planning a new cohort.

Public model tables and API listings do not establish account-specific billing.
No new approval of the unchanged budget is needed to research these facts. The
[current gates](GATES.md) records the separation from completed OpenRouter work.

## Historical integration research

The November 8 notes below preserve the initial proposal, SDK example and dated
prices. They are **not current setup instructions, fresh prices or activation
permission**. Their proposed amounts and “future” status predate the implemented
host gateway and the later calibration ceiling. Use the maintained runbook above
for operational work; do not run a standalone SDK example around its controls.

<details>
<summary>November 8 access, SDK and planning notes</summary>

## Controlled-pilot continuation: 2026-11-08

The owner reported that the account displays 1,500 credits and that one credit
equals $1. This is owner-provided information; the current balance and
account-specific billing terms were not retrieved independently. A read-only
authenticated model-list request succeeded and returned seven available hosted
models; no inference request was made. The verified key is stored outside the
repository in an owner-private host file.

The owner authorized proceeding with the controlled pilot, and
[ADR-0010](adr/0010-trusted-live-model-gateway.md) records the accepted design.
An offline calibration fixture exercises a fixed one-credit reservation and
provider-shaped responses but has no credential access or network transport.
It is not a real model, a verified provider spending cap, or a live result.
Provider billing and reasoning-token bounds, one globally shared live
authorization, the production TLS path and independent activation review
remain prerequisites for the first paid request. A local reservation alone
cannot cap what a provider charges.

Status checked **2026-11-08**. The implemented backend remains `scripted-demo`:
the Python baseline needs no SDK, API key, provider account, or model credit.
This guide records future integration requirements; it does not implement an
adapter, spending gateway, or automatic coding fleet. The `adapter-proposal` task is delivered and ADR-0010 accepts the design. The
production adapter and activation are still gated; see [current gates](GATES.md).

## Ownership, balance, and units

Alejandro Castellanos (`k2jac9`) remains the account and repository owner;
`IPBin` has joined the project as a teammate. Team membership does not establish
additional credits, pooled accounts or credential access. Alejandro confirmed
**$1,500 in available Adaption credit balance** for planning. This is an owner-provided account fact,
not an API-verified balance or a new grant claim. The earlier four-person,
four-times-$1,500 discussion does not apply. Public event offers may describe
different grant amounts; they do not replace the owner's account statement.
Adaption credit does not pay the separate [GCP bill](COSTS.md).

The [hosted model table](https://docs.adaptionlabs.ai/inference-stacks/models/)
quotes **credits per one million tokens**, with separate input, cached-input,
and output rates. The owner has since reported a one-credit-per-dollar
conversion, but account-specific pricing and billing semantics have not been
independently verified. Do not divide the reported balance by the example totals
to promise a request count; verify applicable charges and bounds first.

## Confirmed interfaces; optional future setup

Adaption offers a hosted Responses API and an official Python SDK using
`from adaption import Adaption`; see the [inference quickstart](https://docs.adaptionlabs.ai/inference-stacks/quickstart/),
[SDK reference](https://docs.adaptionlabs.ai/api/python), and
[Responses reference](https://docs.adaptionlabs.ai/api/python/resources/responses/methods/create).
A standalone provider command-line client has not been verified. A terminal
Python program using the SDK is sufficient for future integration; do not
invent an `adaption` CLI command.

The quickstart requires SDK 0.16.0 or later. [PyPI lists 0.19.0](https://pypi.org/project/adaption/0.19.0/)
as released on November 5, 2026. The following is an **optional future setup**
on the trusted gateway host, separate from the baseline and Nix worker image.
It was not installed or executed for this handoff:

```sh
python3 -m venv /absolute/private/path/fleet-provider-venv
/absolute/private/path/fleet-provider-venv/bin/python -m pip install 'adaption==0.19.0'
```

Pin and review transitive dependencies with hashes before a reproducible
provider deployment. Keep this environment outside the worker source snapshot.
After separately authorizing credential creation, sign in to Adaption, open
Settings → API keys, and store the key through a host secret manager or a
protected runtime credential. The SDK reads `ADAPTION_API_KEY`; inject it only
into the trusted gateway process. Never put its value in Git, a flake/Nix
expression, the Nix store, VM metadata, shell history, worker environment,
replay, or log. See [security boundaries](SECURITY_POLICY.md).

This illustrative SDK shape would make a billable network request if called.
It is **not** a Fleet Witness command or an implemented budget gate:

```python
from adaption import Adaption

def authorized_example(supervisor_input: str):
    # Caller must first reserve the request's worst-case budget.
    with Adaption(max_retries=0, timeout=30.0) as client:
        return client.responses.create(
            model="gemma-4-31b-it",
            input=supervisor_input,
            max_output_tokens=512,
            tools=[],
            tool_choice="none",
            store=False,
        )
```

Explicitly disabling tools and response storage avoids inheriting optional
stack behavior. It does not establish all provider or upstream data-retention
terms. Review those terms before sending sensitive data. The
[SDK](https://docs.adaptionlabs.ai/api/python) documents automatic retries;
disable them initially so the future gateway controls and accounts for every
attempt. A timeout does not prove the provider performed no billable work.
Model availability depends on the account; public catalogue presence is not an
access test.

## Token-cost examples

Rates below are a dated snapshot of the
[official model table](https://docs.adaptionlabs.ai/inference-stacks/models/),
using uncached input and no extra charges. The example is **1,000 calls across
the whole fleet**, each with 10,000 input and 2,000 output tokens: 10 million
input and 2 million output tokens total. It is not 1,000 calls per worker.

| Hosted model ID | Input credits / 1M | Output credits / 1M | Example total credits |
| --- | ---: | ---: | ---: |
| `deepseek-v4-flash` | 0.04444 | 0.13332 | 0.71104 |
| `gemma-4-31b-it` | 0.09 | 0.34 | 1.58 |
| `qwen3.5-397b` | 0.55 | 3.50 | 12.50 |
| `glm-5.2` | 1.40 | 4.40 | 22.80 |

Formula: `credits = input_tokens / 1_000_000 × input_rate +
output_tokens / 1_000_000 × output_rate`. Cached pricing applies only to
provider-confirmed cached tokens. Retries, growing conversation history,
billable reasoning, and enabled tools can change the real total. Do not assume
visible answer length equals all billed output. Measure actual reported usage
and reconcile it against billing before scaling.

## Proposed budget contract, not implemented

Reserve **$1,400-equivalent of the stated credit balance** and use at most a
**$100-equivalent pilot envelope**, only after verifying the conversion into
provider credits and obtaining explicit authorization for the experiment.
These are planning allocations, not enforced caps, additional cash deposits,
or permission to spend now. Start with 50–100 tightly bounded requests inside
that envelope to calibrate billing units, latency, failure rates, and actual
token usage. Stop on accounting mismatch or unexpected tool use.

The future host-side gateway must provide:

1. A persistent shared ledger in verified provider units. Atomically reserve
   worst-case input, maximum billed output/reasoning, and all permitted retry
   costs **before** dispatch. Parallel workers cannot each assume the same
   remaining balance is theirs. Also bound requests, concurrency, wall time,
   input length, output length, and tool calls.
2. Fail-closed dispatch when rates, model access, usage accounting, or available
   balance are unknown. Keep pending reservations for ambiguous failures until
   reconciled; release unused reservations only on trustworthy usage evidence.
   Record every attempt and reconcile provider billing against the ledger.
3. An offline fake covering exhaustion, concurrent reservations, timeouts,
   retries, malformed responses, and recovery. Paid tests stay opt-in and
   separate from ordinary unit tests and CI.
4. An allowlisted supervisor input and parsed recommendation only. Preserve
   sealed scenario truth and issuer keys; do not send evaluator answers or
   exported replays as model input. Keep paired facts identical. The trusted
   controller still owns authorization and transactional effects.

The provider-neutral proposal and ADR-0010 now define the design. A real
provider transport, full spend enforcement, tests and independent activation
review remain necessary. Automatic coding-worker dispatch is another future
capability; current workers run offline tests and the scripted demo.

## Adaptive Data and AutoScientist are separate workflows

The [FAQ](https://docs.adaptionlabs.ai/resources/faq/) and
[Adaptive Data configuration guide](https://docs.adaptionlabs.ai/adaptive-data/configure-adaptive-data/)
document `datasets.adapt(..., estimate=True)` to estimate an adaptation job
without starting the full adaptation. This is not an inference token estimate
or a general no-side-effect sandbox: the [adaptation API reference](https://docs.adaptionlabs.ai/api/resources/datasets/methods/adapt)
says column mappings and expansion settings are still saved to the dataset.
Actual usage can vary. Use a disposable dataset, inspect
the exact configuration, and obtain a fresh estimate before an authorized run.
No such job was submitted here.

Dataset adaptation, training, and AutoScientist have different workloads and
cost drivers from Responses inference. Do not start an unbounded automated
research loop on the strength of the inference table. Any later study needs
its own small-data estimate, bounded runs, stop criteria, billing reconciliation,
and explicit budget. See [research and policy scope](SECURITY_POLICY.md).

</details>
