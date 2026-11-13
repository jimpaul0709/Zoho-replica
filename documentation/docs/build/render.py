"""Render helpers: docx -> pdf (Word COM), heading page lookup, two-pass build, contact sheets."""
import os, re, subprocess, tempfile
import pymupdf
from PIL import Image

PS = """param($in,$out)
try {
  $w = New-Object -ComObject Word.Application
  $w.Visible = $false
  $w.DisplayAlerts = 0
  $d = $w.Documents.Open($in, $false, $true)
  $d.ExportAsFixedFormat($out, 17)
  $d.Close(0)
  $w.Quit()
  exit 0
} catch { Write-Output $_.Exception.Message; exit 1 }
"""

def to_pdf(docx, pdf):
    if os.path.exists(pdf):
        os.remove(pdf)
    ps1 = os.path.join(tempfile.gettempdir(), "wh_docx2pdf.ps1")
    open(ps1, "w", encoding="utf-8").write(PS)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1,
                        "-in", os.path.abspath(docx), "-out", os.path.abspath(pdf)], capture_output=True, text=True, timeout=240)
    if not os.path.exists(pdf):
        raise RuntimeError("pdf export failed: " + r.stdout + r.stderr)
    return pdf

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def heading_pages(pdf, headings):
    doc = pymupdf.open(pdf)
    lines = [[norm(l) for l in pg.get_text().splitlines()] for pg in doc]
    pages, start = {}, 1
    for h in headings:
        key = norm(h)
        for i in range(start, len(lines)):
            if any(l == key for l in lines[i]) or any(len(key) > 28 and l.startswith(key[:28]) and not re.search(r"\.{4,}", l) for l in lines[i]):
                pages[h] = i + 1
                start = i
                break
    return pages

def build(build_fn, out):
    doc = build_fn({})
    heads = doc.save(out)
    pdf = os.path.join(os.path.dirname(os.path.abspath(out)), "build", "_ref", os.path.basename(out)[:-5] + ".pdf")
    to_pdf(out, pdf)
    pages = heading_pages(pdf, heads)
    doc = build_fn(pages)
    doc.save(out, pages)
    to_pdf(out, pdf)
    n = len(pymupdf.open(pdf))
    missing = [h for h in heads if h not in pages]
    return pdf, n, missing

def contact(pdf, out_png, first=0, count=8, cols=4, dpi=48):
    doc = pymupdf.open(pdf)
    ims = []
    for i in range(first, min(first + count, len(doc))):
        pix = doc[i].get_pixmap(dpi=dpi)
        ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 6, rows * h + (rows + 1) * 6), (120, 120, 120))
    for k, im in enumerate(ims):
        sheet.paste(im, (6 + (k % cols) * (w + 6), 6 + (k // cols) * (h + 6)))
    sheet.save(out_png)
    return out_png

def page_png(pdf, n, out_png, dpi=70):
    pymupdf.open(pdf)[n - 1].get_pixmap(dpi=dpi).save(out_png)
