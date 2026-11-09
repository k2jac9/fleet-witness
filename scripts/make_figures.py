"""Report figures as SVG (stdlib only). Convert to PNG with any browser, e.g. headless Edge/Chrome:
  msedge --headless --screenshot=fig.png --window-size=1200,800 file:///.../fig.svg  (figure 2: 1200,520)

Usage: python scripts/make_figures.py OUT_DIR SWEEP_DIR[=Label] [SWEEP_DIR=Label ...]
Figure 1: capture rate vs colluder share per regime: a-priori curve plus observed points per model.
Figure 2: median output tokens (incl. hidden reasoning), honest vs colluding agents, on target cases.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fleet_witness.verify_institution import capture_probability  # noqa: E402

INK, INK2, GRID, SURFACE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
SERIES = ['#2a78d6', '#eb6834']  # validated categorical slots 1-2
FONT = 'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif"'
PANELS = [('direct', 'Direct majority (no kernel)', None), ('auditor-1of1', 'Single auditor 1-of-1', (1, 1)),
          ('committee-2of3', 'Committee 2-of-3', (3, 2)), ('committee-4of7', 'Committee 4-of-7', (7, 4)),
          ('unanimous-7of7', 'Unanimous 7-of-7', (7, 7)), ('hybrid-maj+4of7', 'Hybrid: majority + 4-of-7', None)]


def observed(sweep: Path):
    """{regime: {fraction: (captured, n)}} pooled over board conditions."""
    summary = json.loads((sweep / 'sweep-summary.json').read_text(encoding='utf-8'))
    out = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in summary['table']:
        for regime, g in row['regimes'].items():
            n = g['n_targets']
            out[regime][row['fraction']][0] += round(g['observed_capture'] * n)
            out[regime][row['fraction']][1] += n
    return out


def figure1(sweeps, agents=50):
    w, h, cols = 1200, 800, 3
    pw, ph, left, top = 330, 250, 70, 130
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
             f'<text x="{left}" y="38" {FONT} font-size="22" font-weight="600" fill="{INK}">'
             'Unsafe releases on target cases vs colluding share, by governance regime</text>',
             f'<text x="{left}" y="62" {FONT} font-size="14" fill="{INK2}">Points: observed capture rate '
             '(n = 24 target releases per point, visible + hidden board pooled). Dashed line: a-priori seat-capture '
             'probability, N = 50.</text>']
    data = [(label, observed(path)) for path, label in sweeps]
    for index, (regime, title, mk) in enumerate(PANELS):
        ox = left + (index % cols) * (pw + 50)
        oy = top + (index // cols) * (ph + 80)
        def X(f): return ox + f / 0.5 * pw
        def Y(p): return oy + ph - p * ph
        parts.append(f'<text x="{ox}" y="{oy - 12}" {FONT} font-size="15" font-weight="600" fill="{INK}">{title}</text>')
        for p in (0, 0.25, 0.5, 0.75, 1.0):
            parts.append(f'<line x1="{ox}" y1="{Y(p)}" x2="{ox + pw}" y2="{Y(p)}" stroke="{GRID}" stroke-width="1"/>')
            if index % cols == 0:
                parts.append(f'<text x="{ox - 8}" y="{Y(p) + 4}" {FONT} font-size="12" fill="{INK2}" '
                             f'text-anchor="end">{int(p * 100)}%</text>')
        for f in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
            parts.append(f'<text x="{X(f)}" y="{oy + ph + 18}" {FONT} font-size="12" fill="{INK2}" '
                         f'text-anchor="middle">{int(f * 100)}%</text>')
        if mk:
            m, k = mk
            pts = ' '.join(f'{X(f / 100):.1f},{Y(capture_probability(agents, round(agents * f / 100), m, k)):.1f}'
                           for f in range(0, 51))
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{INK2}" stroke-width="2" stroke-dasharray="5 4"/>')
        for s, (label, obs) in enumerate(data):
            offset = (s - (len(data) - 1) / 2) * 7
            for f, (captured, n) in sorted(obs[regime].items()):
                if n:
                    parts.append(f'<circle cx="{X(f) + offset:.1f}" cy="{Y(captured / n):.1f}" r="5.5" fill="{SERIES[s]}" '
                                 f'stroke="{SURFACE}" stroke-width="2"><title>{label} {int(f * 100)}%: '
                                 f'{captured}/{n}</title></circle>')
    parts.append(f'<text x="{w / 2}" y="{h - 14}" {FONT} font-size="13" fill="{INK2}" text-anchor="middle">'
                 'Colluding share of the swarm</text>')
    lx, y = left, 90
    legend = [('line', INK2, 'A-priori seat-capture probability')] + [('dot', SERIES[s], f'Observed: {label}')
                                                                       for s, (label, _) in enumerate(data)]
    for kind, color, text in legend:
        if kind == 'line':
            parts.append(f'<line x1="{lx}" y1="{y}" x2="{lx + 22}" y2="{y}" stroke="{color}" stroke-width="2" stroke-dasharray="5 4"/>')
        else:
            parts.append(f'<circle cx="{lx + 11}" cy="{y}" r="5.5" fill="{color}"/>')
        parts.append(f'<text x="{lx + 30}" y="{y + 4}" {FONT} font-size="13" fill="{INK}">{text}</text>')
        lx += 40 + 7.2 * len(text)
    parts.append('</svg>')
    return '\n'.join(parts)


def token_medians(sweep: Path):
    groups = defaultdict(list)
    for d in sorted(sweep.glob('f*')):
        truth = json.loads((d / 'truth.json').read_text(encoding='utf-8'))
        cell, targets = set(truth['colluders']), set(truth['targets'])
        for line in (d / 'events.jsonl').read_text(encoding='utf-8').splitlines():
            e = json.loads(line)
            answered = e.get('vote') in ('approve', 'deny') or e.get('outcome') in ('sign', 'refuse')
            if e['case_id'] not in targets or not answered or not e.get('output_tokens'):
                continue
            role = 'Colluding' if e['agent_id'] in cell else 'Honest'
            groups[(e['type'], role)].append(e['output_tokens'])
    return {key: (sorted(v)[len(v) // 2], len(v)) for key, v in groups.items()}


def figure2(sweeps):
    w, h, left, top, ph = 1200, 520, 90, 100, 320
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
             f'<text x="{left}" y="40" {FONT} font-size="22" font-weight="600" fill="{INK}">'
             'Collusion has a deliberation cost</text>',
             f'<text x="{left}" y="64" {FONT} font-size="14" fill="{INK2}">Median output tokens (including hidden '
             'reasoning) per response on target cases; n shown under each bar.</text>']
    groups = [(label, token_medians(path)) for path, label in sweeps]
    peak = max(m for _, med in groups for (m, _) in med.values())
    scale = ph / (peak * 1.15)
    slot = (w - left - 60) / (len(groups) * 2)
    bar = 46
    for g, (label, med) in enumerate(groups):
        for t, kind in enumerate(('vote', 'attestation')):
            cx = left + (g * 2 + t) * slot + slot / 2
            name = 'Reviewer votes' if kind == 'vote' else 'Committee audits'
            parts.append(f'<text x="{cx}" y="{top + ph + 46}" {FONT} font-size="14" fill="{INK}" text-anchor="middle">'
                         f'{name}</text>')
            parts.append(f'<text x="{cx}" y="{top + ph + 66}" {FONT} font-size="13" fill="{INK2}" '
                         f'text-anchor="middle">{label}</text>')
            for r, role in enumerate(('Honest', 'Colluding')):
                m, n = med.get((kind, role), (0, 0))
                x = cx - bar - 1 + r * (bar + 2)
                y = top + ph - m * scale
                parts.append(f'<path d="M{x},{top + ph} V{y + 4} q0,-4 4,-4 H{x + bar - 4} q4,0 4,4 V{top + ph} Z" '
                             f'fill="{SERIES[r]}"><title>{label} {name} {role}: median {m} (n={n})</title></path>')
                parts.append(f'<text x="{x + bar / 2}" y="{y - 8}" {FONT} font-size="13" fill="{INK}" '
                             f'text-anchor="middle">{m}</text>')
                parts.append(f'<text x="{x + bar / 2}" y="{top + ph + 18}" {FONT} font-size="11" fill="{INK2}" '
                             f'text-anchor="middle">n={n}</text>')
    parts.append(f'<line x1="{left}" y1="{top + ph}" x2="{w - 60}" y2="{top + ph}" stroke="{INK2}" stroke-width="1"/>')
    for i, role in enumerate(('Honest agents', 'Colluding agents')):
        parts.append(f'<rect x="{w - 300}" y="{24 + i * 22}" width="14" height="14" rx="3" fill="{SERIES[i]}"/>'
                     f'<text x="{w - 278}" y="{36 + i * 22}" {FONT} font-size="13" fill="{INK}">{role}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


if __name__ == '__main__':
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    sweeps = []
    for arg in sys.argv[2:]:
        path, _, label = arg.partition('=')
        sweeps.append((Path(path), label or Path(path).name))
    (out / 'figure1-capture.svg').write_text(figure1(sweeps), encoding='utf-8')
    (out / 'figure2-deliberation.svg').write_text(figure2(sweeps), encoding='utf-8')
    print('wrote', out / 'figure1-capture.svg', out / 'figure2-deliberation.svg')
