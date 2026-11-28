"""Construye Documentacion_Arquitectura_CITI_UCC.docx.

Portada, índice, resumen ejecutivo, 13 capítulos, referencias y anexos.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))

import doc_part1
import doc_part2
import doc_part3
import doc_part4
import doc_part5
from docx_kit import FONT, GRAY, NAVY, TEAL, WHITE, Kit, _field, _shade

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "sustentacion"
OUT = BASE / "Documentacion_Arquitectura_CITI_UCC.docx"
LOGO = ROOT / "backend" / "static" / "images" / "logo_ucc.png"


def cover(doc):
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    if LOGO.exists():
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(str(LOGO), width=Cm(2.8))
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("UNIVERSIDAD COOPERATIVA DE COLOMBIA")
    r.font.name = FONT
    r.font.size = Pt(10.5)
    r.bold = True
    r.font.color.rgb = TEAL
    p = doc.add_paragraph()
    r = p.add_run("Campus Ibagué – El Espinal · Facultad de Ingeniería")
    r.font.name = FONT
    r.font.size = Pt(9.5)
    r.font.color.rgb = GRAY

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(60)

    band = doc.add_table(rows=1, cols=1)
    band.alignment = WD_TABLE_ALIGNMENT.CENTER
    band.autofit = False
    cell = band.cell(0, 0)
    cell.width = Cm(16.4)
    _shade(cell, "132740")
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("CITI")
    r.font.name = FONT
    r.font.size = Pt(46)
    r.bold = True
    r.font.color.rgb = WHITE
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(2)
    r = p2.add_run("Consultorio de Ingeniería, Tecnología e Innovación")
    r.font.name = FONT
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor(0xD7, 0xE2, 0xEE)
    p3 = cell.add_paragraph()
    p3.paragraph_format.space_before = Pt(8)
    p3.paragraph_format.space_after = Pt(18)
    r = p3.add_run("Documento maestro de arquitectura")
    r.font.name = FONT
    r.font.size = Pt(12)
    r.bold = True
    r.font.color.rgb = RGBColor(0x80, 0xBA, 0x27)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    r = p.add_run("De la solicitud al acta: una arquitectura modular para la confianza institucional")
    r.font.name = FONT
    r.font.size = Pt(13)
    r.italic = True
    r.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(40)
    meta = [
        ("Asignatura", "Arquitectura y Modelamiento de Software"),
        ("Entrega", "Sustentación final · Noviembre de 2026"),
        ("Autores", "Santiago Cubillos Arana · Juan José Tique"),
        ("Versión", "1.0 · Documento de arquitectura y evidencia"),
    ]
    table = doc.add_table(rows=len(meta), cols=2)
    table.style = "Table Grid"
    table.autofit = False
    for i, (key, value) in enumerate(meta):
        c0, c1 = table.cell(i, 0), table.cell(i, 1)
        c0.width = Cm(3.2)
        c1.width = Cm(12.6)
        _shade(c0, "E8F6FA")
        c0.text = ""
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(key)
        r0.font.name = FONT
        r0.font.size = Pt(9.5)
        r0.bold = True
        r0.font.color.rgb = NAVY
        c1.text = ""
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(value)
        r1.font.name = FONT
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(70)
    r = p.add_run("Documento de apoyo académico. Las cifras y afirmaciones se contrastaron con el "
                  "código y la suite de pruebas del repositorio.")
    r.font.name = FONT
    r.font.size = Pt(8.5)
    r.italic = True
    r.font.color.rgb = GRAY


def front_matter(doc, k):
    # TOC
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("Contenido")
    r.font.name = FONT
    r.font.size = Pt(24)
    r.bold = True
    r.font.color.rgb = NAVY
    k.toc(r'TOC \o "1-3" \h \z \u')

    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("Índice de figuras")
    r.font.name = FONT
    r.font.size = Pt(20)
    r.bold = True
    r.font.color.rgb = NAVY
    k.toc(r'TOC \h \z \c "Figura"')

    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("Índice de tablas")
    r.font.name = FONT
    r.font.size = Pt(20)
    r.bold = True
    r.font.color.rgb = NAVY
    k.toc(r'TOC \h \z \c "Tabla"')

    # Resumen ejecutivo
    k.h1("Resumen ejecutivo")
    k.p("CITI es un sistema web para gestionar el ciclo completo de una asesoría universitaria: "
        "desde la solicitud del cliente hasta el acta de cierre, pasando por la asignación de "
        "responsables, la ejecución, la entrega de resultados y la decisión del cliente. El "
        "sistema se implementó como un monolito modular en Django 5, con tres apps "
        "(`accounts`, `scheduling`, `portal`), una base SQLite para la demo y configuración "
        "lista para PostgreSQL en producción.")
    k.p("La arquitectura se diseñó alrededor de tres requisitos: acceso por rol y por área, "
        "trazabilidad transaccional y mantenibilidad con un equipo pequeño. De ahí surgen las "
        "decisiones principales: monolito modular en lugar de microservicios, templates Django "
        "con JSON mínimo en lugar de SPA, servicios de dominio explícitos en lugar de señales "
        "globales, y un historial append-only (`CitaEvento`) que se escribe en la misma "
        "transacción que el cambio de estado.")
    k.p("La entrega incluye 107 pruebas automatizadas en 18 clases, nueve diagramas regenerados "
        "desde el código, diez ADR, una evaluación de calidad con ISO/IEC 25010 y evidencia de "
        "mediciones locales. Los límites también se declaran: no hay prueba de carga ni "
        "cobertura formal, el despliegue es manual, no hay CI/CD ni backups automáticos, y "
        "algunos hallazgos de seguridad permanecen abiertos. El sistema es adecuado para el "
        "contexto académico y tiene una ruta clara de evolución; no se presenta como producción "
        "terminada.")
    k.table("Cifras de la entrega",
            ["Indicador", "Valor", "Fuente"],
            [["Pruebas automatizadas", "107/107 OK en 67,524 s", "`fase0_test.txt`"],
             ["Clases de prueba", "18", "`portal/tests.py`"],
             ["Modelos de dominio", "8", "`accounts/models.py`, `scheduling/models.py`"],
             ["Estados formales", "5", "`CitaAsesoria.Estado`"],
             ["Subespecialidades", "14 (4 Sistemas + 10 Civil)", "`subespecialidades.py`"],
             ["Rutas", "26", "`urls.py`"],
             ["Diagramas", "9", "`docs/sustentacion/diagramas/`"],
             ["ADRs", "10", "Capítulo 10"]],
            widths=[1.0, 1.3, 1.0])


def main():
    doc = Document()
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.3)
    section.bottom_margin = Cm(2.1)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = NAVY
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.14

    for style_name, size in (("Heading 1", 22), ("Heading 2", 13), ("Heading 3", 11)):
        style = doc.styles[style_name]
        style.font.name = FONT
        style.font.size = Pt(size)
        style.font.color.rgb = NAVY
        style.font.bold = True

    # Encabezado y pie (excepto portada)
    header = section.header
    hp = header.paragraphs[0]
    hp.text = ""
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(15.9), alignment=2)
    r = hp.add_run("CITI UCC · Documento de arquitectura")
    r.font.name = FONT
    r.font.size = Pt(8)
    r.font.color.rgb = GRAY
    r = hp.add_run("\tNoviembre de 2026")
    r.font.name = FONT
    r.font.size = Pt(8)
    r.font.color.rgb = GRAY

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Página ")
    r.font.name = FONT
    r.font.size = Pt(8)
    r.font.color.rgb = GRAY
    _field(fp, "PAGE", "1")
    r = fp.add_run(" de ")
    r.font.name = FONT
    r.font.size = Pt(8)
    r.font.color.rgb = GRAY
    _field(fp, "NUMPAGES", "1")

    cover(doc)
    doc.add_page_break()
    k = Kit(doc, BASE)
    front_matter(doc, k)
    doc_part1.build(k)
    doc_part2.build(k)
    doc_part3.build(k)
    doc_part4.build(k)
    doc_part5.build(k)

    # Actualizar campos al abrir en Word
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)

    core = doc.core_properties
    core.title = "CITI · Documento maestro de arquitectura"
    core.subject = "Arquitectura y Modelamiento de Software · Sustentación final"
    core.author = "Santiago Cubillos Arana · Juan José Tique"
    core.keywords = "CITI, Django, arquitectura, trazabilidad, ISO 25010, UCC"
    core.comments = "Documento generado desde el código y la evidencia del repositorio."

    doc.save(str(OUT))
    print(f"DOCX generado: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
