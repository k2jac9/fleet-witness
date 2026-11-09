"""Fill the Apart hackathon Google-Docs HTML template with docs/report/REPORT.md.

Usage:
  python scripts/report_to_template.py TEMPLATE.html AUTHORS.json OUT.html
AUTHORS.json: {"authors": [{"name": "...", "affiliation": "...", "email": "..."}, ...]}
Keep AUTHORS.json and the output out of git if they contain personal emails.

Keeps the template's own head (fonts, styles), title box, author grid, "With Apart
Research" line, abstract box and footnote; drops the guidance box; renders the report's
sections below in matching typography. Print OUT.html to PDF with a Chromium browser.
"""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_to_pdf import convert, inline  # noqa: E402

EXTRA_CSS = """
.fw h2{font-family:"Old Standard TT";font-size:14pt;font-weight:700;color:#434343;padding-top:10pt;padding-bottom:0;margin:0 0 4pt;line-height:1.5}
.fw h3{font-family:"Old Standard TT";font-size:13pt;font-weight:700;color:#666666;padding-top:8pt;padding-bottom:2pt;margin:0}
.fw p,.fw li,.fw td,.fw th{font-family:"Old Standard TT";font-size:11pt;line-height:1.3;color:#000}
.fw p{margin:0 0 6pt;text-align:justify}
.fw ul,.fw ol{margin:2pt 0 6pt;padding-left:22pt}
.fw li{margin:1pt 0}
.fw table{border-collapse:collapse;margin:6pt 0 8pt;width:100%;page-break-inside:avoid}
.fw th,.fw td{border:1px solid #999;padding:2pt 5pt;font-size:9.5pt;vertical-align:top}
.fw th{background:#f3f3f3;text-align:left}
.fw td.num,.fw th.num{text-align:right}
.fw img{max-width:100%;max-height:3.3in;display:block;margin:6pt auto 2pt;page-break-inside:avoid}
.fw em.caption{display:block;font-size:9.5pt;font-style:italic;margin:0 0 8pt;text-align:left}
.fw blockquote{margin:4pt 18pt;padding:2pt 8pt;border-left:2px solid #888}
.fw code{font-family:Consolas,monospace;font-size:9pt}
.fw hr{border:none;border-top:1px solid #ccc;margin:10pt 0}
td.c11{width:210pt}
@page{size:Letter;margin:0}
body.c50{padding:60pt 66pt !important;max-width:none !important}
"""


def main(template_path, authors_path, out_path, report_path='docs/report/REPORT.md'):
    template = Path(template_path).read_text(encoding='utf-8')
    authors = json.loads(Path(authors_path).read_text(encoding='utf-8'))['authors']
    md = Path(report_path).read_text(encoding='utf-8')

    title = re.search(r'^#\s+(.*)', md, re.M).group(1)
    abstract = re.search(r'^## Abstract[^\n]*\n(.*?)\n---', md, re.S | re.M).group(1).strip()
    abstract_html = ''.join(f'<p class="c45"><span class="c19">{inline(" ".join(p.split()))}</span></p>'
                            for p in re.split(r'\n\s*\n', abstract) if p.strip())
    abstract_html = abstract_html.replace('<p class="c45">', '<p class="c45" style="font-style:normal">')
    body_md = md[md.index('## 1. Introduction'):]

    head, rest = template.split('</head>', 1)
    head = head.replace('</style>', EXTRA_CSS + '</style>')
    top = rest[:rest.index('<table class="c59">')]           # title, authors, abstract (guidance box dropped)
    footnote = rest[rest.index('<hr class="c57">'):rest.index('</body>')]

    top = top.replace('PROJECT TITLE', html.escape(title))
    cells = ''.join(
        f'<td class="c11" colspan="1" rowspan="1"><p class="c0"><span class="c9">{html.escape(a["name"])}<br>'
        f'{html.escape(a.get("affiliation") or "") or "&nbsp;"}'
        + (f'<br><span style="font-size:9pt">{html.escape(a["email"])}</span>' if a.get('email') else '')
        + '</span></p></td>' for a in authors)
    top = re.sub(r'<table class="c25"><tr class="c46">.*?</table>', f'<table class="c25"><tr class="c46">{cells}</tr></table>',
                 top, count=1, flags=re.S)
    top = re.sub(r'<td class="c55"[^>]*>.*?</td>', f'<td class="c55" colspan="1" rowspan="1">{abstract_html}</td>',
                 top, count=1, flags=re.S)

    content = convert(body_md)
    Path(out_path).write_text(f'{head}</head>{top}<div class="fw">{content}</div>{footnote}</body></html>',
                              encoding='utf-8')
    print(out_path)


if __name__ == '__main__':
    main(*sys.argv[1:4])
