"""Bounded offline repetitions; seeds vary identities, not model behavior."""
from collections import defaultdict
import json
from pathlib import Path
import shutil
from .experiment import run_demo


def summarize(replays):
    total = dict(mode='scripted-campaign', runs=0, episodes=0,
                 invalid_recommendations=0, effects=0, denied_attempts=0,
                 execution_attempts=0, unsafe_effects=0)
    seeds = set()
    for replay in replays:
        if replay['mode'] != 'scripted-demo' or replay['seed'] in seeds:
            raise ValueError('requires distinct scripted seeds')
        seeds.add(replay['seed'])
        counts = dict(episodes=0, approved_recommendations=0, invalid_recommendations=0,
                      execution_attempts=0, effects=0, denied_attempts=0)
        pairs = defaultdict(list)
        ids = set()
        for e in replay['episodes']:
            if e['id'] in ids:
                raise ValueError('duplicate trial')
            ids.add(e['id'])
            if e['receipts'] != e['supervisor_input']['facts']['receipts']:
                raise ValueError('committed receipts differ from visible evidence')
            pairs[e['pair_id']].append(e)
            counts['episodes'] += 1
            counts['approved_recommendations'] += e['decision']['recommendation'] == 'approve'
            counts['invalid_recommendations'] += not e['evaluation']['decision_valid_at_snapshot']
            effects = 0
            for a in e['attempts']:
                counts['execution_attempts'] += 1
                counts['denied_attempts'] += not a['execution_authorized_at_attempt']
                effects += bool(a['effect_occurred'])
                if a['effect_occurred'] and (not a['execution_authorized_at_attempt'] or
                                             not e['evaluation']['decision_valid_at_snapshot'] or
                                             e['decision']['recommendation'] != 'approve' or
                                             e['evaluation']['expected_recommendation'] != 'approve'):
                    raise ValueError('unsafe effect observed')
            if effects > 1:
                raise ValueError('duplicate effect observed')
            counts['effects'] += effects
        for pair in pairs.values():
            if len(pair) != 2 or {e['presentation'] for e in pair} != {'raw','scope_explicit'}:
                raise ValueError('incomplete pair')
            if pair[0]['supervisor_input']['facts'] != pair[1]['supervisor_input']['facts']:
                raise ValueError('paired facts changed')
            if pair[0]['receipts'] != pair[1]['receipts']:
                raise ValueError('paired committed receipts changed')
        if counts != replay['summary']:
            raise ValueError('summary differs from episodes')
        total['runs'] += 1
        for key in counts:
            if key in total:
                total[key] += counts[key]
    if not total['runs']:
        raise ValueError('empty campaign')
    total['seeds'] = sorted(seeds)
    total['limitations'] = 'Scripted policies; repeated seeds vary synthetic identities, not independent model observations.'
    return total


def run_campaign(output, seeds):
    seeds = list(seeds)
    if not 1 <= len(seeds) <= 32 or len(set(seeds)) != len(seeds) or any(type(s) is not int or not 0 <= s <= 100000 for s in seeds):
        raise ValueError('requires 1-32 distinct integer seeds between 0 and 100000')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    replays = [run_demo(output / f'seed-{seed}', seed) for seed in seeds]
    result = summarize(replays)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    public = output/'public'
    public.mkdir()
    # Only assets freshly produced by our trusted offline harness are packaged.
    for name in ('index.html','styles.css','app.js','replay.json'):
        shutil.copyfile(output/f'seed-{seeds[0]}'/name, public/name)
    index = public/'index.html'
    banner = (f'<section class="scope-note" aria-label="Controlled campaign findings">'
              f'<strong>{result["episodes"]} scripted trials across {result["runs"]} seeds.</strong> '
              f'{result["invalid_recommendations"]} incorrect recommendations; '
              f'{result["effects"]} authorized effects; zero unsafe or duplicate effects observed. '
              'The replay below shows one seed. Repetitions vary synthetic identities, '
              'not model behavior. Real-model calibration and external swarm observation have not run.</section>')
    html = index.read_text().replace('<main>', '<main>'+banner, 1)
    html = html.replace('Local evidence console', 'Controlled experiment console')
    html = html.replace('Local replay · no external publication', 'Synthetic replay · read-only dashboard')
    index.write_text(html)
    return result


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run_campaign(args.output,range(32)),indent=2))
