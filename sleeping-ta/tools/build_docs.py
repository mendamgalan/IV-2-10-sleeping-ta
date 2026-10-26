"""Build the two submission PDFs from the repository Markdown sources.

Supports the small Markdown subset used in these documents: headings,
paragraphs, fenced code, tables, links and standalone images.
"""
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
)
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(os.environ.get('TA_DOC_FONT_DIR', '/usr/share/fonts/truetype/dejavu'))
for name, filename in [('Body', 'DejaVuSans.ttf'), ('Bold', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Body', boldItalic='Bold')
styles = {
    'body': ParagraphStyle('body', fontName='Body', fontSize=10, leading=15, spaceAfter=8),
    'title': ParagraphStyle('title', fontName='Bold', fontSize=21, leading=27, spaceAfter=15),
    'heading': ParagraphStyle('heading', fontName='Bold', fontSize=13, leading=18,
                              spaceBefore=12, spaceAfter=7, keepWithNext=True),
    'code': ParagraphStyle('code', fontName='Body', fontSize=8, leading=12, spaceAfter=3),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=8.2, leading=12),
}


def inline(text):
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1 (\2)', text)


def footer(canvas, doc):
    canvas.setFont('Body', 8)
    canvas.drawString(44, 27, 'F.CSM302 · IV-2-10')
    canvas.drawRightString(A4[0] - 44, 27, str(doc.page))


def build(source, target):
    lines = source.read_text(encoding='utf-8').splitlines()
    story, paragraph = [], []
    width = A4[0] - 88

    def flush():
        if paragraph:
            story.append(Paragraph(inline(' '.join(paragraph)), styles['body']))
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('```'):
            flush()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(Paragraph(escape(lines[i]), styles['code']))
                i += 1
            story.append(KeepTogether(block))
            story.append(Spacer(1, 7))
        elif line.startswith('|'):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [s.strip() for s in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', c) for c in cells):
                    rows.append([Paragraph(inline(c), styles['cell']) for c in cells])
                i += 1
            fractions = [0.30, 0.70] if len(rows[0]) == 2 else [0.26, 0.49, 0.25]
            table = Table(rows, colWidths=[width * f for f in fractions], repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9edf2')),
                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#cfd5db')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            story.extend([table, Spacer(1, 10)])
            continue
        elif line.startswith('!['):
            flush()
            match = re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)', line)
            if match:
                path = source.parent / match[2]
                iw, ih = ImageReader(str(path)).getSize()
                factor = min(width / iw, 260 / ih)
                story.append(KeepTogether([
                    Image(str(path), width=iw * factor, height=ih * factor),
                    Paragraph(inline(match[1]), styles['code']), Spacer(1, 7),
                ]))
        elif line.startswith('# '):
            flush()
            story.append(Paragraph(inline(line[2:]), styles['title']))
        elif line.startswith('## '):
            flush()
            story.append(Paragraph(inline(line[3:]), styles['heading']))
        elif not line:
            flush()
        elif re.match(r'^(- |\d+\. )', line):
            flush()
            story.append(Paragraph(inline(line), styles['body']))
        else:
            paragraph.append(line)
        i += 1
    flush()
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=44, rightMargin=44,
                            topMargin=42, bottomMargin=45, title=source.stem,
                            author='IV-2-10 project', pageCompression=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(target)


if __name__ == '__main__':
    for name, filename in [('Report', 'IV-2-10_BD1_Report.pdf'), ('Manual', 'IV-2-10_Manual.pdf')]:
        build(ROOT / 'docs' / f'{name}.md', ROOT / 'docs' / filename)
