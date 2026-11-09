"""Render docs/report/REPORT.md to a print-ready HTML page (stdlib only).

Then print it to PDF with any Chromium browser, e.g.:
  msedge --headless=new --no-pdf-header-footer --print-to-pdf=docs/report/REPORT.pdf docs/report/REPORT.html

Supports the Markdown subset the report uses: headings, paragraphs, nested bullet and
numbered lists, pipe tables, images, block quotes, rules, bold/italic/code and links.
"""
import html
import re
import sys
from pathlib import Path

CSS = """
@page { size: Letter; margin: 0.8in 0.85in; }
body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45;
       color: #111; max-width: 7in; margin: 0 auto; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 10pt; }
h2 { font-size: 13pt; margin: 16pt 0 6pt; border-bottom: 1px solid #ddd; padding-bottom: 2pt; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt; }
p { margin: 5pt 0; }
ul, ol { margin: 3pt 0 6pt; padding-left: 18pt; }
li { margin: 1.5pt 0; }
table { border-collapse: collapse; margin: 8pt 0; font-size: 9.5pt; width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 3pt 6pt; vertical-align: top; }
th { background: #f3f3f1; text-align: left; }
td.num, th.num { text-align: right; }
img { max-width: 100%; max-height: 3.4in; display: block; margin: 8pt auto 2pt; page-break-inside: avoid; }
blockquote { margin: 6pt 0; padding: 4pt 10pt; border-left: 3px solid #999; background: #f7f7f5; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f2f2f0; padding: 0 2pt; border-radius: 2pt; }
hr { border: none; border-top: 1px solid #ddd; margin: 12pt 0; }
em.caption { display: block; font-size: 9pt; color: #444; margin-bottom: 8pt; }
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![\*\w])\*([^*\n]+)\*(?![\*\w])', r'<em>\1</em>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def convert(md: str) -> str:
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if m := re.match(r'^(#{1,4})\s+(.*)', line):
            level = len(m.group(1))
            slug = re.sub(r'[^a-z0-9]+', '-', m.group(2).lower()).strip('-')[:40]
            out.append(f'<h{level} id="{slug}">{inline(m.group(2))}</h{level}>')
            i += 1
        elif stripped == '---':
            out.append('<hr>')
            i += 1
        elif m := re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', stripped):
            out.append(f'<img src="{m.group(2)}" alt="{html.escape(m.group(1))}">')
            i += 1
        elif stripped.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            align = rows[1] if len(rows) > 1 and all(re.fullmatch(r':?-+:?', c) for c in rows[1]) else None
            body = rows[2:] if align else rows[1:]
            right = [c.endswith(':') and not c.startswith(':') for c in align] if align else []
            def cell(tag, c, k):
                cls = ' class="num"' if k < len(right) and right[k] else ''
                return f'<{tag}{cls}>{inline(c)}</{tag}>'
            out.append('<table><thead><tr>' + ''.join(cell('th', c, k) for k, c in enumerate(rows[0]))
                       + '</tr></thead><tbody>' + ''.join(
                           '<tr>' + ''.join(cell('td', c, k) for k, c in enumerate(r)) + '</tr>' for r in body)
                       + '</tbody></table>')
        elif stripped.startswith('>'):
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote>' + inline(' '.join(quote)) + '</blockquote>')
        elif re.match(r'^\s*([-*]|\d+\.)\s+', line):
            block = []
            while i < len(lines) and (re.match(r'^\s*([-*]|\d+\.)\s+', lines[i])
                                      or (lines[i].startswith('  ') and lines[i].strip())):
                block.append(lines[i])
                i += 1
            out.append(render_list(block))
        else:
            para = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(
                    r'^(#{1,4}\s|\||>|!\[|---$|\s*([-*]|\d+\.)\s+)', lines[i]):
                para.append(lines[i].strip())
                i += 1
            text = ' '.join(para)
            if text.startswith('*') and text.endswith('*') and not text.startswith('**'):
                out.append(f'<em class="caption">{inline(text[1:-1])}</em>')
            else:
                out.append(f'<p>{inline(text)}</p>')
    return '\n'.join(out)


def render_list(block: list[str]) -> str:
    """Nested lists by indentation; continuation lines join the previous item."""
    items = []  # (indent, ordered, text)
    for line in block:
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', line)
        if m:
            items.append([len(m.group(1)), m.group(2)[0].isdigit(), m.group(3)])
        elif items:
            items[-1][2] += ' ' + line.strip()
    html_parts, stack = [], []
    for indent, ordered, text in items:
        while stack and indent < stack[-1][0]:
            html_parts.append('</li></' + stack.pop()[1] + '>')
        if not stack or indent > stack[-1][0]:
            tag = 'ol' if ordered else 'ul'
            stack.append((indent, tag))
            html_parts.append(f'<{tag}><li>{inline(text)}')
        else:
            html_parts.append(f'</li><li>{inline(text)}')
    while stack:
        html_parts.append('</li></' + stack.pop()[1] + '>')
    return ''.join(html_parts)


if __name__ == '__main__':
    source = Path(sys.argv[1] if len(sys.argv) > 1 else 'docs/report/REPORT.md')
    target = source.with_suffix('.html')
    md = source.read_text(encoding='utf-8')
    # Drop the drafting note line (italic paragraph directly under the title block) from the PDF.
    md = re.sub(r'^\*Draft for the official Apart template\..*?\*\n', '', md, flags=re.S | re.M)
    # Drafting aids that do not belong in a submission PDF.
    md = re.sub(r'^## Abstract \(.*?\)$', '## Abstract', md, flags=re.M)
    md = re.sub(r'^\*\(Verify every reference.*?\)\*\n', '', md, flags=re.S | re.M)
    title = re.search(r'^#\s+(.*)', md, re.M).group(1)
    target.write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
                      f'<style>{CSS}</style></head><body>{convert(md)}</body></html>', encoding='utf-8')
    print(target)
