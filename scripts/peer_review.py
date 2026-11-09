"""Multi-model AI peer review with a debate round, a data audit and a chair (OpenRouter).

Pipeline (one "round"):
  1. Independent reviews: each reviewer model reviews the manuscript (scientific validity
     focus, structured JSON concerns with severity).
  2. Debate: each reviewer sees the other reviewers' anonymised concerns, marks each as
     agree / disagree / factually-wrong-about-the-paper with reasons, revises its own
     severities and adds anything missed.
  3. Data audit: one model receives the manuscript plus the raw aggregate result tables and
     checks every numeric claim against them.
  4. Chair: a separate model consolidates concerns into a ranked list with consensus level,
     validity judgement and recommended action.

Design inspired by poldrack/ai-peer-review (MIT): independent multi-model reviews, a
meta-review, and a scientific-validity-only reviewer profile. This adds a debate round,
a data audit, OpenRouter support and a spend ledger.

Usage:
  python scripts/peer_review.py --paper docs/report/REPORT.md --data docs/report/review-data.md \
      --out docs/report/reviews/round-1 --max-usd 8
Keys: OPENROUTER_API_KEY. Spend: per-run cap via the shared ledger (tag 'review').
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('FLEET_WITNESS_LEDGER_TAG', 'review')
from fleet_witness.swarm.providers import Ledger, ModelClient  # noqa: E402

REVIEWERS = ['openai/gpt-6.1-sol', 'google/gemini-4-argon', 'x-ai/grok-4.7', 'qwen/qwen3.8-max-0902']
AUDITOR = 'google/gemini-4-argon'
CHAIR = 'openai/gpt-6.1-sol-pro'

SYSTEM = (
    'You are an expert, rigorous peer reviewer for an AI-safety research venue (multi-agent oversight, '
    'formal methods, empirical ML). Judge SCIENTIFIC VALIDITY only: soundness of methods, whether claims '
    'are supported by the evidence presented, statistical treatment, confounds, threats to validity, '
    'overclaiming, missing controls, reproducibility, and accurate positioning against prior work. Ignore '
    'prose style and formatting. If something seems missing, treat it as a request for clarification rather '
    'than asserting the work was not done. Be specific: cite the section or table. Do not invent references; '
    'if you suggest related work, say it should be verified.'
)

RUBRIC = """This is a 3-day hackathon report (Apart Research Swarm Alignment Sprint). Judges score it on
three dimensions, 1-5 each, using these official descriptors:
IMPACT POTENTIAL & INNOVATION: How much would this matter for the field if it worked? How innovative? For 4-5:
 is this actually new to the field, or replicating recent work? 1 negligible; 2 limited (real problem, generic or
 well-trodden approach); 3 moderate (clear problem, reasonable approach, some novelty in framing or method);
 4 significant (important problem, original approach or neglected area, others could build on it); 5 exceptional
 (critical problem, genuinely novel, opens a direction, clear theory of change).
EXECUTION QUALITY: How sound are methodology, implementation and findings? 1 seriously flawed; 2 weak (significant
 gaps: missing validation, flawed design); 3 competent (technically solid given the short duration, interpretable,
 limitations acknowledged); 4 strong (thorough, convincing validation, results clearly support conclusions);
 5 exceptional (ambitious scope executed rigorously, unusually robust validation).
PRESENTATION & CLARITY: 1 incomprehensible; 2 hard to follow (key information buried, or diluted by excessive
 length); 3 clear enough; 4 well presented; 5 exceptionally clear.
Judge it as a hackathon report: reward a promising, honestly backed idea; penalize overclaiming."""

REVIEW_TASK = RUBRIC + """

Review the manuscript below. Reply with ONLY a JSON object:
{{"summary": "<3 sentences>",
  "scores": {{"impact_innovation": 1-5, "execution": 1-5, "presentation": 1-5}},
  "score_rationale": {{"impact_innovation": "...", "execution": "...", "presentation": "..."}},
  "strengths": ["..."],
  "concerns": [{{"id": "C1", "severity": "critical|major|minor", "category": "<e.g. validity, statistics, overclaiming, confound, reproducibility, related-work>",
                 "location": "<section/table>", "issue": "<what is wrong>", "why_it_matters": "...",
                 "suggested_fix": "<concrete, feasible within a hackathon if possible>"}}],
  "verdict": "accept|weak accept|borderline|weak reject|reject",
  "confidence": 1-5}}

MANUSCRIPT:
{paper}"""

DEBATE_TASK = """You previously reviewed this manuscript. Below are your concerns and the concerns of other
anonymous reviewers. For EACH other reviewer's concern decide: "agree", "disagree", or
"factually_wrong" (the concern misreads what the paper actually says or does), with a one-sentence
reason grounded in the manuscript. Then revise your own concerns (change severity, withdraw, or add
concerns you now think were missed). Reply with ONLY a JSON object:
{{"judgements": [{{"concern_ref": "<reviewer letter>.<id>", "stance": "agree|disagree|factually_wrong", "reason": "..."}}],
  "revised_own_concerns": [{{"id": "...", "severity": "critical|major|minor", "issue": "...", "suggested_fix": "..."}}],
  "withdrawn": ["<own ids>"],
  "new_concerns": [{{"id": "N1", "severity": "...", "issue": "...", "suggested_fix": "..."}}],
  "rebuttals": [{{"to": "<reviewer letter>", "about": "<concern ref>", "response": "<defend or concede, with reason>"}}],
  "updated_scores": {{"impact_innovation": 1-5, "execution": 1-5, "presentation": 1-5}},
  "updated_verdict": "accept|weak accept|borderline|weak reject|reject"}}

YOUR CURRENT POSITION (your review, plus your previous debate response if any):
{own}

OTHER REVIEWERS' CURRENT POSITIONS (full reviews and, after round 1, their debate responses
including any challenges to your concerns; answer those challenges in "rebuttals"):
{others}

MANUSCRIPT:
{paper}"""

AUDIT_TASK = """You are a data auditor. Check EVERY numeric claim in the manuscript (abstract, tables,
findings, appendix) against the raw result data provided. Report mismatches, unsupported numbers,
arithmetic errors, wrong denominators, and statistical misstatements. Reply with ONLY a JSON object:
{{"checked_claims": <int>, "issues": [{{"location": "...", "claim": "...", "data_says": "...",
  "severity": "critical|major|minor"}}], "notes": "..."}}

RAW DATA:
{data}

MANUSCRIPT:
{paper}"""

CHAIR_TASK = """You chair the review. Consolidate the independent reviews, the debate judgements and
the data audit into a single ranked list of concerns. Merge duplicates. For each, give: consensus
(how many reviewers raised or agreed), validity (valid / partially valid / invalid, using the
debate's factually_wrong judgements), severity, and the single most effective fix that the authors
can make in a few hours (text change, extra analysis, or small experiment) or "future work".
Reply in Markdown with sections: Rubric scores (each reviewer's initial and final Impact /
Execution / Presentation, plus your own calibrated score with one-line justification), Overall
assessment (with verdict distribution), Resolved vs still-contested disagreements, Ranked concerns
(table: #, concern, consensus, validity, severity, recommended action, effort), Data-audit issues,
Points reviewers got wrong, and Bottom line.

INDEPENDENT REVIEWS:
{reviews}

DEBATE:
{debate}

DATA AUDIT:
{audit}"""


def extract_json(text):
    match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text or '', re.S) or re.search(r'(\{.*\})', text or '', re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {'unparsed': (text or '')[:20000]}


def call(client, task):
    result = client.complete(SYSTEM, task)
    return result['text'], result['cost_usd']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-usd', type=float, default=8.0)
    parser.add_argument('--debate-rounds', type=int, default=2)
    parser.add_argument('--reasoning', default='high', help='OpenRouter reasoning effort for all models')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    paper = Path(args.paper).read_text(encoding='utf-8')
    data = Path(args.data).read_text(encoding='utf-8')
    ledger = Ledger('openrouter', run_cap_usd=args.max_usd, lifetime_cap_usd=30)
    clients = {m: ModelClient('openrouter', m, ledger, max_output_tokens=8000, temperature=0.3,
                              timeout=900, max_concurrency=4) for m in set(REVIEWERS + [AUDITOR, CHAIR])}
    for client in clients.values():
        client.extra_body = {'reasoning': {'effort': args.reasoning}}
    letters = {m: chr(ord('A') + i) for i, m in enumerate(REVIEWERS)}
    spent = 0.0

    print('Round 1: independent reviews + data audit ...', flush=True)
    with ThreadPoolExecutor(len(REVIEWERS) + 1) as pool:
        futures = {m: pool.submit(call, clients[m], REVIEW_TASK.format(paper=paper)) for m in REVIEWERS}
        audit_future = pool.submit(call, clients[AUDITOR], AUDIT_TASK.format(paper=paper, data=data))
        reviews = {}
        for m, f in futures.items():
            text, cost = f.result()
            spent += cost
            reviews[m] = extract_json(text)
            (out / f'review_{letters[m]}.json').write_text(json.dumps({'model': m, **reviews[m]}, indent=2), encoding='utf-8')
        audit_text, cost = audit_future.result()
        spent += cost
        audit = extract_json(audit_text)
        (out / 'data_audit.json').write_text(json.dumps({'model': AUDITOR, **audit}, indent=2), encoding='utf-8')

    debate, transcript = {}, []

    def position(m):
        latest = {'review': reviews[m]}
        if m in debate:
            latest['latest_debate_response'] = debate[m]
        return json.dumps(latest, indent=1)

    for round_no in range(1, args.debate_rounds + 1):
        print(f'Debate round {round_no} ...', flush=True)
        with ThreadPoolExecutor(len(REVIEWERS)) as pool:
            futures = {}
            for m in REVIEWERS:
                others = '\n\n'.join(f'Reviewer {letters[o]}:\n{position(o)}' for o in REVIEWERS if o != m)
                futures[m] = pool.submit(call, clients[m], DEBATE_TASK.format(own=position(m), others=others, paper=paper))
            new = {}
            for m, f in futures.items():
                text, cost = f.result()
                spent += cost
                new[m] = extract_json(text)
                (out / f'debate{round_no}_{letters[m]}.json').write_text(json.dumps({'model': m, **new[m]}, indent=2),
                                                                           encoding='utf-8')
        debate = new
        transcript.append(new)

    print('Chair ...', flush=True)
    anon = lambda d: json.dumps({f'Reviewer {letters[m]}': v for m, v in d.items()}, indent=1)
    full_debate = json.dumps([{f'Reviewer {letters[m]}': v for m, v in rnd.items()} for rnd in transcript], indent=1)
    meta_text, cost = call(clients[CHAIR], RUBRIC + '\n\n' + CHAIR_TASK.format(
        reviews=anon(reviews), debate=full_debate, audit=json.dumps(audit, indent=1)))
    spent += cost
    (out / 'meta_review.md').write_text(meta_text, encoding='utf-8')
    verdicts = {letters[m]: (debate[m].get('updated_verdict') or reviews[m].get('verdict')) for m in REVIEWERS}
    scores = {letters[m]: {'initial': reviews[m].get('scores'), 'final': debate[m].get('updated_scores')} for m in REVIEWERS}
    (out / 'manifest.json').write_text(json.dumps({'reviewers': {letters[m]: m for m in REVIEWERS}, 'auditor': AUDITOR,
                                                   'chair': CHAIR, 'debate_rounds': args.debate_rounds,
                                                   'verdicts_after_debate': verdicts, 'rubric_scores': scores,
                                                   'cost_usd': round(spent, 4)}, indent=2), encoding='utf-8')
    print(f'Done. Verdicts: {verdicts}. Scores: {scores}. Cost ${spent:.3f}. See {out / "meta_review.md"}')


if __name__ == '__main__':
    main()
