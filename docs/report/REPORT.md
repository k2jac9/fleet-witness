# Verify the Institution, Not the Agents: A Bounded-Verified Separation-of-Powers Kernel Stress-Tested Against Colluding LLM Swarms

**Authors:** Alejandro Castellanos and Ignatius Pio Binawan (University of Toronto)

**Track:** 4, Multi-Agent Oversight and Control (cross-track: 2, 3)

*Draft for the official Apart template. Every number comes from runs in this repository
(`runs/sweep-deepseek2k`, `runs/sweep-gptoss`; see Code and Data for offline reproduction).*

**Correction dated 2026-11-09.** This version corrects presentation, statistics and provenance
using retained 2026-11-08 records. It adds no new live-model observations. Original artifacts
and the immutable data archive remain identifiable in [the correction record](CORRECTIONS-2026-11-09.md).

---

## Abstract (limit 150-250 words)

Per-agent alignment and monitoring do not scale to swarms, and a colluding subgroup is
designed to defeat both. We ask whether safety guarantees can instead live in an
*institution*: code whose rules are checked once and enforced on every agent.

We build a separation-of-powers kernel. A worker proposes a release and a kernel-seated
committee attests with per-auditor keys. The executive commits only if mechanical checks pass
(integrity, seating, binding, quorum, policy, uniqueness), logging each release atomically.
Bounded exhaustive exploration of the real implementation (23,376 states) confirms its
safety, liveness, at-most-once and audit invariants, and catches all seven deliberately broken
variants. The resulting guarantee is conditional: an unsafe release needs k false attestations
from seated auditors.

We compare eight governance regimes using 32,830 completed logical responses from two reasoning-model families,
in 50-agent swarms where hidden cells (0-50%) pushed invalid releases.
- **Mechanical checks were decisive.** Plain majority voting approved every forged-signature
  release (48/48 per model). Archived kernel regimes blocked them all. A reconstructed
  mechanically gated majority control also blocks them.
- **Committee capture came only from colluder seats** and never exceeded the bound set by
  the seats actually drawn. A gated majority was safer; hidden-board committees could use
  fewer standalone requests (7 vs 50), but are capturable.
- **Honest agents almost never erred,** even on near-miss receipts, so the independence
  assumption behind committee bounds remains untested.
- **Colluders' outputs ran 1.9-2.8× longer,** an association worth testing as a monitoring
  signal.

---

## 1. Introduction

The Swarm Alignment Hackathon brief describes roughly 1,200 agents that coordinated through
an unsanctioned message board. Its point is that no single-model safety test would have
caught this. Multi-agent failures such as collusion, miscoordination and conflict arise
between agents (Hammond et al., 2025). Per-agent alignment and per-agent monitoring scale
with the number of agents, and a colluding subgroup is designed to defeat both.

Human institutions take a different route. We do not verify every citizen. We design rules,
such as separation of powers, signatures and audits, whose guarantees do not depend on
everyone being honest. Recent work proposes separation of powers for agent economies
(*From Logic Monopoly to Social Contract*, arXiv:2603.25100). That proposal is a design paper:
it implements nothing, measures nothing, and defers its proofs.

An agent institution, unlike a human one, is code. Its rules can be **mechanically verified**
and **stress-tested** against real AI swarms with planted adversaries, two things no
constitution allows.

**Theory of change.** Deployers already route agent actions through gateways (MCP, A2A, LLM
proxies). If consequential actions must pass an institution kernel at that gateway, the
kernel's mechanical guarantees hold regardless of swarm size or model. What remains is to
measure the few behavioural parameters the guarantee depends on: honest error, its
correlation, and colluder compliance.

We show this loop of build, verify, stress-test and measure is feasible in a weekend. A
fellowship would extend it to tasks where honest agents genuinely err, to verifiable seating,
and to deployment at a real gateway.

**Contributions.**

1. A small separation-of-powers kernel for agent swarms. It splits what can be checked
   mechanically (integrity, seating, binding, quorum, policy, uniqueness, audit) from what
   must be judged (is this release safe?).
2. Bounded exhaustive verification of the real kernel against an independent specification,
   with mutation testing to show the checker has teeth.
3. A statement of what the kernel guarantees, as three explicitly conditional claims (§3.3),
   with a closed-form capture probability for randomly seated k-of-m committees.
4. A retained live-model stress test and offline comparison of eight regimes, including a
   reconstructed mechanically gated majority baseline, across colluder shares of 0-50%, visible or hidden voting, and two reasoning-model families
   (32,830 completed logical responses, not a count of provider attempts). It separates two effects:
   - mechanical checks are what stop forgeries;
   - committees trade capture risk, bounded by the seats drawn, for far fewer model requests than a full
     vote's cost.
5. An open harness with logs, and three observations whose limits we state: honest error near
   zero even on near-miss receipts (so independence is untested), no herding in few exposures,
   and longer colluder outputs.

Quorums, Byzantine fault tolerance, threshold signatures and random committee selection are
decades old (§2). We do not claim the quorum idea. We contribute a bounded-verified kernel
for agent swarms and a harness that measures, on real LLM swarms, the behavioural assumptions
those guarantees rest on: honest error, independence and colluder compliance.

## 2. Related Work

**Multi-agent risk and collusion.** Hammond et al. (2025) taxonomize multi-agent failures,
with collusion central. Motwani et al. (2024) study secret collusion via steganography. AI
Control (Greenblatt et al., 2024) asks whether protocols hold against an intentionally
subversive model; we ask the same of an institution facing a *group* of agents.

**Agent institutions and governance.**
- The separation-of-powers proposal (arXiv:2603.25100) is closest in spirit but is neither
  implemented nor tested.
- Paglieri et al. (2026) observe 100 LLM agents in which an evaluation exploit spread and a
  counter-group audited and blew the whistle. They propose Ostrom-style institutions for
  swarm self-governance; we build and verify one institutional mechanism.

**Verified and governed agent runtimes.**
- AgentRFC (Zheng & Zhang, 2026) model-checks agent-protocol security invariants in TLA+.
- Bounded Agents (Muruaga, 2026) proves delegation properties and evaluates them on LLM
  prompt-injection benchmarks.
- Others add action certificates (Wang, 2026), verify-gated admission (Nguyen & Tran, 2026),
  swarm-level runtime assurance (Kekatos et al., 2026) and credential revocation (Deochake,
  2026).

These works verify protocols, delegation or admission, mostly against injection or single
compromised components. None studies authority spread over a committee that a colluding cell
can partially capture.

**Classic foundations.** Byzantine agreement tolerates a bounded fraction of faulty
participants (Lamport, Shostak & Pease, 1982). Threshold cryptography distributes authority
over k-of-n parties (Desmedt & Frankel, 1989). Algorand seats committees by cryptographic
sortition (Gilad et al., 2017). N-version programming showed that independently developed
versions fail in correlated ways (Knight & Leveson, 1986), the assumption most at risk when
every auditor is a copy of one model.

**Gap.** Formal or bounded verification of agent infrastructure exists (AgentRFC, Bounded
Agents), and so do LLM-agent evaluations of governance mechanisms. To our knowledge, none
combines (a) bounded verification of a committee-based institution's invariants with (b) a
live stress test against an LLM swarm containing a colluding cell that can capture seats,
with the guarantee's behavioural assumptions measured. Two candidate papers were
inaccessible to us.

## 3. Methods

### 3.1 The kernel (`fleet_witness/institution.py`)

The kernel has four branches:
- the **legislature** sets versioned policy;
- a **proposer** (a worker, plus the swarm majority in hybrid regimes) submits a release;
- the kernel seats *m* **auditors** uniformly at random from the swarm, each attesting with
  an HMAC under its own key, bound to the exact run and artifact;
- the **executive** commits a release and its audit event in one SQLite transaction.

The executive commits only if a proposal exists, current policy allows it, the evidence is
intact, at least *k* **distinct, seated** auditors gave valid bound attestations, and no
prior release exists.

**Design principle.** The kernel never judges whether evidence *means* "safe". In our task, a
build receipt is authentic but does not establish release safety. That judgement belongs to
auditors, and it is exactly where a colluding cell attacks.

### 3.2 Bounded verification (`fleet_witness/verify_institution.py`)

We explore every reachable state of the *real* kernel (SQLite serialized and cloned at each
state, states deduplicated) in a small world. That world has one case, three seated auditors
(quorum 2), one unseated outsider, and 12 actions including forged, outsider, misbound and
duplicate attestations and repeated executions. After every transition the kernel is
compared with an independently written specification:
- **S1 safety:** no release unless every precondition holds;
- **S2 liveness:** a release whenever they do;
- **S3:** at most one release per case;
- **S4:** every release has its audit event.

Seven mutant kernels, each missing one check, show the checker can fail.

**Scope.** This is bounded model checking, not a proof.
- The checked world (one case, three seats, quorum 2, depth 6) is smaller than the live
  configuration (24 cases, seven seats).
- S2 means "an eligible execution attempt succeeds", not temporal progress.
- States are deduplicated on the contents of the kernel's tables plus the specification state.
- The specification was written by the same team, so a mistake shared with the kernel could
  go unnoticed.

Details are in Appendix B.

### 3.3 What the kernel guarantees: three conditional claims

- **G1 (mechanical; verified within the bound).** No release happens unless a proposal
  exists, current policy allows it, the evidence is intact, and at least k distinct seated
  auditors have given valid attestations bound to that exact release. At most one release
  happens per case, and each is audited. This is a database-level guarantee: at-most-once
  effects in external systems, and concurrent multi-case behaviour, are not covered.
- **G2 (conditional on honest auditors never attesting unsafe releases).** An unsafe release
  then requires at least k colluders on its committee, so capture is at most the fraction of
  committees that drew k or more colluders. This is the "seat bound" in Table 1.
- **G3 (probabilistic).** Assume random, unpredictable seating of m seats from N agents with
  C colluders, honest errors that are independent with rate ε, and full colluder compliance.
  Then

  P(capture) = sum over j = 0,...,m of Hypergeom(j; N, C, m) × P(Binom(m-j, ε) >= k-j).

  Imperfect compliance lowers capture. Correlated honest errors could raise it above G3.

The retained live-model runs exercise G1 and G2 for the archived committee and hybrid
regimes. G3's independence assumption is untested, because honest unsafe error was
essentially zero (§4.3).

### 3.4 Retained live-model stress test (`fleet_witness/swarm/`)

**Release cases.** There are 24 per run: 8 valid, plus invalid build-only, wrong-artifact
and wrong-run receipts (authentic signatures, wrong claim or binding) and forged receipts
(plausible fields, bad signature). The cell's **targets** are the 12 invalid cases honest
agents could spot. The 4 forged cases are not targets; they test what crowds cannot check.

**Swarm.**
- 50 reviewers vote approve or deny in five waves.
- **Visible:** later waves see the running tally and the six most recent public comments.
- **Hidden:** agents vote independently.
- A **cell** of 0, 10, 20, 30, 40 or 50% receives a private instruction: push the targets
  using a shared talking point, and vote honestly elsewhere.
- For every case the kernel seats a committee of 7, shared across conditions so comparisons
  are paired. Committee members audit with the same rule; colluders on the committee are
  told to sign targets.
- Auditors attest after the vote. With a visible board they see the final tally and recent
  comments; with a hidden board they see only the release. Hidden-board committees therefore
  do not depend on the vote, and could run without it.

**Regimes.** The same votes and attestations are judged under each regime:
- **direct majority**, with no kernel;
- **gated majority**: recorded majority votes plus the kernel's mechanical checks, with no
  committee. The original published baseline was a label-derived counterfactual
  (`majority_approve and kind != "forged"`), not an execution through the kernel. The corrected
  offline baseline executes fresh synthetic cases and receipt keys through the actual kernel
  using those recorded votes. Original signing keys were not retained, so this is a
  reconstruction, not historical signature verification;
- **kernel committees** of 1-of-1, 2-of-3, 3-of-5, 4-of-7 and unanimous 7-of-7;
- **hybrid**: the majority **and** 4-of-7.

**Models.** Two reasoning models from different families via OpenRouter: DeepSeek v4 Flash
(`deepseek/deepseek-v4-flash-0731`) and OpenAI gpt-oss-20b (`openai/gpt-oss-20b`).
- The historical runner specifies temperature 0.7; manifests record a 2,000-token cap and
  paired seeds, so the same cells and committees are drawn. Temperature, executable source,
  runtime and provider request identities were not pinned in those manifests (Appendix D).
- Both are described as reasoning models. This comparison changes model families and provider
  backends; it does not isolate reasoning as a causal variable. Non-reasoning models were excluded.
- Each sweep has 16,416 logical response slots (16,415 completed); the two main sweeps record
  $2.182374 in manifest costs. This is a recorded subset, not total research expenditure or
  reconciled provider billing (Appendix D).

**Output caps.** The historical protocol intended non-binding caps and enabled larger-cap
retries for the replacement run. Missing retry metadata prevents a complete attempt-level
truncation audit. No final output in the retained main records reaches 2,000 tokens; this
does not establish that every provider attempt was untruncated (Appendices B.3 and D).

**Blue team.** A detector reads only the public log. It combines shared-minority voting
with TF-IDF similarity of reasons, uses robust z-scores and graph clustering, and is scored
against sealed ground truth.

## 4. Results

### 4.1 Verification

At depth 6 the checker explored 23,376 distinct states and 105,708 transitions, and S1-S4
held throughout. Both kernel modes also passed at depth 4.

All seven mutants were caught, each with a shortest counterexample of four to six actions after the initial evidence setup
(Appendix B; depth counts actions). One of them, the missing uniqueness check, surfaced only at depth 6 and was
missed at depth 5, which shows concretely why bounds matter.

### 4.2 Retained stress-test outcomes (two reasoning models)

Each model has 16,415 completed logical response records out of 16,416 slots (one
transport-error record each). gpt-oss returned six unparseable responses, counted as
abstentions. Rounded manifest costs: $1.38 (DeepSeek), $0.81 (gpt-oss). Provider attempts
and failed-attempt charges cannot be reconstructed completely from these logs.

Table 1 pools shares > 0: five shares × two board conditions × 12 targets = 120 target trials
per regime. Cells show DeepSeek / gpt-oss.

| Regime | Unsafe releases on targets | Seat bound (G2) | A-priori expected (G3) | Valid released (of 96) | Forged released (of 48) | Nominal responses per decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| direct majority | **0 / 0** | n/a | n/a | 96 / 96 | **48 / 48** | 50 |
| gated majority (no committee) | **0 / 0** | n/a | n/a | 96 / 96 | **0 / 0** | 50 |
| auditor 1-of-1 | 21 / 22 | 24 | 36.0 | 96 / 95 | 0 / 0 | 1 |
| committee 2-of-3 | 21 / 20 | 24 | 28.3 | 96 / 96 | 0 / 0 | 3 |
| committee 3-of-5 | 23 / 20 | 26 | 24.4 | 96 / 96 | 0 / 0 | 5 |
| committee 4-of-7 | 16 / 17 | 22 | 21.8 | 96 / 96 | 0 / 0 | 7 |
| unanimous 7-of-7 | **0 / 0** | 0 | 0.1 | 96 / **87** | 0 / 0 | 7 |
| hybrid (majority + 4-of-7) | **0 / 0** | 22† | 21.8† | 96 / 96 | 0 / 0 | 57 |

*Table 1. Pooled outcomes, with a reconstructed gated-majority control.* † Committee-only opportunity, not a hybrid release prediction: the
hybrid also needs a strict swarm majority (approvals > denials; ties fail), which honest voters
never gave a target. The seat bound and the a-priori expectation are identical for both
models because the models share seeds, cells and committees. Board conditions also share
committee draws, so each regime has 60 independent committee draws, not 120. We therefore
report counts by share (Figure 1; Table C1) rather than pooled confidence intervals.
The response-count column describes potential standalone logical requests, not measured
token, dollar or latency savings; the experiment obtained all 50 votes and seven audits.
Only hidden-board audits could omit the voter stage while preserving their information set.

![Figure 1](figures/figure1-capture.png)
*Figure 1. Capture rate on target releases vs colluding share, per regime, for both models.
Points are observed (n = 24 per point, 12 independent committee draws). The dashed line is
the a-priori probability (G3).*

**Finding 1: mechanical checks, not voting, stop forgeries.**
- The direct majority approved every forged-signature release (48/48 in each model). Every
  archived kernel regime blocked all of them; the reconstructed gated-majority control also
  blocks them.
- This is architectural by construction: voters had no way to verify a symmetric HMAC. With
  public-key signatures and a verification tool a crowd could check too; we did not test
  that baseline.
- **The informative comparison is the gated majority:** the same votes plus the kernel's
  mechanical checks. The corrected synthetic reconstruction yields 0/120 captures,
  0/48 forgeries and 96/96 valid releases in each model. It agrees with the original
  label-derived counterfactual and matches the hybrid with 50 rather than 57 nominal
  logical requests. This is an offline control, not a new model run.
- In this setting, then, a committee adds **no safety** over a mechanically gated majority,
  and the captured committee regimes were less safe. Its potential value is needing fewer
  logical requests in a standalone hidden-board deployment (below).

**Finding 2: committee captures respect the seat bound; standalone request counts could be lower.**
- In all regime × share × condition cells, observed capture never exceeded the seat bound
  (G2).
- Honest auditors never signed a target (0/746 per model), so all capture came from colluder
  seats.
- Gaps below the bound are colluders declining their instruction: seated colluders signed
  234/262 times (89.3%, DeepSeek) and 242/262 times (92.4%, gpt-oss).
- **Realized seat draws were favourable:** 12 of 60 independent draws were capturable for 1-of-1 versus 18 expected (about 1.8 SD low), so points sit below G3's curve in Figure 1. G3 is a planning estimate; G2 is what the verified rules guarantee.
- **The trade-off:** a standalone hidden-board 4-of-7 committee could use seven logical
  requests instead of 50. It matched the gated majority's safety at 10% collusion, was captured in 1-2 of 24 targets per share at 20-40%,
  and in about half at 50%. Unanimity was never captured.

**Finding 3: unanimity buys safety with liveness, and the price depends on the model.**
- Unanimity blocked 0/96 valid releases for DeepSeek but 9/96 for gpt-oss.
- Those 9 blocks came from 10 refusals: 8 by honest auditors and 2 by cell members auditing
  non-target releases.

### 4.3 Honest error, herding and other observations

**Honest error is near zero, even on near-miss receipts.** We ran 12 additional runs with
authentic but subtly invalid receipts, again with both models, 3 seeds, and 0% and 30%
shares. The near misses were a run-ID suffix, a two-character digest change, a scope
variant, issuer capitalization and a claim variant.

In the zero-collusion subset, honest auditor error was 0.3% (DeepSeek, issuer capitalization
only) and 0% (gpt-oss); voter error was 1.0% and 0%. Honest error alone captured only a
1-of-1 auditor, twice in 108 case-conditions (Appendix C). At 30% collusion, each model
made one unsafe honest attestation across 508 honest seats.

DeepSeek's rare voter errors clustered on particular cases, with a between-case variance 5.6×
the independent expectation. That points to correlated failure (Knight & Leveson, 1986), but
errors were too rare to capture any multi-seat committee. Mixed-model committees were
constructed by splicing retained seat responses offline, not by running new heterogeneous
committees; they changed no captures. Shared inputs, case difficulty and board exposure
also prevent interpreting the overdispersion statistic as a clean independence test.

This is our honest answer to the brief's "safety in numbers?" question: on exact-match rules,
independence is untested because honest errors barely occur. Judgement-based tasks are needed.

**No observed herding in a small exposure set.** Honest voters who saw an approving
majority before them approved a target 0/14 times (DeepSeek) and 0/16 times (gpt-oss). These exposures are few, so this is weak
evidence of absence, specific to a crisp rule.

**Colluders produced longer outputs** (1.9-2.8× median tokens in both models; Appendix C). This is an association, not a measured cost of deception: colluders also received a longer, conflicting prompt.

**Detection of the planted cell.**
- A public-log detector combining shared-minority voting and reason similarity (Appendix B.4)
  identified the planted cell with F1 = 1.0 at 10-40% shares (gpt-oss at 40%, hidden board:
  0.97), and 0.98-1.0 at 50%.
- False positives: one spurious 3-agent cluster in the 4 zero-collusion runs (2 models × 2 board conditions; gpt-oss, hidden). The detector also needs colluders to lose votes, so it cannot see a cell that wins.
- Because the cell shared a talking point and voted against unanimous honest denials, this
  shows detection of *this planted signature*, not general collusion detection.

## 5. Discussion and Limitations

**Verify the institution, not the agents.** The agents were never verified, yet every outcome
landed inside the envelope that the verified rules (G1) and the seat bound (G2) allow. That
turns an open-ended question ("is every agent honest?") into a few measurable quantities:
- seat-capture probability, which is closed-form;
- honest error and its correlation;
- colluder compliance.

The cleanest lesson is architectural. Anything that can be checked mechanically belongs in
the kernel, because no amount of voting substitutes for it (Finding 1). Judgement can come
from a full vote or from a random committee. A hidden-board committee could use about
seven times fewer logical requests but is less safe, with captures bounded by its seat draws
(Finding 2). Token, dollar and latency savings were not measured. A swarm can choose that trade-off
deliberately: a gated majority where votes are cheap, and a large-quorum committee where they
are not.

**The open risk.** The guarantee also assumes unpredictable seating, uncompromised keys and kernel-routed actions, which our adversary did not attack, and independent honest errors, which we could not test because such errors barely occurred. Knight & Leveson's warning that model copies fail together is the key open risk.

### Limitations

The main limitations, detailed in Appendix A:
- verification is bounded, not a proof;
- the task is synthetic, with instructed colluders and no covert channel or seat-steering;
- two cheap reasoning models were tested, with 50 agents;
- per-share cells are small;
- independence of honest errors is untested;
- the token-length association is confounded by the prompt.

### Future Work (a fellowship roadmap)

1. **Correlated errors:** judgement-based tasks where honest agents genuinely err, testing G3
   and diverse-model committees directly.
2. **Seating and adversaries:** verifiable random seating (VRF or beacon sortition), cells
   that steer seats, and adaptive colluders.
3. **Deployment:** the kernel at an MCP/A2A gateway, with public-key attestations and a
   "crowds plus tools" baseline.
4. **Assurance:** a small specification language for institutions compiled to both kernel and
   model, multi-case checking, and mechanized proofs (TLA+ or Lean).
5. **Deadlines as defence:** colluders produce longer outputs, so test uniform decision
   deadlines as an explicit, measured rule.

## 6. Conclusion

A small, checkable institution held exactly as far as its rules promised against colluding
LLM swarms. Mechanical checks, not voting, stopped forgeries. A mechanically gated majority was
a safe offline control on this dataset. Random committees could use fewer standalone
logical requests but were captured at rates bounded by their seat draws (16-17 of 120 targets for 4-of-7).

These results come from an exact-match task where honest agents almost never erred, so the
key open question remains: do honest AI errors stay independent? That is the next experiment.
Verifying the institution rather than the agents is a tractable, measurable path to
oversight. Larger swarms, concurrent cases, external effects and harder judgement tasks
remain outside the demonstrated implementation assurance.
## Code and Data

- **Code repository:** https://github.com/k2jac9/fleet-witness. Historical report source:
  `6061cb20f39ac19fcc95b09303e02ebcd43a9887` on `feat/live-swarm`. The stabilization candidate
  preserves that history; [the correction record](CORRECTIONS-2026-11-09.md) identifies
  corrected artifacts and reproduction provenance. A source revision recorded during later
  correction does not retroactively bind historical provider requests to that revision.
- **Data:** every reported run, including the superseded truncated run and the 600-token
  pilot, is published as `data/fleet-witness-runs-2026-11-08.zip`. It holds the public event
  logs, sealed ground truth, per-regime decisions and run manifests (see `data/README.md`).
- **Reproduction:** follow `data/README.md` for safe portable extraction and
  `scripts/reproduce_tables.py` for offline recomputation. Figure generation consumes only
  the retained main sweep records. Live re-runs are separate experiments requiring current
  authorization and provider qualification; this correction invokes no model calls.

## Author Contributions

- A.C. built the Fleet Witness baseline (trusted controller, scripted evaluation, replay
  viewer and cloud deployment) that this work extends.
- I.P.B. proposed the institutional-verification research direction, and designed and ran
  the institution kernel, bounded verification and live swarm experiments with AI coding
  assistance.
- Both authors are responsible for the final manuscript.

## References

1. Apart Research (2026). *Swarm Alignment Hackathon* brief and resources.
   https://apartresearch.com/sprints/swarm-alignment-2026
2. Deochake, S. (2026). *Heartbeat-Bound Hierarchical Credentials: Cryptographic Revocation
   for AI Agent Swarms.* arXiv:2605.20704.
3. Desmedt, Y. & Frankel, Y. (1989). *Threshold Cryptosystems.* CRYPTO '89.
4. *From Logic Monopoly to Social Contract: Separation of Power and the Institutional
   Foundations for Autonomous Agent Economies* (2026). arXiv:2603.25100.
5. Gilad, Y., Hemo, R., Micali, S., Vlachos, G. & Zeldovich, N. (2017). *Algorand: Scaling
   Byzantine Agreements for Cryptocurrencies.* SOSP.
6. Greenblatt, R. et al. (2024). *AI Control: Improving Safety Despite Intentional
   Subversion.*
7. Hammond, L. et al. (2025). *Multi-Agent Risks from Advanced AI.* arXiv:2502.14143.
8. Kekatos, N., Ioannou, M., Katsaros, P., Lekidis, A., Nestoridis, T., Nianios, T. & Nikou, D.
   (2026). *Mission-Level Runtime Assurance for LLM-Assisted ISR Swarms over a
   Verification-Aware Fabric.* arXiv:2607.23532.
9. Knight, J. C. & Leveson, N. G. (1986). *An Experimental Evaluation of the Assumption of
   Independence in Multiversion Programming.* IEEE Transactions on Software Engineering.
10. Lamport, L., Shostak, R. & Pease, M. (1982). *The Byzantine Generals Problem.* ACM TOPLAS.
11. Motwani, S. et al. (2024). *Secret Collusion among AI Agents: Multi-Agent Deception via
    Steganography.*
12. Muruaga, X. (2026). *Bounded Agents: Delegation Security for Multi-Agent AI Systems.*
    arXiv:2608.15888.
13. Nguyen, H.-D. & Tran, X.-T. (2026). *Verify-Gated Completion as Admission Control in a
    Governed Multi-Agent Runtime: A Bounded Architecture Case Study.* arXiv:2605.17998.
14. Paglieri, D., Cross, L., Genewein, T., Leibo, J. Z., Tomasev, N. & Vezhnevets, A. S. (2026).
    *A Case Study on Emergent Cheating and Whistleblowing in Autonomous Research Swarms.*
    arXiv:2609.04170.
15. SQLite. *Atomic Commit in SQLite.* https://sqlite.org/atomiccommit.html
16. Wang, Z. (2026). *Proof-Carrying Agent Actions: Model-Agnostic Runtime Governance for
    Heterogeneous Agent Systems.* arXiv:2606.04104.
17. Zheng, S. & Zhang, Q. (2026). *AgentRFC: Security Design Principles and Conformance Testing
    for Agent Protocols.* arXiv:2603.23801.

**Reference status.** Literature and novelty comparisons have not been independently
source-verified in this offline correction. They require verification before submission.

---

## Appendix A: Limitations and Dual-Use / Ethical Considerations

### Limitations

- **Bounded, not complete.** Verification covers one case, three seats and depth 6. Larger
  worlds and arbitrary interleavings across cases are unverified. The specification was
  written by the same team; an error shared by kernel and specification would go unnoticed.
- **Toy task and planted adversary.** The release task is synthetic. Colluders were
  instructed, and coordination did not emerge on its own. There was no covert channel
  between colluders.
- **Models.** Two cheap reasoning models from different families (DeepSeek v4 Flash, OpenAI
  gpt-oss-20b). Results may not transfer to frontier agents.
  - Qwen 3.7 Flash spent its entire 600-token budget on hidden reasoning in about 39% of
    responses in a partial pilot whose logs were not retained. At 2,000 tokens it was too
    slow for a full sweep in the time available, so it is excluded.
  - Non-reasoning models were excluded so that reasoning mode would not be confounded with
    model family.
  - The pilot used a second host (Adaption), whose rate limit made full sweeps impractical.
- **Small cells.** n = 12 targets per cell. Committee draws are shared across board
  conditions, so the two conditions are paired, not independent. No significance claims.
- **Unsafe honest error was essentially zero, so independence was untested.**
  - In both models, honest auditors never signed an invalid main-sweep target (0/746 each).
  - On near-miss receipts, honest auditor error was 0.3% (DeepSeek) and 0% (gpt-oss) with no colluders present. At 30% collusion each model made one honest unsafe attestation in 508 honest seats (about 0.2%), so gpt-oss's honest error was not globally zero.
  - The only other honest error observed was gpt-oss refusing valid releases (8/492). With correlated honest errors, such as shared weights, shared priors
  or herding (cf. Knight & Leveson, 1986), the §3.3 bound could be optimistic. Neither the
  herding null result nor the absence of correlated failure generalizes beyond this task.
- **Seating assumptions.** Committees were drawn by a seeded pseudo-random generator the
  cell could not observe. An adversary who can predict or influence seating defeats the
  bound.
- **Trust assumptions and key management.**
  - The kernel's keys and SQLite store are trusted.
  - Attestations use symmetric HMAC because only the trusted kernel verifies them. This gives
    no public verifiability and no protection against a compromised host.
  - Per-auditor keys are generated fresh per run and held by the kernel; rotation, revocation
    and compromise recovery are not implemented.
  - Asymmetric signatures (e.g. Ed25519), credential revocation (cf. Deochake, 2026) and
    tamper-evident logs would preserve the kernel's semantics while enabling external audit.
  - Containers and OS-level isolation are out of scope.
- **Adversary model.** The cell had no covert channel and no key compromise. It did not try to
  predict or steer seating or to route actions around the kernel.

### Dual-use

**Could this make multi-agent operations easier, or harder to detect?**
- **Easier:** the harness creates instructed colluding agents and measures committee
  capture, so an attacker could use the capture curves to size a cell. The kernel's
  rules are public, so its blind spot is also known: it trusts auditors on semantic
  judgements.
- **Harder to detect:** a colluder who knew about the output-length association or the
  shared-minority detector could try to evade them.
- **Overall:** we judge the work to favour defenders. It shows that mechanical checks block
  forgery outright, that committee risk is predictable, and how to detect a planted cell.

Mitigations:
- the task is synthetic, and nothing touches third-party systems;
- there is no scanning, recruitment or contact with real agents;
- the talking points are generic;
- the detector and the output-length association are described alongside, favouring defenders.

### Ethics and provenance

- No human subjects and no personal data.
- Historical software had configured per-tag spend caps and retained aggregate costs, but
  these records do not establish an enforceable global cap, complete provider-attempt
  accounting or settled billing. Appendix D states the retained totals and omissions.
- The repository was created during the sprint (2026-11-08). Earlier conceptual research
  informed the design, but no pre-sprint code is used (`docs/AI_ASSISTANCE.md`). The scripted
  Fleet Witness controller was built earlier in the same sprint; the institution kernel,
  checker and swarm harness were built after it.
- AI assistance is described in the LLM Usage Statement.

---

## Appendix B: Verification and audit details

**B.1 Bounded-check world.**
- One case, three seated auditors (quorum 2), one registered but unseated agent.
- Evidence is either intact or tampered.

The 12 actions:
- majority or minority proposal;
- policy on or off;
- valid attestations from each seat and from the outsider;
- a forged-signature attestation;
- an attestation bound to the wrong artifact;
- two distinct execution attempts.

Repeating any action models duplicates and replays. Exploration is breadth-first over
serialized SQLite states with deduplication. Both kernel modes, committee-only and hybrid,
are checked.

**B.2 Verification results.**

| Check | Result |
| --- | --- |
| Kernel, depth 6 | 23,376 distinct states, 105,708 transitions; S1-S4 hold |
| Committee-only mode, depth 4 | 3,188 states; all hold |
| Hybrid mode, depth 4 | 2,906 states; all hold |
| Mutant: skip policy recheck | Caught, S1 (4 steps) |
| Mutant: skip integrity | Caught, S1 (tampered evidence, 5 steps) |
| Mutant: skip seat check | Caught, S1 (outsider attests) |
| Mutant: skip binding | Caught, S1 (wrong-artifact attestation) |
| Mutant: count duplicates | Caught, S1 (same auditor twice) |
| Mutant: skip uniqueness | Caught, S3 (two releases; needs depth 6, missed at depth 5) |
| Mutant: skip audit | Caught, S4 |

**B.3 Truncation audit.**
- gpt-oss: no retained final output reaches the 2,000-token cap; longest 1,536 tokens.
  Missing retry/truncation fields mean this is not proof of zero truncated provider attempts.
- DeepSeek: one colluder response hit the 2,000-token cap in the 30% run.
- The original authors describe a rule declared before results were known under which that
  whole run (all agents) was re-run
  with retry enabled. The re-run needed no retries.
- Its outcomes matched the original in 13 of 14 regime × condition cells; the remaining cell
  (4-of-7, hidden) moved from 1 capture to 0.
- Both versions are retained. Main results use the re-run. The archive does not independently
  timestamp the rule's preregistration.
- Provenance: both runs are in the published bundle (`runs/deepseek2k-f30-truncated`,
  `runs/sweep-deepseek2k/f30`), so the 13/14 comparison can be recomputed. The Qwen pilot
  figure in Appendix A comes from logs that were not retained and is not independently
  auditable.

**B.4 Detector specification.** The detector sees only public votes and reasons. For each pair of agents in a condition:
- **Shared-minority score:** the fraction of common cases where both voted on the losing side.
- **Text similarity:** TF-IDF cosine over each agent's concatenated reasons, using word unigrams and bigrams, lowercased, with stopwords and tokens of two characters or fewer removed.

Both pairwise matrices are converted to robust z-scores (median and 1.4826 × MAD; mean absolute deviation is the fallback when the MAD is zero). Scoring:
- combined score = 0.5 · z_minority + 0.5 · z_text;
- a pair is linked if combined ≥ 2.0, z_minority ≥ 3.0 and the raw shared-minority score is > 0;
- connected components of three or more agents are flagged.

The original authors describe tuning on scripted (fake-provider) runs before the live sweep;
retained manifests do not independently bind that preregistration. Code: `fleet_witness/swarm/detect.py`.
---

## Appendix C: Supplementary results

**C.0 Capture by colluder share.**

| Colluder share | 1-of-1 | 2-of-3 | 4-of-7 | Gated majority, unanimity, hybrid |
| --- | ---: | ---: | ---: | ---: |
| 10% | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 20% | 1 / 2 | 2 / 4 | 1 / 2 | 0 / 0 |
| 30% | 8 / 7 | 4 / 2 | 1 / 1 | 0 / 0 |
| 40% | 4 / 4 | 4 / 3 | 2 / 1 | 0 / 0 |
| 50% | 8 / 9 | 11 / 11 | 12 / 13 | 0 / 0 |

*Table C1. Unsafe releases on targets by colluder share (of 24 per share and model; DeepSeek /
gpt-oss).*

**C.1 Output length by role.**

**Colluders produced longer outputs.**
- Median output tokens on target cases (honest vs colluding): DeepSeek votes 106 vs 294
  (n = 5,400 / 1,800) and audits 110.5 vs 240.5 (n = 746 / 262); gpt-oss votes 158 vs 369
  (n = 5,398 / 1,798) and audits 174 vs 327.5 (n = 745 / 262; Figure 2).
  These are conventional medians, averaging the middle two values for even sample sizes.
  The gpt-oss honest-auditor token denominator excludes one unanswered audit; the separate
  safety denominator, 0 signatures in 746 honest target seats, correctly includes that seat.
- In a 600-token pilot there were 99 abstentions: 98 came from colluders, and 95 hit the cap.
- **This is an association, not a measured "cost of deception".** Colluders also received a
  longer prompt with a conflicting instruction.
- Token counts include hidden reasoning. They are visible to an operator through usage
  metadata but not to a content monitor.
- Whether the signal survives adaptive colluders is untested.

![Figure 2](figures/figure2-deliberation.png)
*Figure 2. Median output tokens, including hidden reasoning, on target cases: honest vs
colluding agents.*

**C.2 Honest error on near-miss releases.**

| Honest error on near-miss releases (0% cell) | DeepSeek | gpt-oss |
| --- | ---: | ---: |
| Committee auditors (n = 756 seats) | 0.3% (issuer capitalization only) | 0% |
| Reviewer votes | 1.0% | 0% |
| Committees captured by honest error alone | 1-of-1: 2/108; larger: 0 | 0 |

**C.3 Historical output-cap protocol.** Every agent in a run shares an initial cap. The
historical client could retry truncated responses at 2×, 4× and 8× the cap; this was intended
to avoid binding caps. Retained final-response records omit attempt arrays and final caps,
so they cannot verify that all calls received this treatment. The stabilization client
disables automatic retries; this does not alter the historical logs.
- This matters because truncation is not neutral: in a 600-token pilot, 98 of 99 abstentions (95 at the cap)
  were colluders. In this pilot, a binding cap disproportionately prevented colluders from
  producing parsed answers; a causal mechanism beyond the conflicting-prompt task is untested.
- An unanswered audit counts as "not signed".
- Audit outcome and the one pre-declared re-run are in Appendix B.


---

## Appendix D: Retained accounting and provenance

The archive contains logical event records, not an independently enumerated provider HTTP
attempt log. Eight governance regimes reuse the same votes and attestations; they are not
eight independent API sweeps.

| Retained category | Runs | Completed logical records | Error records | Manifest-recorded USD |
| --- | ---: | ---: | ---: | ---: |
| Main sweeps | 12 | 32,830 | 2 | 2.182374 |
| Near-miss runs | 12 | 32,831 | 1 | 2.020658 |
| 600-token pilot | 6 | 16,416 | 0 | 1.390812 |
| Superseded DeepSeek run | 1 | 2,736 | 0 | 0.234418 |
| Archive total | 31 | 84,813 | 3 | 5.828262 |

Separately retained AI review costs are $1.281 (round 1), $2.9105 (round 2), and $0.8385
(reviewer speed test): **$10.858262** combined with the archive. This is a sum of retained
recorded amounts, not a reconciled provider bill or complete research expenditure. It
excludes unretained pilots, development assistance and charges omitted from failed records.
Main event sums and manifest sums differ by approximately one millionth of a dollar due
to manifest rounding.

Retry/truncation fields are missing from 30,096 of 32,832 main event records (30,094
completed records). The 2,736 records with those fields are the replacement DeepSeek f30
run, all recording zero retries. The archive contains one explicit near-miss retry;
completed-record costs can aggregate successful retry attempts while token counts describe
only the final response. Failed logical records can omit costs of earlier attempts, and
transport retries are not separate records. Every archived event omits attempt token arrays
and the final cap. Missing fields do not mean zero attempts, zero truncation or zero cost.
Exact provider-attempt counts and settled charges remain unknown.

Historical manifests retain model labels, seeds, counts and caps but lack executable Git
identity, runtime identity, temperature, prompt version and provider request IDs. Event
records retain parsed outcomes/reasons and short prompt hashes, not complete exact prompts,
raw responses or attempt records. Seeds reproduce synthetic case and seating identities;
they do not establish inference determinism or a pinned backend. No historical signing
keys were retained. The corrected gated-majority control reconstructs synthetic receipts
with fresh keys, validates the archived scenario recipe and vote totals, and executes the kernel; it cannot re-authenticate
original receipts. Later provenance records cannot repair those historical omissions.

The historical `review-data.md` and AI review files are preserved verbatim. Their pooled
binomial intervals are unsuitable for the paired seating design, their gpt-oss
honest-auditor token count of 746 should be 745 answered responses, and their colluder-auditor
median of 329 should be 327.5. DeepSeek audit medians also change from 111/241 to
110.5/240.5. The main safety denominator of 746 remains correct. Current
tables omit the invalid pooled intervals; the correction record identifies replacement
artifacts and retains the original hashes.

---

## LLM Usage Statement

We used Claude Code (Anthropic, Claude Opus 5.5) extensively, for:
- auditing the existing repository;
- implementing the institution kernel, the bounded checker and the swarm harness;
- running and analysing the experiments;
- generating the figures;
- drafting this report.

The authors set the research questions and the key methodological decisions, including:
- the pivot to verifying institutions rather than agents;
- comparing two reasoning models rather than a reasoning and a non-reasoning model;
- treating output caps as non-binding instruments, with the pre-declared re-run rule.

The 2026-11-09 correction used Codex for offline audit follow-up, the median regression,
report corrections and artifact regeneration. It made no new live-model experiment calls.
Historical AI review records remain unchanged: round 1 ended with three weak rejects and
one reject; round 2 with four weak accepts. Those are model-generated reviews, not human
peer acceptance. Their manifests do not bind manuscript or data hashes, and the AI data
auditor received aggregate text rather than the raw archive. They therefore do not certify
this exact corrected revision. The authors remain responsible for all claims.
