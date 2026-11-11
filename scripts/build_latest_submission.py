"""Prepare latest HTML, or package the separately rendered and inspected PDF.

Usage: python -m scripts.build_latest_submission --prepare | --package
No network access, PDF renderer, provider calls or directory-wide archiving.
"""
import argparse
import hashlib
import html
import io
import json
import re
from pathlib import Path, PurePosixPath
import zipfile

from scripts.report_to_pdf import convert

ROOT = Path(__file__).resolve().parents[1]
TITLE = ('Verify the Institution, Not the Agents: A Bounded-Verified Separation-of-Powers '
         'Kernel Stress-Tested Against Colluding LLM Swarms')
MEMBERS = {
    'latest.pdf': 'docs/report/latest.pdf',
    'latest.md': 'docs/report/latest.md',
    'latest.html': 'docs/report/latest.html',
    'latest-figures/paired-pilot.svg': 'docs/report/latest-figures/paired-pilot.svg',
    'latest.references.json': 'docs/report/latest.references.json',
    'latest.provenance.json': 'docs/report/latest.provenance.json',
    'paired-pilot-2026-11-09.json': 'data/paired-pilot-2026-11-09.json',
    'abstract.txt': 'docs/submission/latest/abstract.txt',
    'metadata.json': 'docs/submission/latest/metadata.json',
    'SUBMISSION.md': 'docs/submission/latest/SUBMISSION.md',
    'EVIDENCE.md': 'docs/submission/latest/EVIDENCE.md',
    'DEMO.md': 'docs/submission/latest/DEMO.md',
    'LICENSE': 'LICENSE',
    'fleet-witness-cover.png': 'docs/assets/fleet-witness-cover.png',
    'fleet-witness-viewer.png': 'docs/assets/fleet-witness-viewer.png',
    'verify_submission.py': 'scripts/verify_submission.py',
}
CSS = '''
@page { size: Letter; margin: .68in .76in .72in;
  @bottom-left { content: "FLEET WITNESS  /  SWARM ALIGNMENT 2026";
    font: 7pt Arial; color: #566577; }
  @bottom-right { content: counter(page); font: 8pt Arial; color: #566577; }
}
* { box-sizing: border-box; }
body { font: 10.2pt/1.4 Arial, Helvetica, sans-serif; color: #172536;
  max-width: 7in; margin: 0 auto; }
h1 { font-size: 20pt; line-height: 1.15; letter-spacing: -.4pt; color: #112e46;
  border-top: 5pt solid #167b7e; padding-top: 12pt; margin: 0 0 14pt; }
h2 { font-size: 12.6pt; color: #125b64; border-bottom: .6pt solid #cbdde1;
  padding-bottom: 3pt; margin: 14pt 0 6pt; break-after: avoid; }
h3 { font-size: 10.8pt; margin: 10pt 0 5pt; break-after: avoid; }
p { margin: 5pt 0; orphans: 3; widows: 3; }
a { color: #185b86; text-decoration: none; overflow-wrap: anywhere; }
code { font: 8.8pt/1.35 monospace; overflow-wrap: anywhere; }
table { width: 100%; border-collapse: collapse; margin: 9pt 0; font-size: 8.9pt;
  break-inside: avoid; }
th,td { border-bottom: .5pt solid #cbd8e2; padding: 5pt; vertical-align: top; }
th { background: #eaf1f5; color: #183d56; text-align: left; }
.num { text-align: right; }
img { display: block; width: 100%; margin: 9pt auto 4pt; break-inside: avoid; }
figure { margin: 0; break-inside: avoid; }
.caption { display: block; font-size: 8.7pt; line-height: 1.35; color: #40546a;
  margin-bottom: 9pt; }
ol,ul { padding-left: 18pt; } li { margin: 5pt 0; }
#references, h2[id^="appendix-a-"] { break-before: page; }
'''


def read_member(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('package members must be relative paths without traversal')
    current = Path(root)
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('package refuses symlinks, including parent directories')
    if not current.is_file():
        raise ValueError('package member is not a regular file')
    return current.read_bytes()


def write_generated(relative, content):
    target = ROOT / relative
    # Check parent links before writing generated artifacts, including the ZIP.
    current = ROOT
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('generated output cannot be a symlink')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def prepare():
    markdown = read_member(ROOT, 'docs/report/latest.md').decode()
    if markdown.splitlines()[0] != '# ' + TITLE:
        raise ValueError('retain the exact report title')
    abstract = markdown.split('## Abstract\n\n', 1)[1].split('\n\n## 1.', 1)[0]
    if not 150 <= len(abstract.split()) <= 250:
        raise ValueError('abstract outside event word limit')
    body = re.sub(r'(<img[^>]+>\n<em class="caption">.*?</em>)',
                  r'<figure>\1</figure>', convert(markdown), flags=re.S)
    rendered = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
                'img-src \'self\' data:; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
                '<title>' + html.escape(TITLE) + '</title><style>' + CSS + '</style></head><body>'
                + body + '</body></html>')
    write_generated('docs/report/latest.html', rendered.encode())
    write_generated('docs/submission/latest/abstract.txt', (abstract + '\n').encode())
    write_generated('docs/submission/latest/metadata.json', encoded({
        'title': TITLE, 'project': 'Fleet Witness',
        'authors': [{'name': 'Alejandro Castellanos', 'affiliation': 'Independent researcher'},
                    {'name': 'Ignatius Pio Binawan', 'affiliation': 'University of Toronto'}],
        'abstract_words_whitespace': len(abstract.split()),
        'track_proposed': 'Multi-Agent Oversight and Control',
        'repository': 'https://github.com/k2jac9/fleet-witness',
        'guidelines': 'https://apartresearch.com/sprints/swarm-alignment-2026#guidelines',
        'template': 'https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/edit',
        'checked_date': '2026-11-09', 'deadline_utc': '2026-11-09T11:59:00Z',
        'submission_status': 'prepared; external upload and confirmation not performed',
        'report': 'latest.pdf', 'video_status': '180-second captioned edited walkthrough; no audio or new model calls',
        'video_url': 'https://github.com/k2jac9/fleet-witness/blob/main/docs/submission/media/fleet-witness-demo.mp4',
        'project_image': 'fleet-witness-cover.png',
    }))


def package():
    members = {name: read_member(ROOT, source) for name, source in MEMBERS.items()}
    pdf = members['latest.pdf']
    if not pdf.startswith(b'%PDF-') or len(pdf) >= 25_000_000:
        raise ValueError('report must be a PDF below the event upload limit')
    checksums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                        for name, data in sorted(members.items()))
    members['SHA256SUMS'] = checksums.encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    write_generated('docs/submission/latest/SHA256SUMS', checksums.encode())
    write_generated('docs/submission/latest-submission.zip', output.getvalue())
    print(f'Packaged {len(members)} explicit members ({len(output.getvalue())} bytes)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--package', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else package()


if __name__ == '__main__':
    main()
