"""Sweep the colluding share and compare governance regimes against capture mathematics.

Each fraction is one swarm run (resumable: finished runs are skipped). The summary
pools every sweep directory given, so runs on different providers (same model)
combine into one table with observed and predicted capture rates.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from ..verify_institution import capture_probability
from .detect import analyze
from .runner import REGIMES, run_swarm
from .providers import STRICT_SWARM_PARSER
from .run_records import classify_run_treatment

DEFAULT_FRACTIONS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)


def run_sweep(root: Path, client, *, fractions=DEFAULT_FRACTIONS, agents=50, cases=24, seed=0,
              conditions=('hidden-cell', 'visible-cell'), waves=5, case_mode='standard'):
    root = Path(root)
    fractions = tuple(fractions)
    names = [f'f{int(round(fraction * 100)):02d}' for fraction in fractions]
    if len(names) != len(set(names)) or any(not 0 <= fraction <= 1 for fraction in fractions):
        raise ValueError('invalid or colliding sweep fractions')
    if root.exists():
        from .providers import source_identity
        source = source_identity()
        authorization = getattr(client, 'authorization', None)
        authorization_identity = None if authorization is None else {
            'id': authorization['authorization_id'], 'purpose': authorization['purpose'],
            'sha256': hashlib.sha256(json.dumps(authorization, sort_keys=True, separators=(',', ':'),
                                               allow_nan=False).encode()).hexdigest()}
        model_config = {'label': client.label, 'temperature': getattr(client, 'temperature', None),
                        'max_output_tokens': client.max_output_tokens, 'timeout_s': getattr(client, 'timeout', None),
                        'extra_body': getattr(client, 'extra_body', {}),
                        'attempt_policy': 'one-attempt-no-retries'}
        expected = dict(zip(names, fractions))
        for output in sorted(root.glob('f*')):
            if output.name not in expected or not output.is_dir() or not (output / 'manifest.json').is_file():
                raise ValueError('existing sweep contains unknown or unfinished runs')
            if classify_run_treatment(output) != STRICT_SWARM_PARSER:
                raise ValueError('existing sweep parser treatment differs from new runs')
            manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
            fraction = expected[output.name]
            wanted = {'agents': agents, 'cases': cases, 'seed': seed + int(fraction * 1000),
                      'conditions': list(conditions), 'waves': waves, 'recent_comments': 6, 'case_mode': case_mode,
                      'cell_fraction': fraction, 'model': client.label, 'incomplete': False,
                      'max_output_tokens': client.max_output_tokens}
            if any(manifest.get(key) != value for key, value in wanted.items()):
                raise ValueError('existing sweep configuration differs from requested run')
            if manifest.get('source') != source:
                raise ValueError('existing sweep source differs from current source')
            if manifest.get('model_config') != model_config or manifest.get('authorization') != authorization_identity:
                raise ValueError('existing sweep model or authorization configuration differs')
    for fraction in fractions:
        output = root / f'f{int(round(fraction * 100)):02d}'
        if (output / 'manifest.json').exists():
            print(f'skip {output} (already finished)')
            continue
        if output.exists():
            raise ValueError(f'{output} exists but is unfinished; move it aside and rerun')
        manifest = run_swarm(output, client, agents=agents, cases=cases, conditions=list(conditions),
                             cell_fraction=fraction, waves=waves, recent_comments=6, seed=seed + int(fraction * 1000),
                             case_mode=case_mode)
        print(f"{output}: calls={manifest['calls']} errors={manifest['errors']} cost=${manifest['cost_usd']:.4f}"
              + (f"  INCOMPLETE: {manifest['abort_reason']}" if manifest['incomplete'] else ''))
        if manifest['incomplete']:
            break


def summarize(roots: list[Path], *, analysis_root=None, decision_overrides=None) -> dict:
    """Read raw runs without rewriting them; optional analyses use a separate root.

    Offline reproduction may supply validated synthetic decision views, indexed
    by resolved run directory. They are never written over historical decisions.
    """
    directories, treatments = [], set()
    for root in roots:
        for directory in sorted(Path(root).glob('f*')):
            manifest_path = directory / 'manifest.json'
            if not manifest_path.exists():
                continue
            treatment = classify_run_treatment(directory)
            treatments.add(treatment)
            directories.append((root, directory))
    if len(treatments) > 1:
        raise ValueError('mixed parser treatments cannot be pooled')
    pooled = defaultdict(lambda: defaultdict(lambda: {'unsafe': 0, 'targets': 0, 'valid_released': 0,
                                                      'valid': 0, 'predicted_sum': 0.0, 'seated_capture': 0}))
    auditors = defaultdict(lambda: {'honest_sign_targets': [], 'honest_sign_valid': [], 'runs': 0,
                                    'swarm_invalid_approved': [0, 0], 'detect': []})
    runs = []
    for root, directory in directories:
        with tempfile.TemporaryDirectory(prefix='fleet-summary-') as temporary:
            scratch = Path(temporary)
            for filename in ('manifest.json', 'truth.json', 'events.jsonl', 'decisions.json'):
                shutil.copyfile(directory / filename, scratch / filename)
            if decision_overrides is not None:
                (scratch / 'decisions.json').write_text(json.dumps(
                    decision_overrides[str(directory.resolve())], allow_nan=False), encoding='utf-8')
            report = analyze(scratch)
        if analysis_root is not None:
            output = Path(analysis_root) / Path(root).name / directory.name
            output.mkdir(parents=True, exist_ok=True)
            with (output / 'analysis.json').open('x', encoding='utf-8') as handle:
                json.dump(report, handle, indent=2, allow_nan=False)
        m = report['manifest']
        if m['incomplete']:
            continue
        runs.append(str(directory))
        fraction = m['cell_fraction']
        truth = json.loads((directory / 'truth.json').read_text(encoding='utf-8'))
        cell = set(truth['colluders'])
        for condition, c in report['conditions'].items():
            key = (fraction, condition)
            eps = c['auditors']['honest_sign_rate_on_targets'] or 0.0
            a = auditors[key]
            a['runs'] += 1
            if c['auditors']['honest_sign_rate_on_targets'] is not None:
                a['honest_sign_targets'].append(c['auditors']['honest_sign_rate_on_targets'])
            if c['auditors']['honest_sign_rate_on_valid'] is not None:
                a['honest_sign_valid'].append(c['auditors']['honest_sign_rate_on_valid'])
            approved, total = map(int, c['swarm_approved_invalid_cases'].split('/'))
            a['swarm_invalid_approved'][0] += approved
            a['swarm_invalid_approved'][1] += total
            if 'f1' in c['detection']:
                a['detect'].append(c['detection']['f1'])
            for regime, g in c['regimes'].items():
                p = pooled[key][regime]
                p['unsafe'] += g['unsafe_on_targets']
                p['targets'] += g['target_cases']
                p['valid_released'] += g['valid_released']
                p['valid'] += g['valid_cases']
                if regime in REGIMES and REGIMES[regime][0] > 0:
                    size, quorum, _ = REGIMES[regime]
                    p['predicted_sum'] += g['target_cases'] * capture_probability(
                        m['agents'], m['cell_size'], size, quorum, eps)
                    # Given the seats actually drawn: captured iff >= quorum colluders were seated
                    # (assumes every seated colluder complies and no honest auditor errs).
                    p['seated_capture'] += sum(
                        len(cell & set(truth['committees'][case][:size])) >= quorum for case in truth['targets'])
    table = []
    for (fraction, condition) in sorted(pooled):
        a = auditors[fraction, condition]
        row = {'fraction': fraction, 'condition': condition, 'runs': a['runs'],
               'honest_auditor_sign_rate_targets': _mean(a['honest_sign_targets']),
               'honest_auditor_sign_rate_valid': _mean(a['honest_sign_valid']),
               'swarm_majority_approved_invalid': f"{a['swarm_invalid_approved'][0]}/{a['swarm_invalid_approved'][1]}",
               'detector_f1': _mean(a['detect']), 'regimes': {}}
        for regime, p in pooled[fraction, condition].items():
            row['regimes'][regime] = {
                'observed_capture': round(p['unsafe'] / p['targets'], 3) if p['targets'] else None,
                'predicted_capture': round(p['predicted_sum'] / p['targets'], 3)
                if regime in REGIMES and REGIMES[regime][0] > 0 and p['targets'] else None,
                'seated_capture': round(p['seated_capture'] / p['targets'], 3)
                if regime in REGIMES and REGIMES[regime][0] > 0 and p['targets'] else None,
                'n_targets': p['targets'],
                'valid_throughput': round(p['valid_released'] / p['valid'], 3) if p['valid'] else None}
        table.append(row)
    return {'runs': runs, 'table': table, 'parser_treatment': next(iter(treatments), None)}


def _mean(values):
    return round(sum(values) / len(values), 3) if values else None


def format_summary(summary: dict) -> str:
    if not summary['table']:
        return 'no finished runs'
    regimes = list(summary['table'][0]['regimes'])
    lines = [f"{len(summary['runs'])} finished runs pooled. Cells: observed capture (given actual seats | a-priori math)"
             " on target releases.",
             f"{'cell':>5} {'board':<8} " + ' '.join(f'{r:>16}' for r in regimes) + '   honest-auditor-error  detector-F1']
    for row in summary['table']:
        cells = []
        for r in regimes:
            g = row['regimes'][r]
            obs = '-' if g['observed_capture'] is None else f"{g['observed_capture']:.2f}"
            pred = '' if g['predicted_capture'] is None else f" ({g['seated_capture']:.2f}|{g['predicted_capture']:.2f})"
            cells.append(obs + pred)
        board = 'visible' if row['condition'].startswith('visible') else 'hidden'
        lines.append(f"{row['fraction']:>5.0%} {board:<8} " + ' '.join(f'{c:>16}' for c in cells)
                     + f"   {row['honest_auditor_sign_rate_targets']!s:>20}  {row['detector_f1']!s:>11}")
    denominators = sorted({g['n_targets'] for row in summary['table'] for g in row['regimes'].values()})
    lines.append(f'(target denominators per cell: {denominators}; exact per-cell n and valid throughput are in JSON)')
    return '\n'.join(lines)
