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
      --out runs/review-new --authorization /private/path/review-authorization.json
Keys: OPENROUTER_API_KEY. All models must share the authorized SQLite run envelope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.swarm.operator import authorized_clients  # noqa: E402
from fleet_witness.swarm.providers import ProviderError  # noqa: E402
from fleet_witness.swarm.run_records import PrivateRunLog, public_attempts, runtime_identity  # noqa: E402

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


def call(client, task, receipts):
    response, attempts, status = None, [], 'provider_error'
    result = None
    try:
        result = client.complete(SYSTEM, task)
        response = result['text']
        attempts = public_attempts(result.get('attempts', []))
        status = result.get('status', 'completed')
        if result.get('truncated') or status not in ('succeeded', 'completed', 'settled'):
            raise ProviderError('incomplete review response; no retry', attempts=attempts, status=status)
        return response, result['cost_usd']
    except Exception as error:
        if result is None:
            attempts = public_attempts(getattr(error, 'attempts', []))
            status = getattr(error, 'status', 'provider_error')
        raise
    finally:
        receipts.write(uuid.uuid4().hex, SYSTEM, task, response, status, attempts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--authorization', type=Path, required=True,
                        help='private explicit authorizations for all models, sharing one run envelope')
    parser.add_argument('--max-usd', type=float, help='must match the frozen shared run cap')
    parser.add_argument('--debate-rounds', type=int, default=2)
    parser.add_argument('--reasoning', default='high', help='OpenRouter reasoning effort for all models')
    args = parser.parse_args()
    if not 0 <= args.debate_rounds <= 3:
        parser.error('--debate-rounds must be between zero and three')
    out = Path(args.out)
    if out.exists():
        parser.error('output already exists; preserve it and choose a fresh directory')
    paper = Path(args.paper).read_text(encoding='utf-8')
    data = Path(args.data).read_text(encoding='utf-8')
    clients = authorized_clients('openrouter', REVIEWERS + [AUDITOR, CHAIR], args.authorization,
                                 max_usd=args.max_usd, temperature=0.3)
    for client in clients.values():
        client.extra_body = {'reasoning': {'effort': args.reasoning}}
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipts = PrivateRunLog(out)
    from fleet_witness.swarm.providers import source_identity
    manifest = {'schema_version': 'swarm-review-2', 'status': 'started', 'source': source_identity(),
                'runtime': runtime_identity(), 'paper_sha256': hashlib.sha256(paper.encode()).hexdigest(),
                'data_sha256': hashlib.sha256(data.encode()).hexdigest(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'debate_rounds': args.debate_rounds, 'attempt_policy': 'one-attempt-no-retries',
                'private_receipts': 'private/requests.jsonl'}
    try:
        manifest.update(review_pipeline(out, paper, data, clients, args.debate_rounds, receipts))
        manifest['status'] = 'completed'
    except Exception as error:
        manifest.update(status='failed', error=type(error).__name__)
        raise
    finally:
        manifest.update(receipts.summary())
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8')
        receipts.close()
    print(f'Done. See {out / "manifest.json"}')


def review_pipeline(out, paper, data, clients, debate_rounds, receipts):
    letters = {m: chr(ord('A') + i) for i, m in enumerate(REVIEWERS)}
    print('Independent reviews, then data audit (one paid request at a time) ...', flush=True)
    reviews = {}
    for m in REVIEWERS:
        text, _ = call(clients[m], REVIEW_TASK.format(paper=paper), receipts)
        reviews[m] = extract_json(text)
        (out / f'review_{letters[m]}.json').write_text(json.dumps({'model': m, **reviews[m]}, indent=2), encoding='utf-8')
    audit_text, _ = call(clients[AUDITOR], AUDIT_TASK.format(paper=paper, data=data), receipts)
    audit = extract_json(audit_text)
    (out / 'data_audit.json').write_text(json.dumps({'model': AUDITOR, **audit}, indent=2), encoding='utf-8')

    debate, transcript = {}, []

    def position(m):
        latest = {'review': reviews[m]}
        if m in debate:
            latest['latest_debate_response'] = debate[m]
        return json.dumps(latest, indent=1)

    for round_no in range(1, debate_rounds + 1):
        print(f'Debate round {round_no} ...', flush=True)
        tasks = {}
        for m in REVIEWERS:
            others = '\n\n'.join(f'Reviewer {letters[o]}:\n{position(o)}' for o in REVIEWERS if o != m)
            tasks[m] = DEBATE_TASK.format(own=position(m), others=others, paper=paper)
        new = {}
        for m in REVIEWERS:
            text, _ = call(clients[m], tasks[m], receipts)
            new[m] = extract_json(text)
            (out / f'debate{round_no}_{letters[m]}.json').write_text(json.dumps({'model': m, **new[m]}, indent=2),
                                                                  encoding='utf-8')
        debate = new
        transcript.append(new)

    print('Chair ...', flush=True)
    anon = lambda d: json.dumps({f'Reviewer {letters[m]}': v for m, v in d.items()}, indent=1)
    full_debate = json.dumps([{f'Reviewer {letters[m]}': v for m, v in rnd.items()} for rnd in transcript], indent=1)
    meta_text, _ = call(clients[CHAIR], RUBRIC + '\n\n' + CHAIR_TASK.format(
        reviews=anon(reviews), debate=full_debate, audit=json.dumps(audit, indent=1)), receipts)
    (out / 'meta_review.md').write_text(meta_text, encoding='utf-8')
    verdicts = {letters[m]: (debate.get(m, {}).get('updated_verdict') or reviews[m].get('verdict')) for m in REVIEWERS}
    scores = {letters[m]: {'initial': reviews[m].get('scores'), 'final': debate.get(m, {}).get('updated_scores')}
              for m in REVIEWERS}
    return {'reviewers': {letters[m]: m for m in REVIEWERS}, 'auditor': AUDITOR, 'chair': CHAIR,
            'verdicts_after_debate': verdicts, 'rubric_scores': scores}


if __name__ == '__main__':
    main()
