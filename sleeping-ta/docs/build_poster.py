"""Render docs/poster.html to IV-2-10_Poster.pdf and a PNG preview for the Teams post.

Usage (from sleeping-ta/):  make poster
Needs WeasyPrint (sudo apt install weasyprint) and pdftoppm (poppler-utils).
"""
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import weasyprint
except ImportError:
    sys.exit('WeasyPrint хэрэгтэй: sudo apt install weasyprint')

DOCS = Path(__file__).resolve().parent
PDF = DOCS / 'IV-2-10_Poster.pdf'

document = weasyprint.HTML(filename=str(DOCS / 'poster.html')).render()
if len(document.pages) != 1:  # the BD2 guide requires a single page
    sys.exit(f'Постер {len(document.pages)} хуудас боллоо; 1 хуудсанд багтаана уу.')
document.write_pdf(PDF)
print('wrote', PDF.relative_to(DOCS.parent))
if shutil.which('pdftoppm'):
    subprocess.run(['pdftoppm', '-r', '150', '-png', '-singlefile', str(PDF), str(DOCS / 'IV-2-10_Poster')],
                   check=True)
    print('wrote docs/IV-2-10_Poster.png')
