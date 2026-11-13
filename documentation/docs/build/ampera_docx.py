"""Ampera document template (from AMP_CSA_DPDP_006): cover, running header, footer, Calibri headings,
grey-header tables, standard closing sections. Built with python-docx; no Word templates inherited."""
import os
import re
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "ampera_logo_cover.png")
NAVY = "002060"
GREY = "D9D9D9"
BODY_FONT, HEAD_FONT = "Times New Roman", "Calibri"


def _fonts(style, name):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def _style(doc, name, font, size, bold=False, italic=False, color="000000", before=0, after=6, keep=False, line=None):
    st = doc.styles[name]
    _fonts(st, font)
    st.font.size, st.font.bold, st.font.italic = Pt(size), bold, italic
    st.font.color.rgb = RGBColor.from_string(color)
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.keep_with_next = Pt(before), Pt(after), keep
    if line:
        pf.line_spacing = line
    return st


def _border(ppr, side, color, sz, space=1):
    b = ppr.find(qn("w:pBdr"))
    if b is None:
        b = OxmlElement("w:pBdr")
        ppr.append(b)
    e = OxmlElement(f"w:{side}")
    for k, v in (("val", "single"), ("sz", str(sz)), ("space", str(space)), ("color", color)):
        e.set(qn(f"w:{k}"), v)
    b.append(e)


def _shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def _cell_borders(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    tb = tcPr.find(qn("w:tcBorders"))
    if tb is None:
        tb = OxmlElement("w:tcBorders")
        tcPr.append(tb)
    for side, (val, sz, color) in kw.items():
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), val)
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:color"), color)
        tb.append(e)


def _table_borders(tbl, color="000000", sz=4):
    b = OxmlElement("w:tblBorders")
    for s in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{s}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        b.append(e)
    tbl._tbl.tblPr.append(b)


def _cell_margins(tbl, top=40, bottom=40, left=90, right=90):
    m = OxmlElement("w:tblCellMar")
    for s, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{s}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tbl._tbl.tblPr.append(m)


def _fixed_layout(tbl):
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tbl._tbl.tblPr.append(lay)


def _field(run, instr):
    def fc(t):
        f = OxmlElement("w:fldChar")
        f.set(qn("w:fldCharType"), t)
        return f
    run._r.append(fc("begin"))
    i = OxmlElement("w:instrText")
    i.set(qn("xml:space"), "preserve")
    i.text = instr
    run._r.append(i)
    run._r.append(fc("separate"))
    t = OxmlElement("w:t")
    t.text = "1"
    run._r.append(t)
    run._r.append(fc("end"))


def _runs(par, text, size=None, font=None, color=None, bold=None, italic=None):
    """Tiny inline markup: **bold**, *italic*, `mono`. A newline becomes a line break."""
    for tok in re.split(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)", text):
        if not tok:
            continue
        b, i, mono = bold, italic, False
        if tok.startswith("**") and tok.endswith("**"):
            tok, b = tok[2:-2], True
        elif tok.startswith("`") and tok.endswith("`"):
            tok, mono = tok[1:-1], True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            tok, i = tok[1:-1], True
        for n, seg in enumerate(tok.split("\n")):
            if n:
                par.add_run().add_break()
            r = par.add_run(seg)
            if size:
                r.font.size = Pt(size)
            if mono:
                r.font.name = "Consolas"
                r.font.size = Pt((size or 11) - 1)
            elif font:
                r.font.name = font
                r._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)
            if b:
                r.font.bold = True
            if i:
                r.font.italic = True


class AmperaDoc:
    def __init__(self, title, doc_id, version, ver_date, product, classification="Internal", landscape=False,
                 cover_lines=None):
        self.d = Document()
        self.title, self.doc_id, self.version, self.ver_date = title, doc_id, version, ver_date
        self.product, self.classification = product, classification
        self.headings, self.fig_n, self.pages = [], 0, {}
        self.landscape = landscape
        self.cover_lines = cover_lines or [title.upper().replace("\n", " ")]
        self._styles()
        self._section(self.d.sections[0], landscape)
        self.d.sections[0].different_first_page_header_footer = True
        self._cover()

    # ---------- setup ----------
    def _styles(self):
        d = self.d
        _style(d, "Normal", BODY_FONT, 12, after=8, line=1.08)
        d.styles["Normal"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _style(d, "Heading 1", HEAD_FONT, 18, bold=True, before=18, after=8, keep=True)
        _style(d, "Heading 2", HEAD_FONT, 14, bold=True, before=14, after=6, keep=True)
        _style(d, "Heading 3", HEAD_FONT, 12, bold=True, before=10, after=4, keep=True)
        for n in ("List Bullet", "List Number"):
            _style(d, n, BODY_FONT, 12, after=3)
            d.styles[n].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for lvl in (1, 2):
            st = d.styles.add_style(f"TOC {lvl}", WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = d.styles["Normal"]
            _fonts(st, HEAD_FONT)
            st.font.size = Pt(12 if lvl == 1 else 11)
            st.paragraph_format.left_indent = Inches(0 if lvl == 1 else 0.3)
            st.paragraph_format.space_after = Pt(3)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def _section(self, sec, landscape):
        sec.page_width, sec.page_height = (Inches(11), Inches(8.5)) if landscape else (Inches(8.5), Inches(11))
        sec.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
        sec.left_margin = sec.right_margin = Inches(1)
        sec.top_margin, sec.bottom_margin = Inches(1.75), Inches(1)
        sec.header_distance, sec.footer_distance = Inches(0.5), Inches(0.45)
        self._hf(sec)

    def _width(self, sec):
        return (sec.page_width - sec.left_margin - sec.right_margin) / 914400.0

    def _hf(self, sec):
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        w = self._width(sec)
        h = sec.header
        for el in list(h._element):
            h._element.remove(el)
        logo_w = 1.8
        t = h.add_table(1, 2, Inches(w))
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        _fixed_layout(t)
        L, R = t.rows[0].cells
        t.columns[0].width, t.columns[1].width = Inches(w - logo_w), Inches(logo_w)
        L.width, R.width = Inches(w - logo_w), Inches(logo_w)
        L.vertical_alignment = R.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = L.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _runs(p, self.title, size=20, font=HEAD_FONT, bold=True)
        rp = R.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        rp.paragraph_format.space_after = Pt(0)
        rp.add_run().add_picture(LOGO, width=Inches(logo_w - 0.1))
        p2 = h.add_paragraph()
        pf = p2.paragraph_format
        pf.space_before, pf.space_after, pf.alignment = Pt(2), Pt(0), WD_ALIGN_PARAGRAPH.LEFT
        _border(p2._p.get_or_add_pPr(), "top", NAVY, 18, space=3)
        pf.tab_stops.add_tab_stop(Inches(w * 0.52), WD_TAB_ALIGNMENT.LEFT)
        pf.tab_stops.add_tab_stop(Inches(w), WD_TAB_ALIGNMENT.RIGHT)
        _runs(p2, f"Document No: {self.doc_id}\tVer No: {self.version}\tVer Date: {self.ver_date}", size=10,
              font=HEAD_FONT, bold=True)
        f = sec.footer
        for el in list(f._element):
            f._element.remove(el)
        fp = f.add_paragraph()
        fp.paragraph_format.tab_stops.add_tab_stop(Inches(w), WD_TAB_ALIGNMENT.RIGHT)
        fp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _border(fp._p.get_or_add_pPr(), "top", "A6A6A6", 4, space=6)
        _runs(fp, f"{self.classification}\tPage ", size=9, font=HEAD_FONT)
        _field(fp.add_run(), "PAGE")
        fp.add_run(" of ")
        _field(fp.add_run(), "NUMPAGES")
        for r in fp.runs:
            r.font.size, r.font.name = Pt(9), HEAD_FONT

    def _cover(self):
        d = self.d
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(20 if self.landscape else 60)
        p.paragraph_format.space_after = Pt(30 if self.landscape else 70)
        p.add_run().add_picture(LOGO, width=Inches(4.8))
        for line in self.cover_lines + [f"Doc ID: {self.doc_id}", f"Doc Version No: {self.version}"]:
            q = d.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            q.paragraph_format.space_after = Pt(14)
            _runs(q, line, size=14, font=HEAD_FONT, color=NAVY)
        self.page_break()

    # ---------- structure ----------
    def spacer(self, pt=6):
        par = self.d.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        par.paragraph_format.line_spacing = Pt(pt)

    def page_break(self):
        par = self.d.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        par.paragraph_format.line_spacing = Pt(1)
        r = par.add_run()
        r.font.size = Pt(1)
        r.add_break(WD_BREAK.PAGE)

    def section(self, landscape):
        """Start a new section with its own header/footer width."""
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        sec.different_first_page_header_footer = False
        self._section(sec, landscape)
        return sec

    def h(self, text, level=1, page_break=False):
        if page_break:
            self.page_break()
        p = self.d.add_heading(level=level)
        _runs(p, text, font=HEAD_FONT)
        for r in p.runs:
            r.font.color.rgb = RGBColor(0, 0, 0)
        if level <= 2:
            self.headings.append((level, text))
        return p

    def p(self, text, align=None, size=None, italic=None, color=None, after=None, keep=False, left=None):
        par = self.d.add_paragraph()
        _runs(par, text, size=size, italic=italic, color=color)
        if align == "left":
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if after is not None:
            par.paragraph_format.space_after = Pt(after)
        if keep:
            par.paragraph_format.keep_with_next = True
        if left:
            par.paragraph_format.left_indent = Inches(left)
        return par

    def note(self, text):
        return self.p(text, italic=True, size=11, color="404040", align="left")

    def bullets(self, items, numbered=False, size=None):
        for it in items:
            par = self.d.add_paragraph(style="List Number" if numbered else "List Bullet")
            _runs(par, it, size=size)

    def table(self, headers, rows, widths, size=10.5, header_fill=GREY, align=None, first_bold=False, fills=None,
              keep=True):
        """headers: list or None. rows: list of lists of str. widths in inches. fills: {(row, col): hex}."""
        off = 1 if headers else 0
        n_rows = len(rows) + off
        t = self.d.add_table(rows=n_rows, cols=len(widths))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _fixed_layout(t)
        _table_borders(t)
        _cell_margins(t)
        for i, wd in enumerate(widths):
            t.columns[i].width = Inches(wd)
        allr = ([headers] if headers else []) + rows
        for ri, row in enumerate(allr):
            tr = t.rows[ri]
            trPr = tr._tr.get_or_add_trPr()
            trPr.append(OxmlElement("w:cantSplit"))
            if headers and ri == 0:
                trPr.append(OxmlElement("w:tblHeader"))
            for ci, txt in enumerate(row):
                c = tr.cells[ci]
                c.width = Inches(widths[ci])
                c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                par = c.paragraphs[0]
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.0
                par.alignment = {"c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT}.get(
                    align[ci] if align else "l", WD_ALIGN_PARAGRAPH.LEFT)
                is_h = bool(headers) and ri == 0
                _runs(par, str(txt), size=size, font=HEAD_FONT, bold=True if (is_h or (first_bold and ci == 0)) else None)
                if is_h:
                    _shade(c, header_fill)
                elif fills and (ri - off, ci) in fills:
                    _shade(c, fills[(ri - off, ci)])
                if keep and ri < n_rows - 1:
                    par.paragraph_format.keep_with_next = True
        self.spacer(8)
        return t

    def kv(self, rows, widths=(2.0, 4.5), headers=("Field", "Detail")):
        return self.table(list(headers), rows, list(widths))

    def callout(self, title, text, color=NAVY, fill="EEF2FA", width=None):
        w = width or self.width_now()
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _fixed_layout(t)
        _cell_margins(t, 90, 90, 160, 140)
        t.columns[0].width = Inches(w)
        c = t.rows[0].cells[0]
        c.width = Inches(w)
        _shade(c, fill)
        _cell_borders(c, left=("single", 36, color), top=("nil", 0, "auto"), bottom=("nil", 0, "auto"),
                      right=("nil", 0, "auto"))
        par = c.paragraphs[0]
        par.paragraph_format.space_after = Pt(2)
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _runs(par, title, size=11, font=HEAD_FONT, bold=True, color=color)
        q = c.add_paragraph()
        q.paragraph_format.space_after = Pt(0)
        q.paragraph_format.line_spacing = 1.0
        q.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _runs(q, text, size=10.5, font=HEAD_FONT)
        self.spacer(8)

    def tiles(self, items, color=NAVY, fill="F2F2F2", width=None):
        """items: [(big, small)] shown as a strip of equal tiles."""
        w = width or self.width_now()
        n = len(items)
        t = self.d.add_table(rows=1, cols=n)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _fixed_layout(t)
        _cell_margins(t, 100, 100, 110, 100)
        for i in range(n):
            t.columns[i].width = Inches(w / n)
        for i, (big, small) in enumerate(items):
            c = t.rows[0].cells[i]
            c.width = Inches(w / n)
            _shade(c, fill)
            _cell_borders(c, left=("single", 24, "FFFFFF"), right=("single", 24, "FFFFFF"),
                          top=("single", 18, color), bottom=("nil", 0, "auto"))
            par = c.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _runs(par, big, size=20, font=HEAD_FONT, bold=True, color=color)
            q = c.add_paragraph()
            q.paragraph_format.space_after = Pt(0)
            q.paragraph_format.line_spacing = 1.0
            q.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _runs(q, small, size=9.5, font=HEAD_FONT, color="404040")
        self.spacer(8)

    def figure(self, path, caption, width=None):
        w = width or min(6.5, self.width_now())
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(2)
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(path, width=Inches(w))
        self.fig_n += 1
        c = self.d.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_after = Pt(10)
        _runs(c, f"Figure {self.fig_n}. {caption}", size=9.5, font=HEAD_FONT, italic=True, color="404040")

    # ---------- standard front and back matter ----------
    def toc(self):
        """Table of Contents heading; entries are inserted at save() as a real TOC field."""
        self._toc_anchor = self.d.add_paragraph()
        self._toc_anchor.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _runs(self._toc_anchor, "Table of Contents", size=12, font=HEAD_FONT, bold=True)
        self.page_break()

    def _fill_toc(self):
        w = self._width(self.d.sections[0])
        prev = self._toc_anchor._p
        for i, (lvl, text) in enumerate(self.headings):
            par = self.d.add_paragraph(style=f"TOC {lvl}")
            par.paragraph_format.tab_stops.add_tab_stop(Inches(w), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if i == 0:
                r = par.add_run()
                for kind in ("begin", "instr", "separate"):
                    if kind == "instr":
                        it = OxmlElement("w:instrText")
                        it.set(qn("xml:space"), "preserve")
                        it.text = ' TOC \\o "1-2" \\h \\z \\u '
                        r._r.append(it)
                    else:
                        f = OxmlElement("w:fldChar")
                        f.set(qn("w:fldCharType"), kind)
                        r._r.append(f)
            _runs(par, f"{text}\t{self.pages.get(text, '')}")
            if i == len(self.headings) - 1:
                f3 = OxmlElement("w:fldChar")
                f3.set(qn("w:fldCharType"), "end")
                par.add_run()._r.append(f3)
            prev.addnext(par._p)
            prev = par._p

    def width_now(self):
        return self._width(self.d.sections[-1])

    def doc_info(self, rows):
        self.p(f"Product: {self.product}", align="left")
        self.h("1. Document Information", 1)
        base = [("Document Title", self.title.replace("\n", " ")), ("Document Number", self.doc_id),
                ("Version Number", self.version), ("Version Date", self.ver_date),
                ("Classification", self.classification)]
        self.kv(base + rows, widths=(2.0, self.width_now() - 2.0))

    def closing(self, n, authors, description):
        """Template closing sections: Revision History, Template Revision History, Review History."""
        w = self.width_now()
        self.h(f"{n}. Revision History", 1)
        cw = [0.8, 1.1, w - 4.7, 0.95, 0.95, 0.9]
        hd = ["Revision Number", "Author(s)", "Description of Version", "Date of Revision (dd-Mmm-YYYY)",
              "Reviewed & approved by", "Approval Date (dd-Mmm-YYYY)"]
        self.table(hd, [[self.version, authors, description, self.ver_date, "Pending review", "-"]], cw, size=10)
        self.note("<This section will be filled by the Compliance team>")
        self.h(f"{n + 1}. Template Revision History", 1)
        self.table(hd, [["1.0", "Saritha K", "Initial template", "02-Jan-2026", "", "02-Jan-2026"]], cw, size=10)
        self.h(f"{n + 1}.1 Review History", 2)
        self.note("<This section will be filled with proof for review of this document. In case there are any "
                  "changes while reviewing, it should be updated in the revision history table above>")
        self.table(["Review Date", "Reviewed by", "Next Review Date"], [["-", "-", "-"], ["", "", ""]], [w / 3] * 3)

    def save(self, path, pages=None):
        self.pages = pages or self.pages
        self._fill_toc()
        self.d.core_properties.title = self.title.replace("\n", " ")
        self.d.core_properties.author = "Ampera Technologies"
        self.d.save(path)
        return [t for _, t in self.headings]
