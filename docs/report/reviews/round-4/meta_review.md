# Rubric scores

**Conventions:** All page references below use **PDF image numbers**, including the title page. The debate is empty and no final reviewer scores were supplied; **NR** means “not reported,” not “unchanged.” Consensus counts reflect the independent reviews, not a subsequent agreement process. Validity assessments are my adjudications: there are no supplied debate `factually_wrong` judgments.

### Reviewers’ initial / final scores

| Reviewer | Impact & innovation | Execution | Presentation & clarity | Formality & visuals | Readability | Reported verdict |
|---|---:|---:|---:|---:|---:|---|
| A | 3 / NR | 3 / NR | 4 / NR | 4 / NR | 4 / NR | Weak accept |
| B | 4 / NR | 4 / NR | 4 / NR | 4 / NR | 5 / NR | Accept |
| C | 4 / NR | 4 / NR | 4 / NR | 4 / NR | 4 / NR | Accept |
| D | 4 / NR | 4 / NR | 4 / NR | 4 / NR | 4 / NR | Accept |

### Chair’s calibrated scores

| Dimension | Score | Justification |
|---|---:|---|
| **Impact potential & innovation** | **3/5** | A useful, buildable integration, but the mechanisms are acknowledged precedents and the distinct contribution needs a sharper comparison; diversity itself is not isolated (§2, p. 3; §4.3, Table 1, p. 7). |
| **Execution quality** | **3/5** | Impressive scope for three days, including implementation-level bounded testing and mutations, but a central reporting contradiction, confounded interpretation, and incomplete historical provenance prevent “convincing validation” (§§3.2–4.3, pp. 4–8; Appendix D.1, p. 16). |
| **Presentation & clarity** | **4/5** | The architecture, experimental progression, and limitations are easy to locate; protocol distinctions and some central evidence require appendix consultation (Figure 1, p. 4; §§3–5, pp. 4–8; Appendix C, pp. 13–15). |
| **Formality & visual presentation** | **4/5** | Professional typography, restrained figures, and clean tables, with minor float, heading-placement, abbreviation, and figure-size issues (pp. 4–5, 8, 13–16). |
| **Readability** | **4/5** | Mostly direct and fluent; the principal obstacles are misleading simplifications and overloaded statistical terminology, rather than convoluted prose (§3.5, p. 6; §4.3, p. 7; §5, p. 8). |

# Overall assessment

**Verdict distribution:** **3 accept, 1 weak accept, 0 reject.** No post-debate verdicts were supplied.

**Chair recommendation: weak accept, with targeted reporting corrections.** This is a worthwhile three-day prototype, not yet a demonstration that model diversity causes safer committees or that the kernel provides deployment-level verification.

Its strongest contributions are:

- **A clear enforcement boundary:** the kernel checks authorization mechanics, while auditors supply semantic judgments (Figure 1 and §3.1, p. 4).
- **Testing the implementation, with useful negative controls:** 23,376 bounded states, seven detected mutations, and an explicitly reported depth-five miss (§4.1, p. 6; Table 3, p. 12).
- **An informative experimental progression:** the authors recognize that mechanical field matching barely tests honest judgment and introduce a harder task (§§3.4–3.5, pp. 5–6).
- **Candid qualification:** synthetic cases, planted collusion, trusted infrastructure, missing records, and AI assistance are disclosed (§5, p. 8; Appendices A and D–E, pp. 10–11, 16–18).

These strengths deserve hackathon credit. Nevertheless, transparent appendices do not cure contradictory results prose or unsupported headline conclusions (§4.3, p. 7; Table 2 and §6, p. 8).

# Substance concerns

This is the **single consolidated priority list**, including presentation and compliance concerns so that authors have one ordering. Subsequent sections explain the form and readability items rather than introducing duplicate priorities.

| # | Concern and location | Consensus | Validity | Severity | Single most effective action | Effort |
|---:|---|---|---|---|---|---|
| **1** | **Unanimity is incorrectly described as safe.** “Unanimity kept gpt-oss safe” contradicts **5 unsafe releases** in Table 2; zero belongs to “Flipped” (§4.3, p. 7; Table 2, p. 8). | **A: 1/4** | **Valid** | **Major** | Replace the sentence with the actual unsafe and valid-release counts, distinguishing safety from overturning the reference decision. | 15–30 min |
| **2** | **Diversity is confounded with reviewer quality; the headline generalizes too far.** DeepSeek alone is substantially stronger, and its homogeneous committee already rounds to 0.0% harmful approval. Mixed committees therefore do not establish a diversity-specific benefit (abstract, p. 1; Table 1 and §4.3, p. 7; §6, p. 8). | **All 4** on scope/interpretation; **A, B: 2/4** explicitly identify the quality confound | **Valid** | **Major** | Recast the result as replacing weaker reviewers with stronger reviewers; give the exact tested seat composition and homogeneous baselines in the same comparison. | 1–2 h |
| **3** | **Guarantee assumptions are inconsistent.** Independence is neither sufficient for the stated Condorcet claim nor necessary for safety. G2 does not require independent errors; predictable seating affects the sampling probability, not the realized-seat implication (§2, p. 3; §§3.3–3.5, pp. 4–6; §5, p. 8; Appendix A.1, p. 10). | **A: 1/4** | **Valid** | **Major** | Add an assumption table for G1–G3 and align the surrounding claims with it, including the competence condition for Condorcet improvement. | ~1 h |
| **4** | **The estimand and uncertainty do not support a precise dependence or “22×” interpretation.** Case heterogeneity alone can produce a gap from a pooled-iid baseline; the committee interval is wide, and the mixed estimate and correlation are underspecified (§3.5, p. 6; §4.3 and Table 1, p. 7). | **All 4**, addressing different aspects | **Valid** | **Major for interpretation** | Add a short statistical-methods block defining finite-pool committee enumeration, the pooled-iid comparator, case-bootstrap uncertainty, and the correlation statistic; remove the multiplier from the abstract. | 1–3 h |
| **5** | **“Flipped” lacks a reproducible reference definition and is overinterpreted causally.** The 100/98 denominators exceed the 96 harmful instances, and “honest agents on their own” could mean several different computations (§4.3, p. 7; Table 2, p. 8). | **A, B: 2/4** | **Valid** | **Major** | Specify the reference algorithm, included case types, abstention treatment, and exposure to board comments in the Table 2 caption; describe the result as a reference-decision comparison unless causal identification is justified. | 30–60 min |
| **6** | **Synthetic labels and outcome-informed adjudication limit validity.** One model family generated all cases and labels; disagreements were subsequently examined, and the contested case is excluded from Table 1 but apparently retained in Table 2 (§3.5, p. 5; §4.3, p. 7; Appendix E.1, p. 17). | **A, C, D: 3/4** | **Valid** | **Moderate** | Add a human/executable adjudication sheet for the seven error-bearing harmful cases and contested case, including safe-rate sensitivity with and without the exclusion. | 2–3 h; independent holdout is future work |
| **7** | **Offline analysis reproducibility is stronger than historical experiment reproducibility.** Prompts, raw responses, source revision, decoding settings, and original signed evidence are unavailable; gated majority was reconstructed with fresh artifacts (Appendix D.1, p. 16). | **A, C, D: 3/4** | **Valid** | **Moderate** | Put a prominent “offline tables reproducible; historical live runs not exactly rerunnable” qualification in Code and Data, and label gated majority an offline replay control. | ~30 min |
| **8** | **Sampling and abstention rules are insufficiently consolidated.** The methods describe 12 reviewers, while Table 1 uses 50 votes for the low-cost models; committee vote sources and non-response handling need specification (§3.5, p. 5; Table 1, p. 7; Table 11, p. 17). | **A, B: 2/4** | **Valid** | **Moderate** | Add one protocol matrix listing each phase/model’s review pool, auditor pool, board condition, repetitions, token cap, and abstention rule. | 1–2 h |
| **9** | **Page-limit compliance depends on treatment of non-reference back matter.** The title plus text through the conclusion occupies eight physical pages, while Code and Data and Author Contributions are not labeled appendices (pp. 1–10). | **C: 1/4** raises accounting ambiguity; chair identifies conservative-count risk | **Partially valid:** ambiguity, not an established breach | **Potentially major** | Move Code and Data and Author Contributions into a clearly labeled appendix, then recount under the organizer’s title-page convention. | 30–60 min |
| **10** | **“Verified code” and gateway claims exceed bounded evidence.** The checker covers one case, three seats, and six actions, not general concurrency or complete deployment mediation (abstract, p. 1; §1, p. 2; §3.2, p. 4; Appendix A.1, pp. 10–11). | **A, C, D: 3/4** | **Valid** | **Moderate** | Use “bounded-tested kernel” consistently and explicitly condition deployment claims on complete mediation and a protected host/key boundary. | ~30 min |
| **11** | **The attack coverage is narrow.** Frontier models were not attacked; colluders were instructed, non-adaptive, and did not compromise seating, keys, or the host (§5, p. 8; Appendix A.1, pp. 10–11). | **B, C, D: 3/4** | **Partially valid:** real limitation, already disclosed in the main text | **Moderate for scope** | Qualify “no honest mistakes to exploit” as a statement about recorded honest reviews, not evidence of resistance to adaptive persuasion. | 15 min; stronger attacks are future work |
| **12** | **Novelty is plausible but not established precisely.** The broad “no prior work” combination claim needs a closer comparison with already cited verification-gate and runtime-governance systems (§2, p. 3). | **A: 1/4** explicit concern; all four acknowledge reused mechanisms | **Partially valid:** insufficient positioning does not establish absence of novelty | **Moderate** | Add a compact, source-verified comparison identifying reused mechanisms and the new implementation/evaluation contribution. | 1–2 h |
| **13** | **Experiment 1 is less self-contained than Experiment 2.** Its main table and plot are in the appendix, and appendix tables are first cited before Tables 1–2 (§4.2, p. 6; Figure 2 and Table 5, pp. 13–14). | **B, C: 2/4** | **Valid as navigation criticism**, not a numbering-rule violation | **Minor** | Replace some results prose with a compact Experiment 1 summary table, subject to a fresh page count. | ~1 h |
| **14** | **Figure 2 compresses the central seat-bound evidence.** Four narrow panels crowd low-rate markers and omit draw-level uncertainty (p. 13). | **A, C, D: 3/4** | **Valid** | **Minor** | Redraw as a larger 2×2 panel layout with an explicit 50% tick and uncertainty or a conspicuous uncertainty note. | ~1 h |
| **15** | **“GPT” ambiguously labels gpt-oss; dense headers impede scanning.** This is especially problematic because a different GPT model appears in Table 1 (Tables 1–2, pp. 7–8; Table 5, p. 14). | **D: 1/4** | **Valid** | **Minor** | Replace “GPT” with “gpt-oss” throughout the tables and captions. | 15 min |
| **16** | **Avoidable page breaks interrupt logical units.** Contributions, G3’s lead-in/equation, and the discussion paragraph are split; Appendix D’s heading has no following content on its page (pp. 2–5, 7–8, 15–16). | **A, B: 2/4** | **Valid** | **Minor** | Apply heading/equation keep-with-next controls and adjust the Table 2 float. | 30–60 min |
| **17** | **Reference/back-matter consistency warrants a final check, but some reviewer objections are overstated.** The bibliography contains titles; abbreviated author lists are not inherently improper (pp. 8–11, 18). | **C, D: 2/4** | **Partially valid** | **Minor** | Run one bibliography and heading-style consistency pass, verifying cited identifiers without assuming they are fabricated. | 1–2 h |
| **18** | **Submission-version timing needs clarification, not a late-submission allegation.** Runs and a November 9 reporting correction are described, but the submitted PDF’s timestamp is not shown (p. 10; LLM Usage Statement, p. 18). | **D: 1/4** | **Partially valid:** date alone proves no breach | **Low / clarification** | State the submitted artifact’s timestamp and distinguish it from the later reporting-only correction. | 15 min |

# Formality and visual presentation

**Overall: polished, with minor defects—not unprofessional.**

- **Headings and capitalization:** The major-section, subsection, and run-in-heading hierarchy is readily distinguishable. Title case for major headings and sentence case for subsections is a defensible convention, not itself an inconsistency. The isolated Appendix D heading should be kept with its opening content (pp. 3–6, 15–16). An unlettered LLM Usage Statement is acceptable if permitted by the template; consistency would improve if it were explicitly placed within the appendix scheme (p. 18).

- **Register:** Plain phrases such as “What we found” are appropriate for this hackathon report. The problem is not informality but categorical wording—particularly “safe,” “verified,” and “fixed this”—where the evidence is conditional or bounded (§1, p. 2; §§4.3–6, pp. 7–8).

- **Citations and references:** Author–year citations are visually consistent and easy to locate. The references do include titles, contrary to Reviewer C’s suggestion. Mixed journal, conference, web, and arXiv formats are not automatically inconsistent; verify metadata and apply one bibliography style, rather than imposing unsupported requirements for full author lists or DOIs (pp. 8–9).

- **Figures:** Figure 1 effectively communicates the enforcement boundary and has a useful explanatory caption (p. 4). Figure 2 needs larger panels and clearer low-rate markers; importantly, the caption should continue to distinguish paired outcomes from independent committee draws (p. 13). Figure 3 is readable and appropriately warns that output length is an association, not a measured cost of deception (p. 15).

- **Tables:** The booktabs-style rules and lack of vertical clutter work well. Table 1 should label enumerated committee probabilities as estimates from recorded reviews rather than simply “Observed”; Table 2 needs a reproducible “Flipped” definition and unambiguous model names; Table 5’s multi-line headers need simplification (pp. 7–8, 14).

- **Typography, whitespace, and layout:** Body text and captions are generally legible, with restrained color and adequate margins. The most visible defects are the split G3 equation, isolated Appendix D heading, and “hidden- board” spacing artifact (pp. 4–5, 12, 15). The title page’s “With Apart Research” block is unconventional but not a substantive professionalism problem (p. 1).

**Exact official-template fidelity cannot be established:** the template/guidelines file itself was not supplied in the review record.

# Readability

The most useful edits improve precision without making the paper more technical.

| Location | Current wording | Recommended rewrite |
|---|---|---|
| §3.5, p. 6 | “A random committee is safe only if honest reviewers make independent mistakes” | **“Committee gains predicted by a pooled independent-error model can disappear when reviewers tend to miss the same cases.”** |
| §4.3, p. 7; Table 2, p. 8 | “Unanimity kept gpt-oss safe but blocked 46 of 64 valid changes.” | **“For gpt-oss, unanimity released 5 of 96 harmful changes and blocked 46 of 64 valid changes. It overturned no honest-reference rejections under the reported ‘Flipped’ measure.”** |
| §5, p. 8 | “G2 and G3 assume reliable, independent honest reviewers…” | **“G2 assumes that honest auditors never approve harmful releases. G3 instead permits honest errors and models them as independent events at a common rate.”** |
| §6, p. 8 | “adding a different model fixed this” | **“Replacing some gpt-oss reviewers with the more accurate DeepSeek model reduced estimated harmful approvals on these cases; this comparison does not isolate a diversity benefit.”** |
| Abstract, p. 1 | “Its rules held in all 23,376 reachable states of a small test world” | **“Its rules held in all 23,376 states explored within six actions in a small test world.”** |
| §4.3, p. 7 | “That leaves colluders no honest mistakes to exploit.” | **“These recorded honest reviews contained no harmful approvals by the frontier models; we did not test those models under collusion.”** |

Two further changes would ease one-pass reading:

1. Introduce one short vocabulary box distinguishing **unsafe release, committee capture, and reference-decision flip** before the results. These are currently too easy to conflate (§§3.3–4.3, pp. 4–8).
2. Replace the prose-heavy phase description with the protocol matrix requested in concern #8. This would resolve the 12-versus-50 review-pool ambiguity without adding substantial prose (§3.5, p. 5; Table 1, p. 7).

Do **not** insert an exact mixed composition, correlation metric, case universe, or coefficient unless confirmed by the analysis. Several reviewer-proposed rewrites supplied those details without evidence.

# Requirements compliance

| Requirement | Assessment |
|---|---|
| **Eight pages excluding references and appendices** | **Conditional / clarification needed.** The title page plus pages through the conclusion occupies PDF pp. 1–8, with references beginning on p. 8. However, Code and Data and Author Contributions occupy additional non-reference material on pp. 9–10 and are not labeled appendices. Moving them into an appendix is safer than declaring them exempt. |
| **150–250-word abstract** | **Pass.** Approximately **235 words** under a whitespace-based count (p. 1). |
| **Required Limitations and Dual-Use / Ethical appendix** | **Pass.** Appendix A substantively covers limitations, dual use, and provenance (pp. 10–11). |
| **Authors and affiliations** | **Pass.** Two named authors and affiliations are visible (p. 1). |
| **Official template structure** | **Not fully assessable.** The visible organization is professional, but the actual template was not supplied (pp. 1–18). |
| **Sprint/deadline eligibility** | **No demonstrated breach.** Reported Experiment 2 calls occurred before the stated AoE deadline; the correction is described as reporting-only, with no new calls. The submitted-version timestamp remains a clarification request (p. 10; p. 18). |

There is **not** a securely established extra page available for moving appendix figures into the main text. That depends on the organizer’s title-page treatment and the back-matter accounting.

# Data-audit issues

The supplied audit contains only `{"unparsed": ""}`. It provides **no substantive audit findings** and must not be treated as confirmation that the artifacts or statistics were independently checked.

The following are document-level checks, not a source-code or raw-data audit:

| Check | Finding |
|---|---|
| **Safety versus “Flipped”** | Confirmed reporting contradiction: gpt-oss unanimity has **5 unsafe**, **0 flipped**, and **18 valid** releases in Table 2. Thus 46 valid changes were blocked, but the rule was not safe (§4.3, p. 7; Table 2, p. 8). |
| **32,830 versus 32,832 records** | Not inherently inconsistent: Table 10 reports **32,830 completed plus 2 error records**, explaining the 32,832-record denominator in Appendix D.2 (p. 16). |
| **Experiment 2 call totals** | Internally plausible: \(48(12+7)=912\) calls per frontier model, and \(48(50+7)\times6=16{,}416\) per population model. The remaining question is which vote pool feeds Table 1 (§3.5, p. 5; Tables 1 and 11, pp. 7, 17). |
| **“22×” versus displayed 12.0% / 0.5%** | Not necessarily an arithmetic error. The binomial 4-of-7 tail at error rate 0.12 is about **0.537%**, giving approximately **22.4×**. Rounding explains the apparent 24× ratio; uncertainty remains the substantive issue (§4.3 and Table 1, p. 7). |
| **Table 2 denominators** | The 96 harmful and 64 valid instances correspond to four conditions. The 100/98 reference-rejection denominators require an explicit case universe and algorithm; their exact construction cannot be inferred reliably from the caption (p. 8). |
| **Abstentions and utility loss** | Table 11 establishes 230 DeepSeek token-cap abstentions, almost all on safe/forged cases. It does **not** establish how many of the 13 blocked valid releases under unanimity were caused by those abstentions (Tables 2 and 11, pp. 8, 17). |
| **Offline replay** | Fresh receipts and keys test rule behavior on retained decisions, not the authenticity or parsing of historical signed artifacts. That distinction is correctly disclosed but should be prominent (Appendix D.1, p. 16). |

# Points reviewers got wrong

1. **Reviewer B overstates the diversity result and its explanation.** A majority of near-perfect DeepSeek seats does not *guarantee* safety: sufficiently many mistaken DeepSeek votes can still combine with gpt-oss votes to cross the threshold. It does prevent the minority from approving alone. Also, with two model families and seven seats, “neither model holds a majority” is impossible. The correct criticism is confounding, not guaranteed safety (§4.3 and Table 1, p. 7).

2. **Reviewer B’s proposed numerical rewrite invents specificity.** The paper does not establish exactly four DeepSeek plus three gpt-oss seats, Pearson correlation over 47 cases, or Gemini correlations below 0.10. These require verification, not insertion (§4.3, p. 7).

3. **Reviewer B attributes DeepSeek’s utility loss too confidently to truncation.** The aggregate abstention count makes that explanation plausible but does not identify the release-level cause. The proposed mechanism for board benefits—specific bug reports defeating generic talking points—is also an interpretation rather than a demonstrated mediation analysis (Table 2, p. 8; Appendix E.2–E.3, pp. 17–18).

4. **Reviewers C and D propose misleading “Flipped” rewrites.** C calls the reference universe “harmful cases” despite its 98 denominator exceeding 96 harmful instances. Both C and D use causal language stronger than the undefined reference supports; honest votes may themselves reflect board exposure (§4.3, p. 7; Table 2, p. 8).

5. **Reviewer D’s “adding one different model” rewrite is unsupported.** The reported mixed committees have at least half their seats assigned to DeepSeek, not one replacement seat (§4.3, p. 7).

6. **Reviewer C’s bibliography alarm is factually overstated.** Titles are present, and 2026 references are not future-dated relative to the paper’s November 2026 setting. Their identifiers should still be verified. Neither C nor D establishes that abbreviated author lists violate the required style (pp. 1, 8–9).

7. **The page-budget and numbering objections need qualification.** B’s claimed spare page is not assured under a title-inclusive count. C’s suggestion to label back matter “excluded” does not itself create an exemption. Citing appendix Tables 3 and 5 before main-text Tables 1 and 2 is inconvenient, but not automatically a numbering violation (§4.1–4.2, p. 6; pp. 8–10, 12–14).

8. **Some supposedly missing limitations are already prominent.** Frontier-only honest review, non-adaptive colluders, and the absence of key/seating attacks appear in the main limitations paragraph. The remaining problem is ensuring that headline claims respect those disclosures (§5, p. 8).

9. **“Pre-declared” should not be extended to every revision or exclusion.** The report describes a planned difficulty adjustment, but the contested-case treatment followed observed disagreement, and the truncation rerun rule lacks an archived timestamp. Neither should be upgraded to established preregistration (Appendix B.3, p. 12; Appendix E.1–E.2, p. 17).

# Bottom line

**A promising, professionally presented hackathon contribution that merits a weak accept—not yet a strong empirical or formal validation.**

The highest-return revision is to **correct the unanimity statement, narrow the diversity claim, define the guarantee assumptions and “Flipped” reference, and resolve page accounting**. These are achievable reporting repairs. More adaptive adversaries, independent holdout cases, and deployment-level verification are future work, not prerequisites for recognizing this prototype’s value.