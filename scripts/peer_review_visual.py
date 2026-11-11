"""Authorized text-only peer review; the historical filename is retained for compatibility.

The existing ModelClient supports text only. Image/PDF mode is explicitly refused
until separately reviewed and qualified; no images are flattened into text and
no rendered visual assessment is claimed. Historical review artifacts are unchanged.
Every future stage uses one source-bound shared ledger envelope, one attempt and
the existing input/output/30-second bounds. Invalid required output stops the
pipeline with its durable accounting and private receipt intact.

Usage (placeholders, not qualification):
  python scripts/peer_review_visual.py --tex paper.tex --guidelines guidelines.md \
      --data results.json --out runs/new-text-review \
      --authorization /private/qualified-records.json --live
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.swarm.providers import ProviderError, source_identity  # noqa: E402
from fleet_witness.swarm.run_records import runtime_identity  # noqa: E402
from scripts.research_requests import (ResearchRequests, ledger_snapshot, paid_arguments,
                                       research_clients, strict_object)  # noqa: E402

REVIEWERS = ['openai/gpt-6.1-sol', 'google/gemini-4-argon', 'meta/muse-wonder', 'xiaomi/mimo-v2.6-pro']
AUDITOR = 'google/gemini-4-argon'
CHAIR = 'openai/gpt-6.1-sol-pro'

SYSTEM = (
    'You are a rigorous peer reviewer for an AI-safety research venue. This is a TEXT-ONLY review of '
    'the supplied LaTeX source, guidelines and result data. No PDF page images are supplied. Assess '
    'methods, evidence, statistics, confounds, overclaiming, reproducibility, prose and source structure. '
    'Do not claim to have inspected rendered typography, layout, figure legibility or page limits. '
    'The compatibility score name formality_aesthetics covers source-level writing and structure only. '
    'Cite source sections, figure labels or table labels. Treat apparently missing evidence as a request '
    'for clarification, and do not invent references.'
)

RUBRIC = """This is a 3-day hackathon report (Apart Research Swarm Alignment Sprint). Score five dimensions, 1-5 each.
The first three are Apart's official judging criteria (descriptors below and in the guidelines document).
IMPACT POTENTIAL & INNOVATION: 1 negligible; 2 limited (real problem, generic approach); 3 moderate (clear problem,
 some novelty in framing or method); 4 significant (important problem, original approach or neglected area, others
 could build on it); 5 exceptional (genuinely novel, opens a direction, clear theory of change). For 4-5: is it new?
EXECUTION QUALITY: 1 seriously flawed; 2 weak (missing validation, flawed design); 3 competent (solid given the short
 duration, interpretable, limitations acknowledged); 4 strong (thorough, convincing validation, results support
 conclusions); 5 exceptional (ambitious scope, unusually robust validation).
PRESENTATION & CLARITY (Apart): 1 incomprehensible; 2 hard to follow (key information buried, excessive length);
 3 clear enough; 4 well presented; 5 exceptionally clear, a model for this type of work.
Two additional criteria requested by the authors:
FORMALITY & SOURCE STRUCTURE (the compatibility key is formality_aesthetics): assess writing register,
 heading hierarchy, terminology, citation syntax and caption text from source alone. 1 unprofessional;
 2 several source-level style problems; 3 acceptable with inconsistencies; 4 polished source with minor issues;
 5 exceptionally clear source structure and style. Rendered visual quality is NOT assessed.
READABILITY (human perspective): can a technically literate reader understand it on one pass? Penalize convoluted
 sentences, needless hedging chains, undefined abbreviations, inconsistent terminology, dense paragraphs and
 over-qualified prose; domain jargon is acceptable. 1 very hard to read; 2 often convoluted; 3 readable with effort;
 4 easy to follow; 5 exceptionally clear and fluent.
Judge it as a hackathon report: reward a promising, honestly backed idea; penalize overclaiming and any breach of
the supplied submission requirements. Source can establish abstract wording, appendices and author fields;
rendered page count and template compliance remain unassessed."""

PLAN_SYSTEM = (
    'You are an expert, rigorous reviewer of research plans for an AI-safety venue (multi-agent oversight, '
    'empirical ML, formal methods). You review a plan BEFORE it is executed, so your job is to make the eventual '
    'study better: find design flaws, confounds, invalid measurements, missing controls, unrealistic scope or '
    'timing, and wasted effort, and propose concrete, feasible fixes. Be specific and constructive. Do not invent '
    'references; if you suggest related work, say it should be verified.'
)

PLAN_TASK = """You are reviewing a research PLAN for a hackathon project (official judging rubric and requirements are
in the guidelines below). Assess the time, model and budget constraints actually stated in the supplied plan.
Reply with ONLY a JSON object:
{"summary": "<3 sentences>",
 "will_it_answer_the_questions": "<does the design actually test RQ1-RQ5? where not, why>",
 "predicted_scores_if_executed_well": {"impact_innovation": 1-5, "execution": 1-5, "presentation": 1-5},
 "top_changes": [{"rank": 1, "change": "<concrete change to the plan>", "why": "...", "cost": "<time/money>",
                  "score_effect": "<which rubric dimension it helps and how>"}],
 "concerns": [{"id": "C1", "severity": "critical|major|minor", "issue": "...", "suggested_fix": "..."}],
 "cut_if_short_on_time": ["<what to drop first>"],
 "verdict": "proceed|proceed with changes|redesign"}"""

PLAN_CHAIR = """You chair a fast plan review (no debate round). Consolidate the independent reviews below into ONE
actionable revision list for the authors. Lead with what to change, not with scores. Reply in Markdown with
sections: Bottom line (2-3 sentences: proceed or not, and the single most important change), Ranked changes
(table: #, change, how many reviewers raised it, why, cost, effect on rubric scores), Disagreements you resolved
(and how), What to cut if time runs short, Predicted scores if executed well (each reviewer and your calibrated
view).

INDEPENDENT REVIEWS:
{reviews}"""

SCORE_KEYS = ('impact_innovation', 'execution', 'presentation', 'formality_aesthetics', 'readability')
SCORES_JSON = '{"impact_innovation": 1-5, "execution": 1-5, "presentation": 1-5, "formality_aesthetics": 1-5, "readability": 1-5}'

REVIEW_TASK = RUBRIC + """

Review the manuscript LaTeX source below. This is text-only: no PDF or page images are supplied.
Reply with ONLY a JSON object:
{"summary": "<3 sentences>",
 "scores": SCORES,
 "score_rationale": {"impact_innovation": "...", "execution": "...", "presentation": "...", "formality_aesthetics": "...", "readability": "..."},
 "strengths": ["..."],
 "concerns": [{"id": "C1", "severity": "critical|major|minor",
               "category": "<validity|statistics|overclaiming|confound|reproducibility|related-work|requirements|formality|figures|tables|headings|capitalization|citations|source-structure|readability>",
               "location": "<source section / figure label / table label>", "issue": "...", "why_it_matters": "...",
               "suggested_fix": "<concrete, feasible within a few hours if possible>"}],
 "readability_examples": [{"location": "...", "original": "<short quote>", "suggested_rewrite": "..."}],
 "verdict": "accept|weak accept|borderline|weak reject|reject",
 "confidence": 1-5}"""

DEBATE_TASK = """You previously reviewed this manuscript (LaTeX source is supplied again; no page images). Below are
your position and the other anonymous reviewers' positions. For EACH other reviewer's concern decide "agree",
"disagree" or "factually_wrong" (it misreads the supplied source), with a one-sentence reason grounded in the
source. Do not infer rendered visual quality. Then revise your own concerns. Reply with ONLY a JSON object:
{"judgements": [{"concern_ref": "<reviewer letter>.<id>", "stance": "agree|disagree|factually_wrong", "reason": "..."}],
 "revised_own_concerns": [{"id": "...", "severity": "critical|major|minor", "issue": "...", "suggested_fix": "..."}],
 "withdrawn": ["<own ids>"],
 "new_concerns": [{"id": "N1", "severity": "...", "category": "...", "issue": "...", "suggested_fix": "..."}],
 "rebuttals": [{"to": "<reviewer letter>", "about": "<concern ref>", "response": "..."}],
 "updated_scores": SCORES,
 "updated_verdict": "accept|weak accept|borderline|weak reject|reject"}

YOUR CURRENT POSITION:
{own}

OTHER REVIEWERS' CURRENT POSITIONS:
{others}"""

AUDIT_TASK = """You are a data auditor. Check EVERY numeric claim in the manuscript (abstract, tables, figures,
findings, appendices) against the result data provided. The data includes a historical review-data file and a dated
correction record; where they disagree, the correction record supersedes the historical file. Report mismatches,
unsupported numbers, arithmetic errors, wrong denominators and statistical misstatements. Check numbers available
in the source and supplied result data; numbers available only inside an external image are outside this text-only audit. Reply with ONLY a JSON object:
{"checked_claims": <positive int>, "issues": [{"location": "...", "claim": "...", "data_says": "...",
  "severity": "critical|major|minor"}], "notes": "..."}

RESULT DATA:
{data}"""

CHAIR_TASK = """You chair this TEXT-ONLY review. No PDF or page images are supplied. Calibrate source-level formality,
structure and readability; rendered layout, typography and figure legibility remain unassessed. Consolidate the
independent reviews, the debate and the data audit into a single ranked list of concerns. Merge duplicates. For each give consensus (how many reviewers raised or agreed),
validity (valid / partially valid / invalid, using the debate's factually_wrong judgements), severity, and the single
most effective fix the authors can make in a few hours, or "future work".
Reply in Markdown with sections: Rubric scores (table of each reviewer's initial and final scores on all five
dimensions, plus your own calibrated score with a one-line justification per dimension), Overall assessment (with
verdict distribution), Substance concerns (ranked table: #, concern, consensus, validity, severity, action, effort),
Formality and source structure (heading hierarchy, capitalization, citations, caption text),
Readability (with the most useful concrete rewrites), Requirements visible in source (abstract wording, required
appendix, authors and affiliations; rendered page limits remain unassessed), Data-audit issues, Points reviewers
got wrong, and Bottom line.

INDEPENDENT REVIEWS:
{reviews}

DEBATE:
{debate}

DATA AUDIT:
{audit}"""

SEVERITY = frozenset(('critical', 'major', 'minor'))
VERDICT = frozenset(('accept', 'weak accept', 'borderline', 'weak reject', 'reject'))
SCORES = {key: range(1, 6) for key in SCORE_KEYS}
CONCERN = {'id': str, 'severity': SEVERITY, 'issue': str, 'suggested_fix': str}
SCHEMAS = {
    'plan': {'summary': str, 'will_it_answer_the_questions': str,
             'predicted_scores_if_executed_well': {key: range(1, 6) for key in SCORE_KEYS[:3]},
             'top_changes': [{'rank': range(1, 10001), 'change': str, 'why': str, 'cost': str, 'score_effect': str}],
             'concerns': [CONCERN], 'cut_if_short_on_time': [str],
             'verdict': frozenset(('proceed', 'proceed with changes', 'redesign'))},
    'review': {'summary': str, 'scores': SCORES, 'score_rationale': {key: str for key in SCORE_KEYS},
               'strengths': [str], 'concerns': [{**CONCERN, 'category': str, 'location': str, 'why_it_matters': str}],
               'readability_examples': [{'location': str, 'original': str, 'suggested_rewrite': str}],
               'verdict': VERDICT, 'confidence': range(1, 6)},
    'audit': {'checked_claims': range(1, 2**31),
              'issues': [{'location': str, 'claim': str, 'data_says': str, 'severity': SEVERITY}], 'notes': str},
    'debate': {'judgements': [{'concern_ref': str, 'stance': frozenset(('agree', 'disagree', 'factually_wrong')),
                               'reason': str}],
               'revised_own_concerns': [CONCERN], 'withdrawn': [str],
               'new_concerns': [{**CONCERN, 'category': str}],
               'rebuttals': [{'to': str, 'about': str, 'response': str}],
               'updated_scores': SCORES, 'updated_verdict': VERDICT},
}


def _validate(value, schema):
    if isinstance(schema, dict):
        if not isinstance(value, dict) or set(value) != set(schema):
            raise ValueError('missing or unexpected response fields')
        for key, expected in schema.items():
            _validate(value[key], expected)
    elif isinstance(schema, list):
        if not isinstance(value, list):
            raise ValueError('expected response list')
        for item in value:
            _validate(item, schema[0])
    elif isinstance(schema, range):
        if type(value) is not int or value not in schema:
            raise ValueError('response integer outside its allowed range')
    elif isinstance(schema, frozenset):
        if not isinstance(value, str) or value not in schema:
            raise ValueError('unexpected response category')
    elif schema is str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError('required response text is empty')
    else:
        raise ValueError('unknown response schema')


def extract_json(text, kind='review'):
    parsed = strict_object(text)
    _validate(parsed, SCHEMAS[kind])
    return parsed


def content(text, images=()):
    if images or not isinstance(text, str):
        raise ValueError('image mode is not qualified; supply text-only source without PDF/page images')
    return text


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


@contextmanager
def review_session(args, out, manifest):
    if getattr(args, 'pdf', None):
        raise ValueError('image/PDF mode is not qualified; supply text-only source')
    models = [*REVIEWERS, CHAIR] + ([AUDITOR] if 'auditor' in manifest else [])
    clients = research_clients(models, args.authorization, live=args.live, max_usd=args.max_usd,
                               max_output_tokens=args.max_tokens, temperature=.3, reasoning=args.reasoning)
    client = clients[CHAIR]
    requests = ResearchRequests(out)
    started = time.monotonic()
    manifest.update(status='started', gated_workflow=True, review_mode='text-only', page_images=0,
                    visual_assessment=False,
                    scope='Supplied source and text data only; rendered PDF/figure/layout quality not assessed.',
                    source=source_identity(), runtime=runtime_identity(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    private_receipts='private/requests.jsonl', completed_stages=[],
                    ledger_before=ledger_snapshot(client),
                    authorization_ids={model: clients[model].authorization['authorization_id'] for model in clients},
                    reasoning=args.reasoning, attempt_policy='one-attempt-no-retries')

    def ask(model, task, label, *, kind=None, system=SYSTEM, filename=None):
        manifest['active_stage'] = label
        print(f'{label}: {model} (text-only, one attempt)', flush=True)
        result = requests.call(clients[model], system, content(task), label,
                               validate=(lambda text: extract_json(text, kind)) if kind else None)
        target = out / (filename or (label + ('.json' if kind else '.md')))
        if kind:
            target.write_text(json.dumps({'model': model, **result}, indent=2), encoding='utf-8')
        else:
            target.write_text(result, encoding='utf-8')
        manifest['completed_stages'].append(label)
        manifest.pop('active_stage', None)
        return result

    try:
        yield ask
        manifest['status'] = 'completed'
    except BaseException as error:
        manifest.update(status='partial' if manifest['completed_stages'] else 'failed',
                        error=type(error).__name__, failed_stage=manifest.get('active_stage'))
        raise
    finally:
        manifest.update(**requests.summary(), ledger_after=ledger_snapshot(client),
                        wall_seconds=round(time.monotonic() - started, 3))
        requests.close()
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(f"Review {manifest['status']}: ${manifest['cost_usd']:.6f} settled / "
              f"${manifest['held_usd']:.6f} held -> {out}", flush=True)


def review_plan(args, out):
    """Independent text reviews followed by a chair, within one shared envelope."""
    plan = Path(args.plan).read_text(encoding='utf-8')
    guidelines = Path(args.guidelines).read_text(encoding='utf-8')
    letters = {model: chr(ord('A') + index) for index, model in enumerate(REVIEWERS)}
    manifest = {'schema_version': 'plan-review-2', 'reviewers': {letters[m]: m for m in REVIEWERS},
                'chair': CHAIR, 'debate_rounds': 0, 'plan_sha256': _hash(plan),
                'guidelines_sha256': _hash(guidelines),
                'required_stages': [*[f'plan_review_{letters[m]}' for m in REVIEWERS], 'chair']}
    task = PLAN_TASK + f'\n\nGUIDELINES:\n{guidelines}\n\nPLAN:\n{plan}'
    with review_session(args, out, manifest) as ask:
        reviews = {model: ask(model, task, f'plan_review_{letters[model]}', kind='plan', system=PLAN_SYSTEM)
                   for model in REVIEWERS}
        anon = json.dumps({f'Reviewer {letters[m]}': value for m, value in reviews.items()}, indent=1)
        ask(CHAIR, PLAN_CHAIR.replace('{reviews}', anon) + f'\n\nPLAN:\n{plan}', 'chair',
            system=PLAN_SYSTEM, filename='plan_meta_review.md')
        manifest['verdicts'] = {letters[model]: reviews[model]['verdict'] for model in REVIEWERS}
    return manifest


def review_paper(args, out):
    tex = Path(args.tex).read_text(encoding='utf-8')
    guidelines = Path(args.guidelines).read_text(encoding='utf-8')
    data = '\n\n'.join(f'=== {Path(path).name} ===\n' + Path(path).read_text(encoding='utf-8') for path in args.data)
    paper = (f'GUIDELINES:\n{guidelines}\n\nTEXT-ONLY MANUSCRIPT LATEX SOURCE (no PDF/page images):\n{tex}')
    letters = {model: chr(ord('A') + index) for index, model in enumerate(REVIEWERS)}
    manifest = {'schema_version': 'text-review-2', 'reviewers': {letters[m]: m for m in REVIEWERS},
                'auditor': AUDITOR, 'chair': CHAIR, 'debate_rounds': args.debate_rounds,
                'tex_sha256': _hash(tex), 'guidelines_sha256': _hash(guidelines), 'data_sha256': _hash(data),
                'required_stages': [*[f'review_{letters[m]}' for m in REVIEWERS], 'audit',
                    *[f'debate{round_no}_{letters[m]}' for round_no in range(1, args.debate_rounds + 1)
                      for m in REVIEWERS], 'chair']}
    with review_session(args, out, manifest) as ask:
        review_task = REVIEW_TASK.replace('SCORES', SCORES_JSON) + '\n\n' + paper
        reviews = {model: ask(model, review_task, f'review_{letters[model]}', kind='review') for model in REVIEWERS}
        audit = ask(AUDITOR, AUDIT_TASK.replace('{data}', data) + '\n\n' + paper,
                    'audit', kind='audit', filename='data_audit.json')
        debate, transcript = {}, []

        def position(model):
            latest = {'review': reviews[model]}
            if model in debate:
                latest['latest_debate_response'] = debate[model]
            return json.dumps(latest, indent=1)

        for round_no in range(1, args.debate_rounds + 1):
            tasks = {model: DEBATE_TASK.replace('SCORES', SCORES_JSON).replace('{own}', position(model)).replace(
                '{others}', '\n\n'.join(f'Reviewer {letters[other]}:\n{position(other)}'
                                        for other in REVIEWERS if other != model)) + '\n\n' + paper
                for model in REVIEWERS}
            debate = {model: ask(model, tasks[model], f'debate{round_no}_{letters[model]}', kind='debate')
                      for model in REVIEWERS}
            transcript.append(debate)
        anon = json.dumps({f'Reviewer {letters[m]}': value for m, value in reviews.items()}, indent=1)
        full_debate = json.dumps([{f'Reviewer {letters[m]}': value for m, value in rnd.items()}
                                 for rnd in transcript], indent=1)
        chair_task = RUBRIC + '\n\n' + CHAIR_TASK.replace('{reviews}', anon).replace('{debate}', full_debate).replace(
            '{audit}', json.dumps(audit, indent=1)) + '\n\n' + paper
        ask(CHAIR, chair_task, 'chair', filename='meta_review.md')
        manifest['verdicts_after_debate'] = {letters[m]: debate.get(m, {}).get('updated_verdict') or reviews[m]['verdict']
                                            for m in REVIEWERS}
        manifest['rubric_scores'] = {letters[m]: {'initial': reviews[m]['scores'],
                                                'final': debate.get(m, {}).get('updated_scores', reviews[m]['scores'])}
                                     for m in REVIEWERS}
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', help='review a research plan instead of a manuscript; no debate')
    parser.add_argument('--tex')
    parser.add_argument('--pdf', help='unsupported legacy image-mode input; refused until separately qualified')
    parser.add_argument('--guidelines', required=True)
    parser.add_argument('--data', action='append')
    parser.add_argument('--out', required=True)
    parser.add_argument('--debate-rounds', type=int, default=0)
    parser.add_argument('--reasoning', choices=('none', 'minimal', 'low', 'medium', 'high'), default='high')
    paid_arguments(parser)
    args = parser.parse_args()
    if args.pdf:
        parser.error('image/PDF mode is not qualified; text-only review accepts --tex without --pdf')
    if not args.live:
        parser.error('paid research requires explicit --live and --authorization')
    if args.plan and (args.tex or args.data or args.debate_rounds):
        parser.error('--plan cannot be combined with manuscript data or debate rounds')
    if not args.plan and not (args.tex and args.data):
        parser.error('text-only paper review requires --tex and --data (or use --plan)')
    if args.debate_rounds < 0:
        parser.error('--debate-rounds must be nonnegative')
    out = Path(args.out)
    if out.exists():
        parser.error('output already exists; choose a fresh directory')
    out.mkdir(mode=0o700, parents=True)
    if args.plan:
        review_plan(args, out)
    else:
        review_paper(args, out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
