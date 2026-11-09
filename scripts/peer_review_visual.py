"""Standalone multi-model AI peer review of the LaTeX report, with rendered PDF pages (OpenRouter).

NOT part of the gated paid workflow in fleet_witness/swarm (operator authorizations, one request
at a time). It was run once, at the request of a team member spending their own OpenRouter key,
because that gate is POSIX-only and its 30 s / 256 KB request limits cannot carry page images or
high-effort reviews. Never runs by default; requires an explicit --max-usd and OPENROUTER_API_KEY.

Each reviewer receives: the Apart hackathon guidelines (rubric, submission requirements), the
LaTeX source, and a PNG image of every page of the compiled PDF. Scores: Apart's three
dimensions plus two added criteria, formality & visual presentation, and human readability.

Pipeline: independent reviews (parallel) and a data audit, N debate rounds (parallel), chair.
Usage:
  python scripts/peer_review_visual.py --tex docs/report/latex/report.tex \
      --pdf docs/report/latex/report.pdf --guidelines GUIDELINES.md \
      --data docs/report/review-data.md --data docs/report/CORRECTIONS-2026-11-09.md \
      --out docs/report/reviews/round-3 --max-usd 10
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import urllib.error
import urllib.request

URL = 'https://openrouter.ai/api/v1/chat/completions'
REVIEWERS = ['openai/gpt-6.1-sol', 'google/gemini-4-argon', 'meta/muse-wonder', 'xiaomi/mimo-v2.6-pro']
AUDITOR = 'google/gemini-4-argon'
CHAIR = 'openai/gpt-6.1-sol-pro'

SYSTEM = (
    'You are an expert, rigorous peer reviewer for an AI-safety research venue (multi-agent oversight, formal '
    'methods, empirical ML). You review BOTH substance and form. Substance: soundness of methods, whether claims '
    'are supported by the evidence, statistics, confounds, overclaiming, reproducibility, positioning against prior '
    'work, and compliance with the hackathon requirements. Form: you are given images of every page of the compiled '
    'PDF, so judge it as a typeset research paper: formality and register of the writing, structure and headings, '
    'capitalization and terminology consistency, citation style and reference formatting, figure and table quality '
    '(legibility, labels, captions, colour, placement), typography and layout, and how easily a human reader can '
    'follow it. Technical jargon is acceptable when needed; needless convolution is not. Cite the page number, '
    'section, figure or table for every point. If something seems missing, treat it as a request for clarification. '
    'Do not invent references; if you suggest related work, say it should be verified.'
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
FORMALITY & VISUAL PRESENTATION (judge from the page images): is this a formal, professional research paper? Consider
 register and tone, heading hierarchy and capitalization consistency, citation and reference style, figure legibility
 and labelling, table design, captions, typography, whitespace and layout, and adherence to the official template
 structure. 1 unprofessional; 2 several formatting or style problems; 3 acceptable with noticeable inconsistencies;
 4 polished with minor issues; 5 publication-quality typesetting and style.
READABILITY (human perspective): can a technically literate reader understand it on one pass? Penalize convoluted
 sentences, needless hedging chains, undefined abbreviations, inconsistent terminology, dense paragraphs and
 over-qualified prose; domain jargon is acceptable. 1 very hard to read; 2 often convoluted; 3 readable with effort;
 4 easy to follow; 5 exceptionally clear and fluent.
Judge it as a hackathon report: reward a promising, honestly backed idea; penalize overclaiming and any breach of
the submission requirements (8-page limit excluding references and appendices, 150-250 word abstract, required
Limitations and Dual-Use / Ethical appendix, authors and affiliations)."""

PLAN_SYSTEM = (
    'You are an expert, rigorous reviewer of research plans for an AI-safety venue (multi-agent oversight, '
    'empirical ML, formal methods). You review a plan BEFORE it is executed, so your job is to make the eventual '
    'study better: find design flaws, confounds, invalid measurements, missing controls, unrealistic scope or '
    'timing, and wasted effort, and propose concrete, feasible fixes. Be specific and constructive. Do not invent '
    'references; if you suggest related work, say it should be verified.'
)

PLAN_TASK = """You are reviewing a research PLAN for a hackathon project (official judging rubric and requirements are
in the guidelines below; the plan's current paper is summarized inside the plan). The team has about 3 hours,
two inexpensive models (DeepSeek v4 Flash, gpt-oss-20b) and a budget of about $15.
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

Review the manuscript (LaTeX source below, and the attached images of every compiled PDF page, in order).
Reply with ONLY a JSON object:
{"summary": "<3 sentences>",
 "scores": SCORES,
 "score_rationale": {"impact_innovation": "...", "execution": "...", "presentation": "...", "formality_aesthetics": "...", "readability": "..."},
 "strengths": ["..."],
 "concerns": [{"id": "C1", "severity": "critical|major|minor",
               "category": "<validity|statistics|overclaiming|confound|reproducibility|related-work|requirements|formality|figures|tables|headings|capitalization|citations|typography|layout|readability>",
               "location": "<page / section / figure / table>", "issue": "...", "why_it_matters": "...",
               "suggested_fix": "<concrete, feasible within a few hours if possible>"}],
 "readability_examples": [{"location": "...", "original": "<short quote>", "suggested_rewrite": "..."}],
 "verdict": "accept|weak accept|borderline|weak reject|reject",
 "confidence": 1-5}"""

DEBATE_TASK = """You previously reviewed this manuscript (LaTeX source and page images are attached again). Below are
your position and the other anonymous reviewers' positions. For EACH other reviewer's concern decide "agree",
"disagree" or "factually_wrong" (it misreads the paper or the page images), with a one-sentence reason grounded in the
manuscript. Then revise your own concerns. Reply with ONLY a JSON object:
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
unsupported numbers, arithmetic errors, wrong denominators and statistical misstatements, including numbers read off
the figures in the page images. Reply with ONLY a JSON object:
{"checked_claims": <int>, "issues": [{"location": "...", "claim": "...", "data_says": "...",
  "severity": "critical|major|minor"}], "notes": "..."}

RESULT DATA:
{data}"""

CHAIR_TASK = """You chair the review. Page images of the PDF are attached so you can calibrate the formality and
visual-presentation judgements yourself. Consolidate the independent reviews, the debate and the data audit into a
single ranked list of concerns. Merge duplicates. For each give consensus (how many reviewers raised or agreed),
validity (valid / partially valid / invalid, using the debate's factually_wrong judgements), severity, and the single
most effective fix the authors can make in a few hours, or "future work".
Reply in Markdown with sections: Rubric scores (table of each reviewer's initial and final scores on all five
dimensions, plus your own calibrated score with a one-line justification per dimension), Overall assessment (with
verdict distribution), Substance concerns (ranked table: #, concern, consensus, validity, severity, action, effort),
Formality and visual presentation (headings, capitalization, citations, figures, tables, typography, layout),
Readability (with the most useful concrete rewrites), Requirements compliance (page limit, abstract length, required
appendix, authors and affiliations), Data-audit issues, Points reviewers got wrong, and Bottom line.

INDEPENDENT REVIEWS:
{reviews}

DEBATE:
{debate}

DATA AUDIT:
{audit}"""


class Budget:
    def __init__(self, cap):
        self.cap, self.spent, self.lock = cap, 0.0, threading.Lock()

    def add(self, usd):
        with self.lock:
            self.spent += usd
            if self.spent > self.cap:
                raise RuntimeError(f'spend cap exceeded: ${self.spent:.4f} > ${self.cap}')


def extract_json(text):
    match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text or '', re.S) or re.search(r'(\{.*\})', text or '', re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {'unparsed': (text or '')[:20000]}


def render_pages(pdf, dpi):
    import pymupdf  # optional dependency for this script only
    doc = pymupdf.open(pdf)
    return [base64.b64encode(page.get_pixmap(dpi=dpi).tobytes('png')).decode() for page in doc]


def content(text, images):
    parts = [{'type': 'text', 'text': text}]
    for i, image in enumerate(images, 1):
        parts.append({'type': 'text', 'text': f'[PDF page image {i} of {len(images)}; page 1 is the title page]'})
        parts.append({'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{image}'}})
    return parts


def call(model, user, budget, log, label, reasoning, max_tokens, system=None):
    body = {'model': model, 'temperature': 0.3, 'max_tokens': max_tokens,
            'reasoning': {'effort': reasoning}, 'usage': {'include': True},
            'messages': [{'role': 'system', 'content': system or SYSTEM}, {'role': 'user', 'content': user}]}
    data = json.dumps(body).encode()
    headers = {'Authorization': f"Bearer {os.environ['OPENROUTER_API_KEY']}", 'Content-Type': 'application/json',
               'X-Title': 'fleet-witness peer review'}
    started = time.monotonic()
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(URL, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(request, timeout=1200) as response:
                payload = json.loads(response.read())
            break
        except urllib.error.HTTPError as error:
            detail = error.read()[:300].decode('utf-8', 'replace')
            log(label, model, attempt, f'HTTP {error.code}: {detail}', 0.0, None)
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError) as error:
            log(label, model, attempt, f'network: {error}', 0.0, None)
            if attempt == 3:
                raise
        time.sleep(5 * attempt)
    choice = payload['choices'][0]
    usage = payload.get('usage') or {}
    cost = float(usage.get('cost') or 0.0)
    budget.add(cost)
    log(label, model, attempt, choice.get('finish_reason'), cost, usage, round(time.monotonic() - started, 1))
    return choice['message'].get('content') or ''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', help='review a research plan (Markdown) instead of a paper; fast, no debate')
    parser.add_argument('--tex')
    parser.add_argument('--pdf')
    parser.add_argument('--guidelines', required=True)
    parser.add_argument('--data', action='append')
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-usd', type=float, required=True)
    parser.add_argument('--debate-rounds', type=int, default=0,
                        help='0 (default): independent reviews + chair. Past rounds showed debate rarely moved '
                             'scores; 1 is available when reviewers disagree sharply.')
    parser.add_argument('--reasoning', default='high')
    parser.add_argument('--dpi', type=int, default=110)
    parser.add_argument('--max-tokens', type=int, default=16000)
    args = parser.parse_args()
    if 'OPENROUTER_API_KEY' not in os.environ:
        parser.error('OPENROUTER_API_KEY is not set')
    out = Path(args.out)
    if out.exists():
        parser.error('output already exists; choose a fresh directory')
    if args.plan:
        out.mkdir(parents=True)
        return review_plan(args, out)
    if not (args.tex and args.pdf and args.data):
        parser.error('paper review needs --tex, --pdf and --data (or use --plan)')
    out.mkdir(parents=True)

    tex = Path(args.tex).read_text(encoding='utf-8')
    guidelines = Path(args.guidelines).read_text(encoding='utf-8')
    data = '\n\n'.join(f'=== {Path(p).name} ===\n' + Path(p).read_text(encoding='utf-8') for p in args.data)
    images = render_pages(args.pdf, args.dpi)
    paper = (f'HACKATHON GUIDELINES (official rubric and submission requirements):\n{guidelines}\n\n'
             f'MANUSCRIPT LATEX SOURCE:\n{tex}')
    budget = Budget(args.max_usd)
    lock, calls = threading.Lock(), []

    def log(label, model, attempt, status, cost, usage, seconds=None):
        entry = {'label': label, 'model': model, 'attempt': attempt, 'status': status, 'cost_usd': cost,
                 'seconds': seconds, 'prompt_tokens': (usage or {}).get('prompt_tokens'),
                 'completion_tokens': (usage or {}).get('completion_tokens')}
        with lock:
            calls.append(entry)
        print(f"  {label:<12} {model:<28} {status} ${cost:.4f} {seconds or ''}s", flush=True)

    def ask(model, text, label, with_images=True):
        return call(model, content(text, images if with_images else []), budget, log, label,
                    args.reasoning, args.max_tokens)

    letters = {m: chr(ord('A') + i) for i, m in enumerate(REVIEWERS)}
    manifest = {'schema_version': 'visual-review-1', 'gated_workflow': False,
                'note': 'Standalone run outside the authorized paid workflow; see script docstring.',
                'reviewers': {letters[m]: m for m in REVIEWERS}, 'auditor': AUDITOR, 'chair': CHAIR,
                'reasoning': args.reasoning, 'debate_rounds': args.debate_rounds, 'page_images': len(images),
                'image_dpi': args.dpi,
                'tex_sha256': hashlib.sha256(tex.encode()).hexdigest(),
                'pdf_sha256': hashlib.sha256(Path(args.pdf).read_bytes()).hexdigest(),
                'guidelines_sha256': hashlib.sha256(guidelines.encode()).hexdigest(),
                'data_sha256': hashlib.sha256(data.encode()).hexdigest(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'status': 'started'}
    started = time.monotonic()
    try:
        review_task = REVIEW_TASK.replace('SCORES', SCORES_JSON) + '\n\n' + paper
        print('Independent reviews + data audit (parallel) ...', flush=True)
        with ThreadPoolExecutor(len(REVIEWERS) + 1) as pool:
            futures = {m: pool.submit(ask, m, review_task, f'review_{letters[m]}') for m in REVIEWERS}
            audit_future = pool.submit(ask, AUDITOR, AUDIT_TASK.replace('{data}', data) + '\n\n' + paper, 'audit')
            reviews = {m: extract_json(f.result()) for m, f in futures.items()}
            audit = extract_json(audit_future.result())
        for m in REVIEWERS:
            (out / f'review_{letters[m]}.json').write_text(json.dumps({'model': m, **reviews[m]}, indent=2), encoding='utf-8')
        (out / 'data_audit.json').write_text(json.dumps({'model': AUDITOR, **audit}, indent=2), encoding='utf-8')

        debate, transcript = {}, []

        def position(m):
            latest = {'review': reviews[m]}
            if m in debate:
                latest['latest_debate_response'] = debate[m]
            return json.dumps(latest, indent=1)

        for round_no in range(1, args.debate_rounds + 1):
            print(f'Debate round {round_no} (parallel) ...', flush=True)
            tasks = {m: DEBATE_TASK.replace('SCORES', SCORES_JSON).replace('{own}', position(m)).replace(
                '{others}', '\n\n'.join(f'Reviewer {letters[o]}:\n{position(o)}' for o in REVIEWERS if o != m))
                + '\n\n' + paper for m in REVIEWERS}
            with ThreadPoolExecutor(len(REVIEWERS)) as pool:
                futures = {m: pool.submit(ask, m, tasks[m], f'debate{round_no}_{letters[m]}') for m in REVIEWERS}
                new = {m: extract_json(f.result()) for m, f in futures.items()}
            for m in REVIEWERS:
                (out / f'debate{round_no}_{letters[m]}.json').write_text(json.dumps({'model': m, **new[m]}, indent=2),
                                                                      encoding='utf-8')
            debate = new
            transcript.append(new)

        print('Chair ...', flush=True)
        anon = json.dumps({f'Reviewer {letters[m]}': v for m, v in reviews.items()}, indent=1)
        full_debate = json.dumps([{f'Reviewer {letters[m]}': v for m, v in rnd.items()} for rnd in transcript], indent=1)
        chair_task = RUBRIC + '\n\n' + CHAIR_TASK.replace('{reviews}', anon).replace('{debate}', full_debate).replace(
            '{audit}', json.dumps(audit, indent=1))
        meta = ask(CHAIR, chair_task, 'chair')
        (out / 'meta_review.md').write_text(meta, encoding='utf-8')
        manifest['verdicts_after_debate'] = {letters[m]: debate.get(m, {}).get('updated_verdict') or reviews[m].get('verdict')
                                             for m in REVIEWERS}
        manifest['rubric_scores'] = {letters[m]: {'initial': reviews[m].get('scores'),
                                                  'final': debate.get(m, {}).get('updated_scores')} for m in REVIEWERS}
        manifest['status'] = 'completed'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {str(error)[:300]}')
        raise
    finally:
        manifest.update(cost_usd=round(budget.spent, 6), wall_seconds=round(time.monotonic() - started, 1), calls=calls)
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(f'Done ({manifest["status"]}): ${budget.spent:.4f}, {manifest["wall_seconds"]}s -> {out}', flush=True)


def review_plan(args, out):
    """Fast plan review: parallel independent reviews, then an action-first chair. No debate."""
    plan = Path(args.plan).read_text(encoding='utf-8')
    guidelines = Path(args.guidelines).read_text(encoding='utf-8')
    budget, lock, calls = Budget(args.max_usd), threading.Lock(), []
    letters = {m: chr(ord('A') + i) for i, m in enumerate(REVIEWERS)}

    def log(label, model, attempt, status, cost, usage, seconds=None):
        with lock:
            calls.append({'label': label, 'model': model, 'attempt': attempt, 'status': status, 'cost_usd': cost,
                          'seconds': seconds})
        print(f"  {label:<12} {model:<28} {status} ${cost:.4f} {seconds or ''}s", flush=True)

    task = PLAN_TASK + f'\n\nGUIDELINES:\n{guidelines}\n\nPLAN:\n{plan}'
    started = time.monotonic()
    print('Plan review: independent reviews (parallel) ...', flush=True)
    with ThreadPoolExecutor(len(REVIEWERS)) as pool:
        futures = {m: pool.submit(call, m, task, budget, log, f'plan_{letters[m]}', args.reasoning,
                                  args.max_tokens, PLAN_SYSTEM) for m in REVIEWERS}
        reviews = {m: extract_json(f.result()) for m, f in futures.items()}
    for m in REVIEWERS:
        (out / f'plan_review_{letters[m]}.json').write_text(json.dumps({'model': m, **reviews[m]}, indent=2),
                                                            encoding='utf-8')
    print('Chair ...', flush=True)
    anon = json.dumps({f'Reviewer {letters[m]}': v for m, v in reviews.items()}, indent=1)
    meta = call(CHAIR, PLAN_CHAIR.replace('{reviews}', anon) + f'\n\nPLAN:\n{plan}', budget, log, 'chair',
                args.reasoning, args.max_tokens, PLAN_SYSTEM)
    (out / 'plan_meta_review.md').write_text(meta, encoding='utf-8')
    manifest = {'schema_version': 'plan-review-1', 'gated_workflow': False,
                'reviewers': {letters[m]: m for m in REVIEWERS}, 'chair': CHAIR, 'debate_rounds': 0,
                'plan_sha256': hashlib.sha256(plan.encode()).hexdigest(),
                'verdicts': {letters[m]: reviews[m].get('verdict') for m in REVIEWERS},
                'cost_usd': round(budget.spent, 6), 'wall_seconds': round(time.monotonic() - started, 1),
                'calls': calls}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Done: ${budget.spent:.4f}, {manifest["wall_seconds"]}s -> {out}', flush=True)


if __name__ == '__main__':
    main()
