# Verify the institution, not the agents

Added 2026-11-08 on branch `feat/live-swarm` by IPBin (with Claude Code). This is the part of
Fleet Witness that calls real models. Everything earlier in the repo remains the scripted
mechanism study.

## Thesis

Aligning every agent in a swarm does not scale: the cost grows with the number and
capability of agents, and one captured agent can break it. Human societies instead put
guarantees in **institutions**: separation of powers, signatures, audits.

An agent institution is code, so two things become possible:
1. **Bounded formal verification** of its rules.
2. **Stress-testing it against a real LLM swarm** that contains a colluding cell.

## Components

| File | Role |
| --- | --- |
| `fleet_witness/institution.py` | Separation-of-powers kernel. The legislature sets policy, a worker or the swarm proposes, a kernel-seated auditor committee attests (k-of-m, per-auditor keys), and the executive commits each release and its audit event atomically. The kernel checks mechanics (integrity, seating, binding, quorum, policy, uniqueness) and delegates the semantic safety judgement to auditors: the attack surface. |
| `fleet_witness/verify_institution.py` | Bounded exhaustive state exploration of the **real** kernel (SQLite + HMAC) against an independently written specification. It checks safety, liveness, at-most-once release and audit completeness. Seven mutant kernels show the checker catches broken rules. It also contains the exact capture probability for a committee drawn from N agents with C colluders and honest error rate ε. |
| `fleet_witness/swarm/` | Live LLM swarm (OpenRouter or Adaption): reviewers vote in waves, the board is visible or hidden (herding), and a hidden colluding cell pushes invalid releases. A kernel-drawn committee of 7 audits each case. The same votes and attestations are judged under each regime. |

Regimes compared:

| Regime | Rule | Cost |
| --- | --- | --- |
| `direct` | Swarm majority acts, no kernel | N calls |
| `auditor-1of1` | One auditor | 1 call |
| `committee-2of3` | 2 of 3 auditors | 3 calls |
| `committee-3of5` | 3 of 5 auditors | 5 calls |
| `committee-4of7` | 4 of 7 auditors | 7 calls |
| `unanimous-7of7` | All 7 auditors | 7 calls |
| `hybrid-maj+4of7` | Swarm majority plus 4 of 7 auditors | N + 7 calls |

The detector (shared-minority voting plus reason similarity, robust z-scores) and the
OpenRouter LLM judge act as an audit-of-auditors branch.

## Verified so far

- Depth-6 bounded check: 23,376 distinct kernel states, all invariants hold. All 7 mutants
  are caught, each with a shortest counterexample trace.
- 17 unit tests: `python -m unittest tests.test_swarm tests.test_institution`.

## Run

```sh
python -m fleet_witness.verify_institution --depth 6 --mutants
python -m fleet_witness swarm-sweep --root runs/sweep-or --provider openrouter \
  --model deepseek/deepseek-v4-flash-0731 --seed 1000 --max-usd 5
python -m fleet_witness swarm-summary runs/sweep-or runs/sweep-ad
```

## Spend safety

- Every call reserves its worst case in `~/.fleet_witness/spend-ledger.json`.
- Per-run caps, plus lifetime caps of Adaption $100 and OpenRouter $15.
- Certainly-unsent failures (DNS failures, 4xx, rate limits) are not charged.
- Rate limits pause all threads for the provider's requested wait.
- The run stops after 25 consecutive errors.
- Keys come from the user environment only.

## Honest limits

- The check is bounded (small worlds, depth 6), not a proof for all sizes.
- Colluders are instructed; coordination does not emerge on its own.
- One cheap model family.
- Toy release task.
- Novelty is claimed only relative to the literature we could read.
