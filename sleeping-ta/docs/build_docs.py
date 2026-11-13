"""Build IV-2-10_BD1_Report.pdf and IV-2-10_Manual.pdf from the Markdown sources.

Usage (from sleeping-ta/):  make docs
Needs python3-markdown and LibreOffice Writer (soffice). The Markdown files are
the only source, so the PDFs cannot drift from them.
"""
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit('python3-markdown хэрэгтэй: sudo apt install python3-markdown')

DOCS = Path(__file__).resolve().parent
TEXT_WIDTH = 640  # px available between the page margins

STYLE = """
@page { size: 21cm 29.7cm; margin: 2cm 2cm 2cm 2.5cm; }
body { font-family: "Arial"; font-size: 10.5pt; }
p, li { text-align: justify; margin-top: 0.05cm; margin-bottom: 0.15cm; }
h1, h2, h3 { font-family: "Arial"; }
h1 { font-size: 17pt; border-bottom: 1px solid #000000; margin-bottom: 0.2cm; }
h2 { font-size: 13.5pt; margin-top: 0.45cm; margin-bottom: 0.12cm; }
h3 { font-size: 11pt; margin-top: 0.3cm; margin-bottom: 0.1cm; }
td, th { font-family: "Arial"; font-size: 9pt; vertical-align: top; }
code, pre { font-family: "DejaVu Sans Mono"; font-size: 8.3pt; }
.cap { font-size: 9pt; text-align: center; margin-bottom: 0.3cm; }
"""

COVER = """
<p align="center" style="margin-top:0.3cm"><font face="Times New Roman" style="font-size:15pt"><b>ШИНЖЛЭХ УХААН, ТЕХНОЛОГИЙН ИХ СУРГУУЛЬ<br>МЭДЭЭЛЭЛ, ХОЛБООНЫ ТЕХНОЛОГИЙН СУРГУУЛЬ</b></font></p>
<p align="center" style="margin-top:0.8cm"><img src="{logo}" width="76" height="126" alt="ШУТИС"></p>
<p align="center" style="margin-top:2.2cm"><font face="Times New Roman" style="font-size:18pt">F.CSM302 Үйлдлийн систем</font></p>
<p align="center" style="margin-top:0.8cm"><font face="Times New Roman" style="font-size:30pt"><b>{title}</b></font></p>
<p align="center" style="margin-top:0.4cm"><font face="Times New Roman" style="font-size:16pt">{subtitle}</font></p>
<p align="center" style="margin-top:0.3cm"><font face="Times New Roman" style="font-size:12pt">Хувилбар 1.1 · 2026-11-13</font></p>
<table border="0" cellspacing="0" cellpadding="3" align="center" style="margin-top:2.4cm">
<tr><td width="170"><font face="Times New Roman" style="font-size:12pt">Шалгасан багш:</font></td><td width="260"><font face="Times New Roman" style="font-size:12pt">Г. Ганбат</font></td></tr>
<tr><td><font face="Times New Roman" style="font-size:12pt">Багийн дугаар:</font></td><td><font face="Times New Roman" style="font-size:12pt">IV-2-10</font></td></tr>
<tr><td><font face="Times New Roman" style="font-size:12pt">Гүйцэтгэсэн оюутан:</font></td><td><font face="Times New Roman" style="font-size:12pt">Ж. Мэнд-Амгалан /B242270008/<br>Г. Оргилсайхан /B222270044/<br>Б. Түмэнбаяр /B242270114/<br>Б. Манлайбаатар /B241940052/</font></td></tr>
</table>
<p align="center" style="margin-top:3.2cm"><font face="Times New Roman" style="font-size:12pt">Улаанбаатар хот<br>2026 он</font></p>
"""


def image_size(path):
    """Width and height in px for PNG or SVG (enough for LibreOffice layout)."""
    data = path.read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    text = data.decode('utf-8', 'replace')
    width = re.search(r'<svg[^>]*\bwidth="(\d+)', text)
    height = re.search(r'<svg[^>]*\bheight="(\d+)', text)
    return int(width.group(1)), int(height.group(1))


def to_html(source, cover=None):
    text = source.read_text(encoding='utf-8')
    if cover:
        text = re.sub(r'\A# .*\n\n.*\n', '', text)  # the cover replaces title + subtitle lines
    body = markdown.markdown(text, extensions=['tables', 'fenced_code'])

    def sized(match):
        alt, src = match.group(1), match.group(2)
        width, height = image_size(DOCS / src)
        scale = min(1.0, (TEXT_WIDTH - 60) / width)
        return (f'<p align="center"><img src="{(DOCS / src).resolve().as_uri()}" alt="{alt}" '
                f'width="{round(width * scale)}" height="{round(height * scale)}"></p>')

    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', sized, body)
    body = re.sub(r'<p><em>(Зураг \d+\..*?)</em></p>', r'<p class="cap"><i>\1</i></p>', body, flags=re.S)
    body = body.replace('<table>', '<table border="1" cellspacing="0" cellpadding="3" width="100%">')
    body = body.replace('<thead>\n<tr>', '<thead>\n<tr bgcolor="#dcdcdc">')
    parts = [f'<!DOCTYPE html><html lang="mn"><head><meta charset="utf-8"><title>{source.stem}</title>'
             f'<style>{STYLE}</style></head><body>']
    if cover:
        parts.append(COVER.format(logo=(DOCS / 'images' / 'logo.png').as_uri(), **cover))
        headings = re.findall(r'<h2>(.*?)</h2>', body)
        items = ''.join(f'<p style="margin:0.08cm 0">{h}</p>' for h in headings)
        parts.append(f'<h1 style="page-break-before: always">Агуулга</h1>{items}')
        body = body.replace('<h2>', '<h2 style="page-break-before: always">', 1)
    parts.append(body + '</body></html>')
    return ''.join(parts)


def build(source, target, cover=None):
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / f'{target.stem}.html'
        html.write_text(to_html(source, cover), encoding='utf-8')
        subprocess.run(['soffice', f'-env:UserInstallation=file://{tmp}/profile', '--headless',
                        '--infilter=HTML (StarWriter)', '--convert-to', 'pdf:writer_pdf_Export',
                        '--outdir', tmp, str(html)], check=True, stdout=subprocess.DEVNULL)
        shutil.move(Path(tmp) / f'{target.stem}.pdf', target)
    print('wrote', target.relative_to(DOCS.parent))


if __name__ == '__main__':
    if not shutil.which('soffice'):
        sys.exit('LibreOffice хэрэгтэй: sudo apt install libreoffice-writer')
    build(DOCS / 'Report.md', DOCS / 'IV-2-10_BD1_Report.pdf',
          cover={'title': 'The Sleeping Teaching Assistant', 'subtitle': 'Бие даалт №1 — тайлан'})
    build(DOCS / 'Manual.md', DOCS / 'IV-2-10_Manual.pdf')
