"""Genera Guion_Sustentacion_10min.docx desde el guion Markdown.

Conversor acotado: títulos, párrafos, citas, listas, tablas y negritas.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "sustentacion"
SRC = BASE / "Guion_Sustentacion_10min.md"
OUT = BASE / "Guion_Sustentacion_10min.docx"
LOGO = ROOT / "backend" / "static" / "images" / "logo_ucc.png"

NAVY = RGBColor(0x13, 0x27, 0x40)
TEAL = RGBColor(0x00, 0xAC, 0xC9)
GREEN = RGBColor(0x80, 0xBA, 0x27)
GRAY = RGBColor(0x5F, 0x5E, 0x5E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"
MONO = "Consolas"
CODE = RGBColor(0x1F, 0x3A, 0x5F)


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_text(cell, text, bold=False, color=NAVY, size=8.5, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def inline(paragraph, text, size=10.5, color=NAVY, bold=False, italic=False):
    """Agrega texto con **negritas**, *cursivas* y `código`."""
    parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = MONO
            run.font.size = Pt(size - 0.8)
            run.font.color.rgb = CODE
            continue
        is_bold = part.startswith("**") and part.endswith("**")
        is_italic = part.startswith("*") and part.endswith("*") and not is_bold
        run = paragraph.add_run(part[2:-2] if is_bold else (part[1:-1] if is_italic else part))
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.bold = bold or is_bold
        run.italic = italic or is_italic


def add_heading(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    if level == 1:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(8)
        inline(p, text, 17, NAVY, bold=True)
        pPr = p._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "10")
        bottom.set(qn("w:space"), "4")
        bottom.set(qn("w:color"), "00ACC9")
        borders.append(bottom)
        pPr.append(borders)
    else:
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        inline(p, text, 12.5, TEAL, bold=True)


def add_table(doc, rows):
    cols = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            if r == 0:
                shade(cell, "132740")
                set_cell_text(cell, value, True, WHITE, 8.5)
            else:
                shade(cell, "FFFFFF" if r % 2 else "F4F8FB")
                set_cell_text(cell, value, c == 0, NAVY, 8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def build():
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    doc = Document()

    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = NAVY
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12

    # Encabezado y pie
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("CITI UCC · Guion de sustentación · 2026")
    run.font.name = FONT
    run.font.size = Pt(8)
    run.font.color.rgb = GRAY
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number(footer)

    # Portada
    if LOGO.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run().add_picture(str(LOGO), width=Cm(2.6))
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    inline(p, "UNIVERSIDAD COOPERATIVA DE COLOMBIA", 10, TEAL, bold=True)
    p = doc.add_paragraph()
    inline(p, "Campus Ibagué – El Espinal · Facultad de Ingeniería", 9.5, GRAY)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(40)
    inline(p, "Guion de sustentación", 30, NAVY, bold=True)
    p = doc.add_paragraph()
    inline(p, "CITI · Consultorio de Ingeniería, Tecnología e Innovación", 16, TEAL, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    inline(p, "Arquitectura y Modelamiento de Software · Entrega final", 11, GRAY)

    meta = [
        ("Expositores", "Santiago Cubillos Arana · Juan José Tique"),
        ("Duración", "9:00 de voz + 0:30 de transiciones = 9:30"),
        ("Reparto", "Santiago 5:05 · Juan José 3:55"),
        ("Fecha", "Noviembre de 2026"),
    ]
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(34)
    table = doc.add_table(rows=len(meta), cols=2)
    table.style = "Table Grid"
    for i, (k, v) in enumerate(meta):
        shade(table.cell(i, 0), "E8F6FA")
        set_cell_text(table.cell(i, 0), k, True, NAVY, 9.5)
        set_cell_text(table.cell(i, 1), v, False, NAVY, 9.5)

    doc.add_page_break()

    in_table = False
    table_rows = []
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue
        elif in_table:
            add_table(doc, table_rows)
            table_rows = []
            in_table = False

        if not line:
            continue
        if line.startswith("# "):
            # El título ya está en la portada.
            continue
        if line.startswith("### "):
            add_heading(doc, line[4:].strip(), 2)
        elif line.startswith("## "):
            add_heading(doc, line[3:].strip(), 1)
        elif line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.right_indent = Cm(0.4)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(8)
            pPr = p._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            left = OxmlElement("w:left")
            left.set(qn("w:val"), "single")
            left.set(qn("w:sz"), "18")
            left.set(qn("w:space"), "8")
            left.set(qn("w:color"), "00ACC9")
            borders.append(left)
            pPr.append(borders)
            inline(p, line[2:].strip(), 10.5, NAVY, italic=True)
        elif line.startswith("- [ ] "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.space_after = Pt(3)
            inline(p, "☐  " + line[6:].strip(), 10, NAVY)
        elif line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Cm(0.6)
            inline(p, line[2:].strip(), 10, NAVY)
        elif line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            inline(p, line, 10.5, NAVY, bold=True)
        elif line.startswith("---"):
            continue
        else:
            p = doc.add_paragraph()
            inline(p, line, 10.5, NAVY)

    if in_table and table_rows:
        add_table(doc, table_rows)

    doc.save(str(OUT))
    print(f"DOCX generado: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    build()
