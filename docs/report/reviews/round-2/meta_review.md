## Rubric scores

Scores are **Impact / Execution / Presentation**. Final scores and verdicts use the **last debate round**, not intermediate updates.

| Reviewer | Initial scores | Final scores | Initial → final verdict |
|---|---:|---:|---|
| A | 3 / 3 / 4 | 3 / 3 / 4 | Weak accept → Weak accept |
| B | 4 / 4 / 5 | 4 / 4 / 4 | Accept → Weak accept |
| C | 4 / 4 / 4 | 4 / 3 / 4 | Accept → Weak accept |
| D | 4 / 4 / 4 | 4 / 3 / 4 | Accept → Weak accept |
| **Chair** | — | **4 / 3 / 4** | **Weak accept** |

**Chair’s calibration:** Significant potential in the integrated verification-and-evaluation workflow, without established first-of-kind novelty; competent hackathon execution, but central probability and generalization claims need correction; the evidence is sufficiently traceable to audit.

## Overall assessment

**Recommendation: weak accept as a promising hackathon mechanism demonstration.**

The strongest supported contribution is the combination of implementation-level bounded checking, mutation testing, a mechanically gated majority control, and logged LLM stress tests. The audit corroborates the primary experimental counts. These are substantial accomplishments for three days.

The evidence does **not** establish robust semantic oversight, equivalent safety between committees and gated majority, arbitrary-scale implementation assurance, or general collusion detection. In particular:

- Table 1 shows **16/120 and 17/120 unsafe target releases for 4-of-7**, versus **0/120 for gated majority**.
- Essentially absent honest unsafe error leaves G3’s honest-error model empirically unvalidated.
- The hybrid’s **21.8** prediction is a committee-only opportunity estimate, not a hybrid release expectation.

These problems mostly admit inexpensive corrections to claims and interpretation. Stronger semantic evaluation and broader verification are future work, not prerequisites for recognizing the hackathon contribution.

**Verdict distribution:** initially **3 accept, 1 weak accept**; finally **4 weak accept**. No reviewer recommends rejection.

This consolidation relies on the supplied reviews, debate, and audit; it is not an independent code rerun or source verification.

## Resolved vs still-contested disagreements

### Resolved

- **Committee equivalence:** All four reviewers ultimately agree that §6’s “matched a gated majority’s judgement” wording exceeds Table 1. The supported finding is a request-count–capture trade-off.
- **Hybrid prediction:** All four agree that Table 1’s hybrid G3 entry is mislabeled.
- **Verification scope:** All four agree that the one-case checked world cannot exercise cross-case isolation and excludes the live seven-seat configurations.
- **Existing controls and disclosures:** Gated majority is already present; Figure 1 already discloses 12 independent committee draws per point; Finding 2 already reconciles 24/36 pooled opportunities with 12/18 capturable draws.
- **Herding:** D withdrew the allegation of a strong absence claim. The manuscript already calls the result weak and task-specific.
- **References:** Source verification is warranted, but the supplied material does not establish fabricated citations.
- **Near-miss inconsistency:** All four agree that “too rare to affect any committee” conflicts with the reported **2/108 honest-error captures for DeepSeek 1-of-1**.

### Still contested or requiring clarification

- **Statistical severity:** A treats the remaining uncertainty issue as minor; B, C, and D rate it major. I calibrate it as **moderate**, because pairing is disclosed and these are exploratory results, but cross-regime precision remains inadequately quantified.
- **Seating versus behavior:** Seating variation explains variation in realized seat bounds, but observed capture differences also involve colluder compliance. They should not all be declared pure seating artifacts.
- **Standalone committee cost:** Auditor board exposure, audit timing, and dependence on the reviewer stage remain unspecified in the supplied evidence.
- **Novelty strength:** A scores Impact 3; the other reviewers score 4. The integration is promising, but the claimed literature gap remains provisional pending verification.

## Ranked concerns

Consensus counts **distinct reviewers**, not debate votes, and refers to the retained concern—not every original supporting argument. Validity below assesses the corrected concern; factually wrong versions are excluded and identified later.

**Major** affects a central inference or assurance claim; **moderate** materially limits interpretation; **minor** is a localized qualification or accounting correction.

| # | Concern | Consensus | Validity | Severity | Recommended action | Effort |
|---:|---|---|---|---|---|---|
| **1** | **Headline conclusions exceed the behavioral evidence.** §§3.4, 4.2–4.3, 6 and Table 1 demonstrate an exact-match task with essentially no honest unsafe attestations, not equivalent committee judgment or validated semantic oversight. Plain-majority forgery failure is also architectural because voters lack HMAC verification. | **4/4** | **Valid** | **Major** | Replace the abstract/conclusion’s headline interpretation with an evidence-calibrated paragraph: committees traded fewer requests for observed capture risk; gated majority was safer here; G3 remains untested; the forgery comparison concerns access to mechanical verification. | 30–60 min |
| **2** | **Hybrid expected capture is mislabeled.** §3.3 G3 predicts committee approval; Table 1 assigns its **21.8** value to hybrid release, which requires additional gates. | **4/4** | **Valid** | **Major** | Relabel 21.8 as **“committee-only opportunity estimate—not hybrid release prediction.”** State the majority threshold/tie rule in the accompanying note. | 15–30 min |
| **3** | **The checked world cannot validate cross-case isolation or the live committee configurations.** §3.2 and Appendix B.1 cover one case, three seats, quorum two, depth six—not 24 cases and seven seats. This is a coverage limitation, not evidence of an actual bug. | **4/4** | **Valid** | **Major** | Report a targeted two-case isolation test, using existing tests if available, with a deliberately missing-case-filter mutant to establish sensitivity. Explicitly retain the distinction between this test and exhaustive verification. | 1–3 h |
| **4** | **Uncertainty and seed dependence remain insufficiently characterized.** Tables 1–2 and Figure 1 use only 12 seating draws per share, paired across board conditions/models/regimes; independence across shares needs clarification. | **4/4** | **Valid**, after removing the incorrect caption allegation | **Moderate** | Add a seed-indexed, draw-level uncertainty analysis preserving all paired outcomes and stratifying by share. Distinguish seating variation from response variation. | 2–3 h |
| **5** | **Standalone request savings and deployment cost are not yet established.** §3.4 does not specify auditor board exposure or timing; seven versus fifty requests does not imply proportional token, dollar, or latency savings. | **4/4** | **Valid**, without B’s original Table 2 inference | **Moderate** | Add an execution-dependency statement specifying auditor inputs/timing and whether reviewer calls can be omitted; describe the saving only as nominal model-request reduction unless actual deployment costs are calculated. | 30–60 min |
| **6** | **G1–G3 assumptions and deployment scope blur in summaries.** §§1, 5–6 extend assurance beyond bounded checking; honest-error independence belongs to G3, not mechanical G1 or zero-error G2. Database release uniqueness does not establish at-most-once external effects. | **4/4** | **Valid** | **Moderate** | Add one G1–G3 assumption-and-scope box, referenced beside the abstract’s state count, distinguishing bounded implementation evidence, conditional seat bounds, behavioral predictions, and untested external/concurrent semantics. | 30–60 min |
| **7** | **Near-miss prose and error denominators are inconsistent.** §4.3 reports 2/108 honest-error captures for DeepSeek 1-of-1 despite “any committee” wording; Appendix A also generalizes zero-cell error rates beyond their evaluated subset. | **4/4** for prose contradiction; Appendix extension is audit-only | **Valid** | **Minor** | Replace the near-miss summary with a configuration- and colluder-share-specific statement consistent with the tables, including which configurations support the mixed-model null. | 30–60 min |
| **8** | **Novelty positioning depends on incompletely verified sources.** §2’s gap and descriptions of prior systems rely on an acknowledged incomplete scan and inaccessible candidates. | **4/4** | **Valid** as a verification request, not a fabrication finding | **Minor** | Source-check the identifiers and substantive comparisons supporting the novelty claim; make any unresolved comparison explicitly provisional. | 1–3 h |
| **9** | **Output length is an observational, prompt-confounded association.** Abstract, §4.3 and Figure 2 do not establish a cost of deception or a validated monitoring signal. | **4/4** | **Valid** | **Minor** | Replace the monitoring interpretation with a clearly noncausal target/non-target × colluder/honest comparison from existing logs, described as only a partial prompt control. | 1–2 h |
| **10** | **Detector operating limits and false positives need quantification.** §4.3 and Appendix B.4 require shared losing-side evidence, which can disappear when colluders win; the zero-collusion false-positive denominator is unspecified. | **4/4** | **Valid** | **Minor** | Add an operating-characteristics table reporting false-positive runs/total zero-collusion runs by model and condition, with the losing-side requirement stated in its caption. | 1–2 h |
| **11** | **Pilot abstentions are mislabeled as truncations.** §§3.4 and 4.3 say 98/99 cut-offs were colluders; the audit distinguishes abstentions from cap hits. | **0/4; audit-only** | **Valid** | **Minor** | Replace the sentence with: **99 abstentions, 98 by colluders; 95 abstentions hit the cap.** | 10 min |
| **12** | **The regime count is inconsistent.** Abstract and §1 say seven including gated majority, while §3.4/Table 1 contain eight. | **0/4; audit-only** | **Valid** | **Minor** | State **eight reported regimes**, including the added gated-majority baseline. | 10 min |
| **13** | **Scheduled and completed call counts are conflated.** §3.4 reports 16,416 per sweep; §4.2 reports 16,415 completed plus one transport error. | **0/4; audit-only** | **Valid** | **Minor** | Consistently label **16,416 scheduled / 16,415 completed per sweep**, with one transport failure. | 10 min |
| **14** | **Two historical pilot statistics are not verifiable from the supplied summary blocks.** Appendix A’s Qwen estimate and Appendix B.3’s rerun comparison have different provenance limitations. | **0/4; audit-only** | **Partially valid:** verification is incomplete, not a demonstrated numerical error | **Minor** | Add a provenance note distinguishing the unretained Qwen estimate from the retained-run comparison, and avoid using either as independently audited validation. | 15–30 min |

For concern 2, the relevant quantity is
\[
P(\text{hybrid release})=P(\text{majority approval}\cap\text{committee approval}\cap\text{other gates}).
\]
Under a **zero-honest-error, strict-majority model** with colluders occupying at most half the electorate, this probability is zero. That is a conditional model result—not something proved by observing zero honest errors.

A challenging judgment task with measurable honest errors, broader bounded verification, concurrent/external-action tests, and adaptive detector attacks are **future work**. They are not realistically necessary additions within the remaining hours.

## Data-audit issues

The audit checked **70 claims** and reports that the primary tables, verification counts, compliance rates, herding counts, token ratios, detector F1 values, and seating-variance calculation match the supplied raw data.

| Audit issue | Correct interpretation |
|---|---|
| **Abstention versus truncation** — §§3.4, 4.3 | There were **99 abstentions**, **98 by colluders**, and **95 cap hits**. The supplied figures do not establish “98 of 99 truncated responses.” |
| **Near-miss error scope** — Appendix A | The **0.3% DeepSeek / 0% gpt-oss** figures describe the **0%-collusion cell**. At 30% collusion, each model had **one honest unsafe auditor error across 508 honest seats**, approximately 0.2%. Thus gpt-oss’s unsafe honest error was not globally zero. |
| **Regime count** — Abstract, §1, §3.4, Table 1 | Seven original regimes plus gated majority yield **eight reported regimes**. |
| **Call accounting** — §§3.4, 4.2 | Across both sweeps: **32,832 scheduled calls**, **32,830 completed**, and **two transport failures**. The headline completed total is supported. |
| **Historical provenance** — Appendices A, B.3 | The Qwen ~39% estimate lacks retained pilot logs. The DeepSeek 13/14 comparison references a retained run path but lacks printed comparison counts in the supplied summaries. Neither is shown false. |

The audit also corroborates approximately **$2.18 total API cost**. That does **not** establish a sevenfold deployment-cost reduction between governance regimes.

These are localized corrections; the audit supplies no basis for alleging that the primary experimental results are fabricated or numerically unreliable.

## Points reviewers got wrong

| Original allegation or proposed inference | Chair’s resolution |
|---|---|
| **C.C5:** Figure 1 silently overstates independent sample size. | **Invalid as stated.** A marked this `factually_wrong`; the caption already says “n = 24 … 12 independent committee draws.” C conceded. Missing uncertainty remains valid. |
| **B.C4:** Table 2’s 12/13 represents two gpt-oss board-condition results. | **Invalid.** C marked this `factually_wrong`; it is the **DeepSeek/gpt-oss split**. B conceded. Auditor information-set uncertainty remains valid. |
| **D.C4:** A crowd-plus-verification baseline is missing. | **Invalid.** A marked this `factually_wrong`; Table 1 already contains gated majority. A public-key/tool-assisted voter experiment would broaden applicability, not repair an absent control. |
| **D.C2:** The 24/36 figures cannot be reconciled with 120 trials. | **Invalid as a numerical inconsistency.** Finding 2 explains 12/18 capturable draws doubled across paired board conditions. D conceded; an explicit formula is optional clarification. |
| **D.C5:** The specification and mutants need releasing. | Their absence is **not established**: the debate identifies the existing Code and Data release. Ask about accessibility or completeness rather than assuming non-release. |
| **D.C7–C8:** General detector success or a strong herding-absence claim is asserted. | Those broad allegations are **unsupported by the supplied text**: planted-signature scope and weak, task-specific herding evidence are already acknowledged. D withdrew C8. Detector false-positive accounting remains a valid request. |
| **B.C6:** Suspect identifiers are hallucinated placeholders. | **Not established.** An editorial verification note is not evidence of fabrication. Verify the sources and substantive comparisons. |
| **B/C:** Empirical committee-size ordering violates theoretical monotonicity. | **Overstated.** Finite samples can reverse expected rankings; at exactly 50% collusion, the listed odd-sized majority committees have equal one-half capture probability under zero error/full compliance. Observed captures also depend on compliance. |
| Resampling all fifty reviewer votes supplies counterfactual auditor decisions. | **Unjustified without coverage and exchangeability assumptions.** Reviewer votes and auditor attestations are distinct calls. B conceded this limitation. |
| Non-target length comparisons isolate deception, or shared membership alone proves vote/attestation dependence. | **Neither follows automatically.** The length comparison is a partial control; a nonzero-error hybrid prediction needs an explicit joint response model. |

## Bottom line

**Keep the promising result; narrow the assurance claim.** This is a credible hackathon integration of bounded implementation checking and empirical swarm stress testing, with primary results corroborated by the audit.

The highest-value immediate changes are to **correct the committee-equivalence conclusion, relabel the hybrid prediction, and make verification/behavioral scope explicit**. A small cross-case test and paired uncertainty analysis would then strengthen execution most efficiently. The report warrants **weak acceptance**, not a claim that robust semantic swarm oversight has been demonstrated.