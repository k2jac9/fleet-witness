# Rubric scores

**All page references below are physical PDF pages; p. 1 is the title page.** Arrows show **initial → final** scores, using the last debate round.

| Reviewer | Impact & innovation | Execution | Presentation & clarity | Formality & visual presentation | Readability | Verdict |
|---|---:|---:|---:|---:|---:|---|
| A | 3 → 3 | 3 → 3 | 3 → 3 | 4 → 4 | 4 → 4 | Borderline → Borderline |
| B | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4 | Accept → Accept |
| C | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4 | 3 → 3 | Weak accept → Weak accept |
| D | 4 → 4 | 4 → 4 | 4 → 3 | 4 → 4 | 4 → 3 | Accept → Weak accept |
| **Chair: calibrated** | **3** | **3** | **4** | **4** | **3** | **Weak accept, conditional on compliance corrections** |

### Chair’s calibration

| Dimension | Score | One-line justification |
|---|---:|---|
| Impact potential & innovation | **3/5** | Important problem and useful implementation–verification–stress-test integration, but the report does not establish a new authorization mechanism or validate judgment-dependent oversight (§§2–3, pp. 3–5; §4.3, p. 7). |
| Execution quality | **3/5** | Actual-implementation checking, seven detected mutants, and two-model experiments are substantial for three days; missing historical execution records, truncation uncertainty, and the narrow task prevent “convincing validation” of the broader claims (§4.1, p. 5; Appendices B–D, pp. 12–15). |
| Presentation & clarity | **4/5** | Contributions, G1–G3, and numbered findings make the argument easy to locate; methodological qualifications and several display inconsistencies still need correction (pp. 2, 4, 6–8). |
| Formality & visual presentation | **4/5** | Professional typography, restrained figures, and clean tables; bibliography, appendix hierarchy, float placement, and author-block defects are noticeable but repairable (pp. 1, 6–7, 9–14). |
| Readability | **3/5** | The headline is clear, but reconstructing the workflow, paired sampling design, and honest-error denominators requires repeated reading (§3.4, pp. 4–5; §4.3, p. 7; Appendices C–D, pp. 13–15). |

# Overall assessment

**This is a promising, scientifically useful hackathon report—not yet convincing evidence for general semantic oversight of agent swarms.** Its strongest contribution is the combination of bounded exploration of the actual SQLite-backed kernel, mutation testing, and an empirical harness that exposes the limits of committee authorization (§§3.2–3.3, p. 4; §4.1, p. 5; Table 2, p. 12).

The report deserves particular credit for the unfavorable result: **on this dataset, committees add no observed safety over a mechanically gated majority**, while smaller committees introduce capture opportunities. That is more informative than presenting only the forgery advantage over ungated voting (Table 1 and Finding 1, p. 6).

The principal limitation is evidential scope. Exact receipt-field inspection produces almost no honest unsafe attestations, so the experiments largely test mechanical authorization, seating opportunities, and instructed colluder compliance—not the correlated judgment failures that motivate the broader architecture (§4.3, p. 7). The authors already acknowledge this; the remaining task is to make every headline formulation consistent with that boundary (Abstract, p. 1; Conclusion, p. 8).

**Verdict distribution**

- **Initial:** 2 accept, 1 weak accept, 1 borderline.
- **Final:** 1 accept, 2 weak accept, 1 borderline; no rejects.
- **Chair:** weak accept on scientific merit, conditional on resolving the page-limit problem, completing affiliations, and clarifying submission eligibility (pp. 1, 9, 15).

# Substance concerns

This is the **single consolidated ranking**, including screening and presentation concerns. Later sections explain selected fixes without creating a second ranking.

**Consensus counts distinct reviewers, not repeated debate comments.** “Major” means a concern affects eligibility or a principal inference; “Minor” means a bounded reporting, terminology, or presentation defect. The supplied debate contains **agree/disagree stances, not explicit `factually_wrong` labels**; validity therefore follows the factual resolutions supported by the images and supplied audit.

| # | Concern | Consensus | Validity | Severity | Single most effective action | Effort |
|---:|---|---|---|---|---|---|
| **1** | **Page-limit compliance:** counted material reaches p. 9 because Code and Data and Author Contributions precede References, after the title page and seven narrative pages (pp. 1–9). | **4/4** | **Valid** under the stated counting rule; organizer exemption unconfirmed | **Major—screening** | Move the p. 9 non-reference sections into an appendix and verify that all counted material fits within eight physical pages. | 20–40 min |
| **2** | **Benchmark does not validate semantic oversight or G3’s independence assumption.** Targets are mechanically decidable receipt defects; main-task honest unsafe attestations are 0/746 per model. The receipt-versus-attestation distinction also lacks a concrete example (§§3.1–3.4, pp. 3–5; §4.3, p. 7). | **4/4** | **Valid**, but already acknowledged | **Major—scope** | Add one benchmark-scope/workflow box showing representative receipt defects, agent-visible fields, and kernel checks, explicitly labeling the task an exact-match proxy. | 1–2 h; judgment-task validation is future work |
| **3** | **Non-binding output caps are asserted more strongly than historical evidence permits.** Retry/truncation fields are absent from 30,096/32,832 main records; the documented replacement changes one 4-of-7 hidden-board capture from 1 to 0 (§3.4, p. 5; Appendices B.3, C.3, D, pp. 12–15). | **4/4** | **Valid** | **Major—confound** | Add a compact original-versus-replacement sensitivity table, stating that non-binding caps were intended but cannot be verified throughout. | 1–2 h |
| **4** | **“Complete logs” overstates reproducibility.** Historical prompts, raw responses, executable identity, prompt version, temperature, request IDs, and most attempt metadata are missing. Current temperature 0.7 does not establish historical configuration (Contribution 5, p. 2; §3.4, p. 5; Appendix D, p. 15). | **4/4** | **Valid** | **Major—reproducibility** | Replace the completeness claim with a concise reproducibility contract distinguishing retained records, reconstructable artifacts, current defaults, and unrecoverable historical information. | 45–90 min |
| **5** | **“Standalone committee” evidence pools different information conditions.** Visible-board auditors see the preceding 50-agent tally/comments; smaller-committee selection from seven seats is unspecified (§3.4, p. 5; Findings 1–2 and Table 1, p. 6). | **4/4** | **Valid** | **Major—interpretation** | Add a methods/results block specifying the actual seat-selection rule and reporting hidden- versus visible-board capture counts separately. | 1–2 h |
| **6** | **Uncertainty and realized seating are insufficiently visible.** There are 60 distinct committee draws overall and 12 per nonzero share—not 120 or 24 independent observations. Figure 1 shows G3 but not realized G2 opportunities; “matched safety” overstates a zero-failure observation (Table 1, p. 6; Figure 1, p. 7; Table 3, p. 13). | **4/4** | **Valid**; pairing is disclosed, not concealed | **Major—interpretation** | Produce a draw-aware results display with realized G2 opportunities and uncertainty preserving paired conditions/models and share strata; replace equivalence wording with observed counts. | 2–3 h |
| **7** | **The reconstructed gated-majority control needs an explicit preservation argument.** Fresh receipts and keys cannot re-authenticate original receipts (§3.4, p. 5; Appendix D, p. 15). | **4/4** for clarification | **Partially valid:** reconstruction is already disclosed; invalidity is not demonstrated | Minor | Add a reconstruction-equivalence box identifying preserved fields/votes, regenerated fields, and actual kernel checks exercised. | 1–2 h |
| **8** | **Some global claims blur G1, G2, and G3; “liveness” is overloaded.** “Every reachable state” omits the depth bound, while S2 checks success of an attempted eligible execution—not eventual progress. Independence belongs to G3, not every guarantee (pp. 1–4, 6, 8, 11). | **4/4** | **Valid** | Minor | Apply one claim-language pass naming the relevant G-claim and renaming S2 “eligible-execution success.” | 30–60 min |
| **9** | **Deadline eligibility cannot be established from the dated correction narrative.** November 9 alone does not establish lateness under a November 8 AoE deadline (Code and Data/Contributions, p. 9; LLM Usage Statement, p. 15). | **4/4** | **Valid clarification request**, not a proven breach | Minor; potentially eligibility-relevant | Supply a timezone-qualified submission/version timeline with commit/PDF hashes and the timing of the reconstructed control. | 20–40 min if records exist |
| **10** | **Table 1’s pooling caption is wrong for two outcome groups.** Valid/forged denominators include 0% collusion; target denominators exclude it (Table 1, p. 6). | **4/4 + audit** | **Valid** | Minor | State the sampling range separately for each column group. | 10–15 min |
| **11** | **Captured 3-of-5 results are omitted from both per-share displays.** This contradicts Figure 1’s “regimes that were ever captured” caption (Table 1, p. 6; Figure 1, p. 7; Table 3, p. 13). | **4/4 + audit** | **Valid** | Minor | Add 3-of-5 to Table 3 and label Figure 1 “selected committee regimes.” | 20–40 min |
| **12** | **Detector evaluation is under-tabulated.** F1 0.97–1.0 lacks per-condition counts, aggregation units, zero-positive handling, and sensitivity information (§4.3, p. 7; Appendix B.4, p. 13). | **4/4** | **Valid**; planted-signature limitation is already explicit | Minor | Add an appendix confusion-count table with TP/FP/FN and precision/recall/F1, including zero-collusion handling. | 1–2 h |
| **13** | **One affiliation is missing; Apart Research’s role is ambiguous** (author block, p. 1). | **4/4** | **Valid** | Minor—requirements | Complete Alejandro Castellanos’s affiliation and identify Apart’s actual role. | 5–10 min |
| **14** | **Bibliographic attribution/style and novelty positioning need verification.** Title-fragment attribution, yearless SQLite, mixed author truncation, and incomplete metadata undermine the related-work comparison (§2, p. 3; References, pp. 9–10). | **4/4** | **Valid** formatting concern; source correctness remains unverified | Minor | Perform one source-verified bibliography pass, including the claims made about the closest works. | 1–2 h |
| **15** | **Mutation-trace reporting is incomplete.** Four mutants lack explicit counterexample lengths despite the main-text four-to-six-action claim (§4.1, p. 5; Table 2, p. 12). | **4/4**, after correction | **Valid** | Minor | Add a counterexample-length column for every mutant, marking unrecorded values honestly. | 30–60 min if traces exist |
| **16** | **G3 table assumptions are easy to miss locally.** Table 1’s expectation uses full colluder compliance and zero honest error, whereas observed compliance is lower (G3, p. 4; Table 1/Finding 2, p. 6). | **1/4** explicitly raised this addition | **Partially valid:** assumptions are stated elsewhere | Minor | Repeat “ε = 0; full colluder compliance” beside the Expected (G3) heading/note. | 5–10 min |
| **17** | **Workflow terminology, acronyms, denominator changes, and the model-selection explanation impede one-pass reading** (§§1–3, pp. 2–5; §4.3, p. 7; Table 4, p. 14). | **4/4** | **Valid** | Minor | Add a compact definitions-and-units box, then use those labels consistently. | 45–60 min |
| **18** | **A few phrases are unnecessarily rhetorical or imprecise**, notably criticism of prior work and “unanimity buys safety with liveness” (Introduction/contributions, p. 2; Finding 3, p. 6). | **4/4** | **Valid** | Minor | Replace these phrases with neutral descriptions of evaluated properties and observed availability costs. | 15–30 min |
| **19** | **Structural typesetting defects interrupt reading:** sentence-splitting floats, crowded Table 1 headers/note, bare table-reference fragments, inconsistent appendix subhead treatment, and excessive final-reference whitespace (pp. 5–7, 10–14). | **4/4** on core defects | **Valid** | Minor | Reflow floats at paragraph boundaries and normalize back-matter headings without reducing readable type size. | 1–2 h |
| **20** | **Internal review history is more detailed than scientifically useful.** Automated verdict tallies add little to the provenance account (pp. 9, 15). | **3/4** on narrative harm; D disputes it | **Partially valid:** back-matter AI-use/provenance disclosure is appropriate | Minor | Remove review-score history while preserving AI-use disclosure and auditable version/timing facts. | 10–15 min |

# Formality and visual presentation

**Overall: professional and polished, but not publication-final.** The page images support **4/5**, not a broad finding of poor formatting.

| Aspect | Chair’s assessment |
|---|---|
| **Headings and hierarchy** | The numbered main sections and subsections are clear. The weaker area is back matter: Appendix A uses displayed subheads, while B/C use bold run-ins; B.2 and C.2 end in bare “Table 2.” / “Table 4.” references. These look unfinished rather than substantively confusing (pp. 11–13; concern #19). |
| **Capitalization and terminology** | Capitalization is broadly coherent by heading level; there is no pervasive capitalization problem. The more consequential inconsistency is conceptual: “liveness” alternates between attempted-execution success and valid-release acceptance (§3.2, p. 4; Finding 3, p. 6; concern #8). |
| **Register** | Most prose is appropriately formal. “Implements nothing, measures nothing,” “the checker has teeth,” and “two things no constitution allows” should become neutral factual statements (p. 2; concern #18). |
| **Citations and references** | Author–year citations are readable, but title-as-author attribution, SQLite’s absent date, mixed author-list conventions, and incomplete publication metadata need a verified cleanup. A title-based citation is not inherently invalid when authorship is unavailable; its use should be deliberate and consistent (pp. 2–3, 9–10; concern #14). |
| **Figures** | **Figure 1 is already nearly full text width and legible.** Its shared y-axis and below-panel legend are conventional. Distinct colors and marker shapes help distinguish models. The substantive problems are missing 3-of-5 coverage and realized G2 opportunities—not an established legibility failure (p. 7; concerns #6, #11). Figure 2 is cleanly labeled, with direct numerical annotations and an appropriately cautious caption (p. 14). |
| **Tables** | The booktabs-style tables are generally professional. Table 1’s grouped headings are crowded, and essential pairing information is buried in a dense note; move “120 paired target trials, 60 committee draws” into the caption or header. Table 2 needs explicit trace lengths, not invented entries (pp. 6, 12; concerns #6, #15, #19). |
| **Typography** | Body type, equation setting, margins, and link styling are consistent and readable. There is no reason to shrink fonts to repair the page limit; moving meta-information is the better fix (pp. 2–9; concerns #1, #19). |
| **Layout and whitespace** | Table 1 interrupts a sentence, Figure 1 separates Finding 3 from its continuation, and Figure 2/Table 4 interrupt Appendix C.3. The final reference page is mostly blank. These are reflow problems, not reasons to redesign the paper (pp. 5–7, 10, 13–14; concern #19). |

# Readability

The central lesson is understandable on one pass; the experimental mechanics are not consistently so. The most useful edits are below.

| Location | Current wording/problem | Recommended rewrite |
|---|---|---|
| **Abstract, p. 1** | “Per-agent alignment and monitoring do not scale to swarms…” | **“Per-agent safety measures may miss failures caused by coordination among agents.”** |
| **Introduction, p. 2** | “It implements nothing, measures nothing, and defers its proofs.” | **“The proposal is conceptual and does not report an implementation, empirical evaluation, or completed proofs.”** Verify this characterization against the source. |
| **§3.2, p. 4** | “We explore every reachable state of the real kernel…” | **“We explore all states reachable within the specified world, action set, and depth bound using the actual kernel implementation.”** |
| **§3.4, p. 5** | Convoluted explanation of excluding non-reasoning models | **“We compare two reasoning-mode model/backend configurations. This design does not estimate an effect of reasoning mode or separate model-family effects from backend effects.”** |
| **§3.4, p. 5** | Retries are described as establishing non-binding caps throughout | **“The intended procedure retried truncated responses at larger caps. Because attempt metadata are missing for most retained main records, we cannot verify that caps were non-binding throughout.”** |
| **Table 1 / Finding 2, p. 6** | Pairing is relegated to a note; “matched safety” implies equivalence | **“The 120 target outcomes use 60 committee draws shared across board conditions. At 10% collusion, 4-of-7 also had zero observed captures; this is not evidence of safety equivalence.”** |
| **Finding 3, p. 6** | “Unanimity buys safety with liveness…” | **“Unanimity prevented observed captures but reduced valid-release acceptance for gpt-oss.”** |
| **§4.3 and Table 4, pp. 7, 14** | Seats, case-conditions, and refusal subsets are mixed | **“Table 4 covers 108 zero-collusion near-miss case-conditions per model, comprising 756 auditor slots (108 × 7). These are distinct from the 746 honest target slots in the main experiment.”** |
| **Discussion, p. 8** | “The guarantee” combines different assumptions | **“G1 concerns mechanical authorization within the checked bounds. G2 assumes honest auditors never sign unsafe releases. G3 additionally assumes random seating, independent honest errors, and full colluder compliance.”** |

At first use, expand **Model Context Protocol (MCP), Agent2Agent (A2A), hash-based message authentication code (HMAC), and term frequency–inverse document frequency (TF-IDF)**. More importantly, illustrate **release, receipt/evidence, and auditor attestation** as different objects in one workflow (§§1–3.4, pp. 2–5).

# Requirements compliance

| Requirement | Assessment | Required response |
|---|---|---|
| **Eight pages excluding references and appendices** | **Not compliant under the literal stated rule, absent an organizer exemption.** The title page plus narrative pp. 2–8 already use eight physical pages; additional counted sections appear on p. 9. Printed numbering does not alter this (pp. 1–9). | Move Code and Data and Author Contributions into an appendix. This alone can leave the existing title page plus seven narrative pages within eight pages. |
| **150–250-word abstract** | **Pass.** Approximately **216 words** using ordinary whitespace/hyphenated-word counting (p. 1). | None. |
| **Required Limitations and Dual-Use / Ethical appendix** | **Pass.** Appendix A is substantive and addresses bounds, adversaries, trust assumptions, provenance, misuse, and ethics (pp. 11–12). | Preserve it during shortening. |
| **Authors and affiliations** | **Incomplete.** Both authors are named, but Alejandro Castellanos has no stated affiliation; “With Apart Research” does not resolve individual affiliation or organizational role (p. 1). | Supply the accurate affiliation, or an independent-researcher designation if applicable. |
| **Sprint-work and replacement-submission eligibility** | **Unresolved—not a demonstrated violation.** The November 9 audit/correction lacks timezone-qualified submission/version evidence (pp. 9, 15). | Provide hashes and timestamps, distinguishing sprint results from later corrections and identifying when the gated-majority analysis was completed. |
| **Official template structure** | The expected research structure and required appendix are present. Exact source-template compliance cannot be certified from images alone; the visible deficiencies are those identified above (pp. 1–15). | Resolve the concrete defects rather than redesigning the template. |

# Data-audit issues

The supplied audit reports **145 checked claims** and identifies two concrete discrepancies. These are **reporting inconsistencies**, not evidence that the principal outcome totals are wrong.

| Issue | Audit-supported correction | Consequence |
|---|---|---|
| **Mixed sampling ranges in Table 1** (p. 6) | Targets: **5 nonzero shares × 2 boards × 12 = 120**. Valid: **6 shares × 2 boards × 8 = 96**. Forged: **6 shares × 2 boards × 4 = 48**. Restricting the latter groups to 10–50% would instead give **80** and **40**. | Correct the caption by outcome group; no outcome-count change is required if the present sampling ranges are intended. |
| **Missing 3-of-5 per-share results** (Figure 1, p. 7; Table 3, p. 13) | DeepSeek/gpt-oss captures out of 24: **10%: 0/0; 20%: 1/2; 30%: 2/1; 40%: 7/5; 50%: 13/12**. Totals are **23/120** and **20/120**, agreeing with Table 1 (p. 6). | Add the Table 3 column and correct Figure 1’s exhaustive-sounding caption. |

**Audit boundary:** the supplied audit text is truncated during its summary, and its underlying data files are not included here. Its broad statement that other numbers match should be treated as a reported audit result—not as this chair’s independent verification of all remaining claims.

The missing retry metadata, fresh-key reconstruction, and absent historical prompts remain genuine provenance limitations even where archived totals recompute correctly (Appendix D, pp. 14–15). Arithmetic agreement does not establish complete historical execution auditing.

# Points reviewers got wrong

| Reviewer statement or proposed fix | Chair’s resolution |
|---|---|
| **B initially declared page-limit compliance.** | Incorrect under the supplied counting rule: non-reference material on p. 9 was omitted from that accounting. B subsequently agreed with the correction (pp. 1–9). |
| **C’s semantic-task limitation is framed as if confined to future work.** | Overstated. The abstract, §3.3, §4.3, limitations appendix, and conclusion already acknowledge untested independence and the exact-match limitation. The concern remains valid as a scope restriction, not as an undisclosed omission (pp. 1, 4, 7–8, 11). |
| **C’s “straw baseline” criticism implies an unacknowledged comparison problem.** | Only partially valid. Finding 1 explicitly calls the forgery advantage architectural by construction, discusses the missing public-key/tool baseline, and foregrounds gated majority. The remaining concern is reconstruction validation (pp. 5–6, 15). |
| **C proposes enlarging Figure 1 “to full width.”** | It already occupies nearly the full text width. A shared y-axis and legend below the panels are not defects by themselves; Table 1’s dense methodological note is the stronger visual concern (pp. 6–7). |
| **B initially supplies “first m seats” as the committee-selection rule.** | Not established by the manuscript. Ask for the actual rule; do not insert a plausible reconstruction as fact (§3.4, p. 5). |
| **D initially suggests independent-binomial intervals using n = 24, or a generic ±20-point width.** | Incorrect for the paired design. Each share has 12 committee draws underlying 24 paired outcomes; uncertainty must preserve that structure. D later accepted this correction (Table 1, p. 6; Figure 1, p. 7). |
| **D’s initial denominator gloss describes “108 runs.”** | Incorrect. Table 4 reports 108 case-conditions, with 756 auditor slots = 108 × 7; Table 5 lists twelve near-miss runs overall (p. 14). |
| **Several reviews say Table 2 omits lengths for three mutants.** | The image shows **four** omissions: seat, binding, duplicate, and audit. Policy and integrity have explicit lengths; uniqueness identifies the required depth (p. 12). |
| **An early citation fix inserts 2026 for SQLite.** | Do not invent a publication date. Use a verified date, or “n.d.” with suitable access information (References, p. 10). |
| **Broad criticism treats AI-use/revision disclosure itself as inappropriate.** | Too strong. Such disclosure belongs in back matter and is useful. Only superfluous automated-verdict history should be trimmed; methodological provenance and eligibility timestamps should remain (pp. 9, 15). |

No supplied evidence establishes fabricated references, late submission, invalid reconstructed outcomes, or general figure illegibility. Those should not be asserted as findings (References, pp. 9–10; provenance, p. 15; Figure 1, p. 7).

# Bottom line

**Weak accept as a three-day hackathon contribution, conditional on submission-compliance corrections.**

The defensible contribution is a **bounded-checked authorization kernel plus an informative empirical demonstration of committee capture and its limits**, including an honest negative comparison against gated majority (§§3–4, pp. 3–7). Novelty is primarily integrative, and general semantic safety remains unvalidated (§2, p. 3; §4.3, p. 7).

The highest-value few-hour revision is to:

1. **Fix the page count and affiliation** (pp. 1, 9).
2. **Reconcile headline claims with the historical provenance and truncation evidence** (pp. 2, 5, 12–15).
3. **Clarify the workflow, committee construction, and hidden/visible-board results** (pp. 3–6).
4. **Repair the two audit-confirmed display errors and foreground draw-level sampling** (Table 1, p. 6; Figure 1, p. 7; Table 3, p. 13).

A genuinely judgment-dependent benchmark with measurable correlated honest error is **future work**, not a reasonable demand for a few-hour hackathon revision. The present report should make that boundary unmistakable (§4.3, p. 7; Conclusion, p. 8).