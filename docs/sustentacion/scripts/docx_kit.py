"""Utilidades de composición para el documento maestro CITI (python-docx)."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x13, 0x27, 0x40)
TEAL = RGBColor(0x00, 0xAC, 0xC9)
GREEN = RGBColor(0x80, 0xBA, 0x27)
AMBER = RGBColor(0xB8, 0x7A, 0x00)
GRAY = RGBColor(0x5F, 0x5E, 0x5E)
LIGHT_GRAY = RGBColor(0xEE, 0xF2, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"
MONO = "Consolas"


def _field(paragraph, instr, placeholder=""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instr
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t")
    value.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(text)
    run._r.append(separate)
    run._r.append(value)
    run._r.append(end)
    return run


def _shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def _cell_margins(table, top=60, bottom=60, left=90, right=90):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    tblPr.append(mar)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    trPr.append(header)


def _cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    cant.set(qn("w:val"), "true")
    trPr.append(cant)


class Kit:
    def __init__(self, doc: Document, base: Path):
        self.doc = doc
        self.base = base
        self.fig_n = 0
        self.tab_n = 0

    @staticmethod
    def _field(paragraph, instr, placeholder=""):
        return _field(paragraph, instr, placeholder)

    # ------------------------------------------------------------------ text
    def h1(self, text, page_break=True):
        p = self.doc.add_paragraph(style="Heading 1")
        if page_break:
            p.paragraph_format.page_break_before = True
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = FONT
        run.font.size = Pt(22)
        run.font.bold = True
        run.font.color.rgb = NAVY
        pPr = p._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "18")
        bottom.set(qn("w:space"), "6")
        bottom.set(qn("w:color"), "00ACC9")
        borders.append(bottom)
        pPr.append(borders)

    def h2(self, text):
        p = self.doc.add_paragraph(style="Heading 2")
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = FONT
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = TEAL

    def h3(self, text):
        p = self.doc.add_paragraph(style="Heading 3")
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = FONT
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = NAVY

    def p(self, text="", bold=False, italic=False, size=10.5, color=NAVY,
          align="justify", space_after=6, indent=0.0, keep_next=False):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(space_after)
        pf.line_spacing = 1.14
        pf.keep_with_next = keep_next
        if indent:
            pf.left_indent = Cm(indent)
        p.alignment = {
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }[align]
        self._inline(p, text, size, color, bold, italic)
        return p

    def lead(self, lead, text, size=10.5):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.14
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = p.add_run(lead + " ")
        r.font.name = FONT
        r.font.size = Pt(size)
        r.bold = True
        r.font.color.rgb = NAVY
        self._inline(p, text, size, NAVY)
        return p

    def _inline(self, p, text, size, color, bold=False, italic=False):
        import re
        parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                r = p.add_run(part[2:-2])
                r.bold = True
            elif part.startswith("`") and part.endswith("`"):
                r = p.add_run(part[1:-1])
                r.font.name = MONO
                r.font.size = Pt(size - 1)
                r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
            elif part.startswith("*") and part.endswith("*"):
                r = p.add_run(part[1:-1])
                r.italic = True
            else:
                r = p.add_run(part)
            r.font.name = r.font.name or FONT
            if r.font.name != MONO:
                r.font.size = Pt(size)
                r.font.color.rgb = color
            r.bold = bold or r.bold
            r.italic = italic or r.italic

    def bullets(self, items, size=10.5, indent=0.55):
        for item in items:
            p = self.doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Cm(indent)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.1
            self._inline(p, item, size, NAVY)

    def numbered(self, items, size=10.5):
        for item in items:
            p = self.doc.add_paragraph(style="List Number")
            p.paragraph_format.left_indent = Cm(0.65)
            p.paragraph_format.space_after = Pt(3)
            self._inline(p, item, size, NAVY)

    def code(self, text):
        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        cell = table.cell(0, 0)
        cell.width = Cm(16.2)
        _shade(cell, "F4F6F8")
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        for i, line in enumerate(text.splitlines()):
            if i:
                p.add_run().add_break()
            r = p.add_run(line)
            r.font.name = MONO
            r.font.size = Pt(8.4)
            r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ---------------------------------------------------------------- figures
    def figure(self, filename, caption, width_cm=16.0):
        path = self.base / "diagramas" / filename
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run()
        run.add_picture(str(path), width=Cm(width_cm))
        self.fig_n += 1
        cap = self.doc.add_paragraph(style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        r = cap.add_run("Figura ")
        r.font.name = FONT
        r.font.size = Pt(8.8)
        r.font.color.rgb = GRAY
        self._field(cap, r"SEQ Figura \* ARABIC", str(self.fig_n))
        r2 = cap.add_run(f". {caption}")
        r2.font.name = FONT
        r2.font.size = Pt(8.8)
        r2.italic = True
        r2.font.color.rgb = GRAY

    # ----------------------------------------------------------------- tables
    def table(self, caption, headers, rows, widths=None, font=8.6,
              bold_first=False, align_center=False):
        self.tab_n += 1
        cap = self.doc.add_paragraph(style="Caption")
        cap.paragraph_format.space_before = Pt(6)
        cap.paragraph_format.space_after = Pt(3)
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run("Tabla ")
        r.font.name = FONT
        r.font.size = Pt(8.8)
        r.font.color.rgb = GRAY
        self._field(cap, r"SEQ Tabla \* ARABIC", str(self.tab_n))
        r2 = cap.add_run(f". {caption}")
        r2.font.name = FONT
        r2.font.size = Pt(8.8)
        r2.italic = True
        r2.font.color.rgb = GRAY

        table = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        _cell_margins(table)
        if widths:
            total = sum(widths)
            widths = [w * 16.6 / total for w in widths]
        else:
            widths = [16.6 / len(headers)] * len(headers)
        for c, head in enumerate(headers):
            cell = table.cell(0, c)
            cell.width = Cm(widths[c])
            _shade(cell, "132740")
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if align_center else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(head)
            run.font.name = FONT
            run.font.size = Pt(font)
            run.bold = True
            run.font.color.rgb = WHITE
        _repeat_header(table.rows[0])
        for i, row in enumerate(rows):
            _cant_split(table.rows[i + 1])
            for c, value in enumerate(row):
                cell = table.cell(i + 1, c)
                cell.width = Cm(widths[c])
                cell.text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.02
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (align_center and c > 0) else WD_ALIGN_PARAGRAPH.LEFT
                self._inline(p, str(value), font, NAVY, bold=(bold_first and c == 0))
                if i % 2:
                    _shade(cell, "F4F8FB")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(1)

    def callout(self, title, text, tone="amber"):
        fills = {"amber": ("FFF8E1", "D99A00"), "teal": ("E8F6FA", "00ACC9"),
                 "red": ("FDE0E0", "D32F2F"), "green": ("F1F8E6", "80BA27")}
        fill, border = fills.get(tone, fills["amber"])
        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        _cant_split(table.rows[0])
        cell = table.cell(0, 0)
        cell.width = Cm(16.2)
        _shade(cell, fill)
        tblPr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for side in ("top", "left", "bottom", "right"):
            edge = OxmlElement(f"w:{side}")
            edge.set(qn("w:val"), "single")
            edge.set(qn("w:sz"), "6")
            edge.set(qn("w:space"), "0")
            edge.set(qn("w:color"), border)
            borders.append(edge)
        tblPr.append(borders)
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(title)
        r.font.name = FONT
        r.font.size = Pt(9.2)
        r.bold = True
        r.font.color.rgb = NAVY
        p2 = cell.add_paragraph()
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = 1.08
        self._inline(p2, text, 9.0, NAVY)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # --------------------------------------------------------------- special
    def toc(self, instr):
        p = self.doc.add_paragraph()
        self._field(p, instr, "Actualice el índice en Word: clic derecho > Actualizar campo (F9).")
        return p

    def page_break(self):
        self.doc.add_page_break()
