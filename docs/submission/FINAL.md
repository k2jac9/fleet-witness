# Final hackathon submission

**Status: prepared, awaiting upload by Ignatius Pio Binawan (as of 2026-11-09, 05:35 UTC-5).**
Update this line with the upload time and confirmation once the official form has been submitted.
A Git push is not a submission confirmation.

## Retrospective correction: 11 November 2026

The report source now includes the [11 November evidence correction](../report/CORRECTIONS-2026-11-11.md),
dated after the recorded preparation and event deadline. It scopes archive reproduction to Experiment 1,
documents Experiment 2's aggregate-only public evidence, and corrects scanner coverage, missing-answer
and reference-run attribution claims. It does not establish an official upload, a replacement submission
or acceptance. The preparation status above remains unchanged because no upload confirmation is recorded.
The original plan, run aggregates, review outputs and review manifests remain historical records.

Round 4 recorded three AI accept verdicts and one weak accept, but its numerical audit ended with
`status: "length"` and an empty `unparsed` result. The manifest's `status: "completed"` describes the
historical pipeline outcome; it does not show a passed numerical audit. Those model reviews do not
certify the retrospectively corrected report.

## Prepared submission details

| Field | Value |
| --- | --- |
| Title (keep exactly the same for any replacement) | Verify the Institution, Not the Agents: Checks and Balances for AI Swarms, Tested Against Hidden Colluders |
| Report PDF | [`docs/report/latex/report.pdf`](../report/latex/report.pdf) (source: [`report.tex`](../report/latex/report.tex)) |
| Authors | Alejandro Castellanos (Independent Researcher); Ignatius Pio Binawan (University of Toronto) |
| Track | 4, Multi-Agent Oversight and Control (cross-track: 2 and 3) |
| Repository | https://github.com/k2jac9/fleet-witness |
| Deadline | 2026-11-08 23:59 AoE = 2026-11-09 11:59 UTC = 06:59 Toronto (EST) |

## How this relates to the other report in the repository

The prepared report covers four studies: the kernel check, Experiment 1 (checklist task), Experiment 2
(judgement task) and, in Appendix F, the live-supervisor pilot. The pilot was designed and run by
Alejandro Castellanos; its full write-up is the companion report [`docs/report/latest.md`](../report/latest.md)
with its evidence package in [`docs/submission/latest/`](latest/). That package was prepared overnight
with an earlier title and was not uploaded; it is kept unchanged as the pilot's evidence.

## Historical prepared abstract (9 November record)

The text below preserves the earlier prepared abstract. Its prior heading, "as entered in the form",
did not establish an upload confirmation. The corrected manuscript and evidence note qualify its
rounded committee comparison and public evidence scope.

When many AI agents work together, a few of them can secretly coordinate to push a harmful action
through, and checking every agent one by one does not scale. We show that a small institution, a
program that enforces checks and balances, can stop forged actions and limit colluders' influence
without trusting any individual agent. One agent proposes a change, a randomly chosen committee must
sign off, and automatic checks must pass. Its rules held in all 23,376 reachable states of a small test
world, and the test caught all seven deliberately broken versions. We then attacked it with 50-agent
populations in which up to half the agents colluded. A plain majority vote approved every forged
release; the institution's automatic checks blocked them all. In a checklist task, random committees
were never captured more often than their seating allowed. In a judgement task, reviewing 48 pull
requests with hidden harmful code, frontier reviewers (GPT-6.1 Sol, Gemini 4 Argon) never approved a
harmful change. A small model's mistakes, however, fell on the same changes: a seven-seat committee of
its copies approved 12% of harmful changes, exactly as often as a single reviewer. Giving half the
seats to a stronger model with different blind spots cut this to 0.1%. Conclusion: put every check a
program can do into verified code, and do not rely on more copies of the same model for safety; measure
where reviewers share blind spots and seat reviewers who do not share them.

## Historical preparation checks (9 November record)

These describe the earlier prepared edition. Current compilation and verification belong to the
dated correction and [build evidence](../BUILD_STATUS.md), not to this historical checklist.

- Main body 7 pages after the title page (limit 8, excluding references and appendices).
- Abstract 245 words (limit 150–250).
- Authors and affiliations on the title page.
- Required "Limitations and Dual-Use / Ethical Considerations" appendix: Appendix A.
- Final AI review (round 4, fast format): 3 accept, 1 weak accept
  ([`docs/report/reviews/round-4/`](../report/reviews/round-4/)); its numerical audit was incomplete,
  as documented above.
