"""Construye CITI_Sustentacion_Final.pptx (13 diapositivas + 3 de respaldo).

Diseño nativo en python-pptx, 16:9, paleta UCC.
No modifica el código de la aplicación.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "sustentacion"
DIAG = BASE / "diagramas"
EVID = BASE / "evidencias"
LEGACY = EVID / "legacy"
OUT = BASE / "CITI_Sustentacion_Final.pptx"
LOGO = ROOT / "backend" / "static" / "images" / "logo_ucc.png"

NAVY = RGBColor(0x13, 0x27, 0x40)
TEAL = RGBColor(0x00, 0xAC, 0xC9)
GREEN = RGBColor(0x80, 0xBA, 0x27)
AMBER = RGBColor(0xD9, 0x9A, 0x00)
GRAY = RGBColor(0x5F, 0x5E, 0x5E)
LIGHT = RGBColor(0xF4, 0xF8, 0xFB)
BORDER = RGBColor(0xDD, 0xE3, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_TEAL = RGBColor(0xE8, 0xF6, 0xFA)
SOFT_GREEN = RGBColor(0xF1, 0xF8, 0xE6)
SOFT_AMBER = RGBColor(0xFF, 0xF8, 0xE1)
SOFT_GRAY = RGBColor(0xEE, 0xF2, 0xF7)

FONT = "Segoe UI"
FONT_B = "Segoe UI Semibold"
SW, SH = 13.333, 7.5

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)


def blank():
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=WHITE, line=BORDER, radius=True, lw=1.0):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(lw)
    shape.shadow.inherit = False
    if radius:
        try:
            shape.adjustments[0] = 0.08
        except Exception:
            pass
    return shape


def text(slide, x, y, w, h, content, size=16, color=NAVY, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, line_spacing=1.05):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    lines = str(content).split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            p = tf.add_paragraph()
            p.alignment = align
            p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.name = font
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return box


def bullets(slide, x, y, w, h, items, size=16, color=NAVY, gap=8):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "•  " + item
        p.space_after = Pt(gap)
        p.line_spacing = 1.08
        for r in p.runs:
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.color.rgb = color
    return box


def header(slide, kicker, title, subtitle=None, number=None):
    text(slide, 0.55, 0.32, 11.6, 0.3, kicker.upper(), 10.5, TEAL, True, font=FONT_B)
    text(slide, 0.55, 0.62, 11.9, 0.7, title, 27, NAVY, True, font=FONT_B)
    if subtitle:
        text(slide, 0.55, 1.28, 11.9, 0.45, subtitle, 12, GRAY)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.72), Inches(0.9), Inches(0.045))
    line.fill.solid(); line.fill.fore_color.rgb = TEAL; line.line.fill.background()
    if number:
        text(slide, 12.25, 7.12, 0.6, 0.25, str(number), 9, GRAY, False, PP_ALIGN.RIGHT)
    text(slide, 0.55, 7.12, 9.5, 0.25,
         "CITI UCC · Arquitectura y Modelamiento de Software · 2026", 8.5, GRAY)


def tag(slide, x, y, w, label, fill=SOFT_TEAL, color=NAVY, size=10):
    r = rect(slide, x, y, w, 0.3, fill, fill, True, 0)
    text(slide, x, y + 0.04, w, 0.22, label, size, color, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, FONT_B)


def logo(slide, x=0.55, y=0.3, w=0.62):
    if LOGO.exists():
        slide.shapes.add_picture(str(LOGO), Inches(x), Inches(y), width=Inches(w))


def add_picture_fit(slide, path, x, y, w=None, h=None):
    im = Image.open(path)
    if w and not h:
        h = w * im.height / im.width
    if h and not w:
        w = h * im.width / im.height
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w), height=Inches(h))


# ---------------------------------------------------------------------------
# 1. Portada
# ---------------------------------------------------------------------------
s = blank()
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SW), Inches(SH))
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.14), Inches(SH))
bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
if LOGO.exists():
    s.shapes.add_picture(str(LOGO), Inches(0.72), Inches(0.55), width=Inches(0.95))
text(s, 1.85, 0.62, 6.0, 0.3, "UNIVERSIDAD COOPERATIVA DE COLOMBIA", 10.5,
     RGBColor(0xCF, 0xDA, 0xE6), True, font=FONT_B)
text(s, 1.85, 0.92, 7.0, 0.3, "Campus Ibagué – El Espinal · Facultad de Ingeniería", 10,
     RGBColor(0x9F, 0xB3, 0xCA))
text(s, 0.72, 1.75, 11.6, 0.35, "SUSTENTACIÓN FINAL · ARQUITECTURA Y MODELAMIENTO DE SOFTWARE", 12, TEAL, True, font=FONT_B)
text(s, 0.72, 2.15, 11.4, 0.9, "CITI", 64, WHITE, True, font=FONT_B)
text(s, 0.72, 3.05, 11.4, 0.6, "Consultorio de Ingeniería, Tecnología e Innovación", 25, WHITE, False, font=FONT)
text(s, 0.72, 3.7, 11.2, 0.8,
     "De la solicitud al acta: una arquitectura modular para la confianza institucional.",
     17, RGBColor(0xD7, 0xE2, 0xEE))
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.72), Inches(4.7), Inches(3.2), Inches(0.05))
line.fill.solid(); line.fill.fore_color.rgb = GREEN; line.line.fill.background()
text(s, 0.72, 5.0, 6.0, 0.3, "EXPOSITORES", 9.5, TEAL, True, font=FONT_B)
text(s, 0.72, 5.3, 6.5, 0.55, "Santiago Cubillos Arana", 18, WHITE, True, font=FONT_B)
text(s, 0.72, 5.85, 6.5, 0.55, "Juan José Tique", 18, WHITE, True, font=FONT_B)
text(s, 8.4, 5.3, 4.3, 0.9, "Noviembre de 2026", 14, RGBColor(0xCF, 0xDA, 0xE6), False, PP_ALIGN.RIGHT)
text(s, 8.4, 5.7, 4.3, 0.9, "Documento de arquitectura + demo en vivo", 11,
     RGBColor(0x9F, 0xB3, 0xCA), False, PP_ALIGN.RIGHT)

# ---------------------------------------------------------------------------
# 2. Problema y contexto
# ---------------------------------------------------------------------------
s = blank()
header(s, "01 · Problema y contexto", "Un consultorio que necesita confianza, no solo pantallas",
       "El CITI articula academia, empresas y territorio; la arquitectura debe hacer visible quién responde y qué ocurrió.", 2)
bullets(s, 0.6, 1.95, 5.0, 3.4, [
    "El CITI atiende empresas, instituciones y ciudadanía con recursos académicos limitados.",
    "Sin responsables, reglas académicas y evidencia, la atención se vuelve un correo tras otro.",
    "El diseño debe garantizar acceso por rol, trazabilidad y un cierre verificable.",
], 15.5)
tag(s, 0.6, 6.55, 1.9, "5 roles", SOFT_TEAL)
tag(s, 2.65, 6.55, 2.2, "2 áreas UCC", SOFT_GREEN, NAVY)
tag(s, 5.0, 6.55, 2.2, "14 especialidades", SOFT_AMBER, NAVY)
# contexto nativo
cx, cy = 8.55, 2.35
rect(s, cx, cy, 2.5, 1.15, NAVY, NAVY)
text(s, cx, cy + 0.12, 2.5, 0.35, "SISTEMA CITI", 12, TEAL, True, PP_ALIGN.CENTER, font=FONT_B)
text(s, cx, cy + 0.48, 2.5, 0.55, "Django 5.x\nMVT + servicios", 10.5, WHITE, False, PP_ALIGN.CENTER, font=FONT)
actors = [("Cliente / Empresa", 1.55), ("Estudiante", 2.55), ("Docente", 3.55),
          ("Coordinador", 4.55), ("Director", 5.55)]
for label, y in actors:
    rect(s, 6.55, y, 1.75, 0.38, SOFT_TEAL, TEAL)
    text(s, 6.6, y + 0.07, 1.65, 0.22, label, 8.8, NAVY, True, PP_ALIGN.CENTER, font=FONT_B)
    text(s, 8.35, y + 0.06, 0.18, 0.2, "→", 10, GRAY, True, PP_ALIGN.CENTER)
ext = [("Navegador HTTP", 2.1), ("PostgreSQL / SQLite", 3.05), ("MEDIA_ROOT", 4.0)]
for label, y in ext:
    rect(s, 11.15, y, 1.65, 0.48, SOFT_GRAY, BORDER)
    text(s, 11.2, y + 0.08, 1.55, 0.3, label, 8.5, NAVY, False, PP_ALIGN.CENTER)
    text(s, 11.0, y + 0.1, 0.18, 0.2, "→", 9, GRAY, True, PP_ALIGN.CENTER)
text(s, 8.55, 5.55, 2.5, 0.3, "GitHub · CDN FullCalendar", 8.5, GRAY, False, PP_ALIGN.CENTER)
text(s, 8.55, 6.0, 4.2, 0.8, "La frontera del sistema es Django; los actores solo entran por HTTP y reglas de rol.",
     9.2, GRAY, False, PP_ALIGN.LEFT)
s.notes_slide.notes_text_frame.text = "Santiago: el CITI no es un CRM genérico; es un consultorio universitario con reglas académicas y necesidad de evidencia."

# ---------------------------------------------------------------------------
# 3. Evolución
# ---------------------------------------------------------------------------
s = blank()
header(s, "02 · Evolución del proyecto", "Del modelado inicial al sistema implementado",
       "Cada etapa dejó un artefacto verificable: modelos, arquitectura, decisiones, pruebas y demo.", 3)
stages = [
    ("S1–S5", "Modelado", ["Actores, casos de uso", "Clases y ERD inicial", "Arquitectura propuesta"], SOFT_TEAL, TEAL),
    ("S6–S10", "Implementación", ["Django MVT", "Bloqueantes corregidos", "42 pruebas + seed"], SOFT_GREEN, GREEN),
    ("S11–S16", "Trazabilidad e interacción", ["CitaEvento append-only", "Dashboard ejecutivo", "107 pruebas + E2E"], SOFT_AMBER, AMBER),
]
for i, (period, title, items, fill, accent) in enumerate(stages):
    x = 0.55 + i * 4.15
    rect(s, x, 1.95, 3.85, 1.55, fill, accent)
    text(s, x + 0.18, 2.02, 1.2, 0.28, period, 9.5, accent, True, font=FONT_B)
    text(s, x + 0.18, 2.28, 3.4, 0.3, title, 12.5, NAVY, True, font=FONT_B)
    text(s, x + 0.18, 2.62, 3.45, 0.75, " · ".join(items), 8.9, GRAY)
    if i < 2:
        text(s, x + 3.86, 2.55, 0.25, 0.3, "→", 16, GRAY, True, PP_ALIGN.CENTER)
# legacy thumbnails
text(s, 0.6, 3.72, 5.9, 0.3, "EVIDENCIA DE EVOLUCIÓN · MODELADO INICIAL S1–S5", 9.5, TEAL, True, font=FONT_B)
legacy = [
    ("legacy_01_clases.png", "Clases · versión simple"),
    ("legacy_02_clases_full.png", "Clases · modelo amplio"),
    ("legacy_03_casos_uso.png", "Casos de uso · versión 1"),
    ("legacy_04_casos_uso_full.png", "Casos de uso · versión 2"),
]
for i, (name, label) in enumerate(legacy):
    x = 0.6 + (i % 2) * 2.55
    y = 4.0 + (i // 2) * 1.35
    add_picture_fit(s, LEGACY / name, x, y, h=1.2)
text(s, 0.6, 6.65, 5.3, 0.3, "Modelado inicial S1–S5 · capturas de clases y casos de uso", 7.3, GRAY, False, PP_ALIGN.LEFT)
text(s, 6.55, 3.72, 6.0, 0.3, "MODELO IMPLEMENTADO", 9.5, GREEN, True, font=FONT_B)
bullets(s, 6.55, 4.05, 6.0, 2.0, [
    "8 modelos: Empresa, CustomUser, PerfilEstudiante, FranjaHoraria, CitaAsesoria, NotaBitacora, CitaEvento, CitaInteraccion.",
    "5 estados formales y una única reapertura permitida.",
    "Diagramas definitivos regenerados desde el código real.",
], 10.5, NAVY, 5)
tag(s, 6.55, 5.35, 2.0, "107 pruebas", SOFT_GREEN, NAVY)
tag(s, 8.75, 5.35, 2.3, "0 migraciones pendientes", SOFT_TEAL, NAVY)
s.notes_slide.notes_text_frame.text = "Santiago: mostramos los diagramas iniciales como evidencia, no como modelo vigente; el modelo final se regeneró del código."

# ---------------------------------------------------------------------------
# 4. Casos de uso
# ---------------------------------------------------------------------------
s = blank()
header(s, "03 · Modelado", "Cinco roles, un mismo flujo de valor",
       "Cada actor tiene un portal, un alcance y un conjunto de acciones permitidas por el servidor.", 4)
actors_uc = [
    ("CLIENTE", ["Solicitar asesoría o consultoría", "Seguir, comentar y solicitar ajustes", "Aprobar o rechazar entregable", "Cancelar solicitud"], SOFT_TEAL, TEAL),
    ("ESTUDIANTE", ["Registrar bitácora de apoyo", "Consultar casos de apoyo"], SOFT_GREEN, GREEN),
    ("DOCENTE", ["Gestionar caso asignado", "Publicar entregable", "Emitir acta de cierre"], SOFT_AMBER, AMBER),
    ("COORDINADOR", ["Revisar bandeja del área", "Asignar docente y tutor", "Seguimiento de su área", "Exportar CSV"], SOFT_TEAL, TEAL),
    ("DIRECTOR", ["Panel ejecutivo", "Trazabilidad global", "Indicadores y CSV", "Administrar registros"], SOFT_GRAY, GRAY),
]
for i, (actor, items, fill, accent) in enumerate(actors_uc):
    x = 0.55 + i * 2.45
    rect(s, x, 1.95, 2.3, 2.55, WHITE, accent)
    rect(s, x, 1.95, 2.3, 0.42, fill, fill, False, 0)
    text(s, x, 2.03, 2.3, 0.28, actor, 10, accent, True, PP_ALIGN.CENTER, font=FONT_B)
    text(s, x + 0.12, 2.5, 2.05, 1.9, "\n".join("• " + it for it in items), 8.8, NAVY, False, PP_ALIGN.LEFT, line_spacing=1.08)
text(s, 0.55, 4.72, 8.0, 0.3, "FLUJO DE VALOR COMPARTIDO · UN SOLO REGISTRO, CINCO MIRADAS", 9.5, TEAL, True, font=FONT_B)
flow = [
    ("Solicitar", "solicitada", SOFT_TEAL, TEAL),
    ("Asignar", "asignada", SOFT_GREEN, GREEN),
    ("Ejecutar", "en_proceso", SOFT_AMBER, AMBER),
    ("Entregar", "en_proceso", SOFT_AMBER, AMBER),
    ("Cerrar", "finalizada", SOFT_GRAY, GRAY),
]
for i, (step, state, fill, accent) in enumerate(flow):
    x = 0.55 + i * 2.45
    rect(s, x, 5.05, 2.15, 0.62, fill, accent)
    text(s, x, 5.12, 2.15, 0.25, str(i + 1) + " · " + step, 10.5, NAVY, True, PP_ALIGN.CENTER, font=FONT_B)
    text(s, x, 5.38, 2.15, 0.2, state, 7.8, GRAY, False, PP_ALIGN.CENTER)
    if i < 4:
        text(s, x + 2.15, 5.2, 0.3, 0.25, "→", 13, GRAY, True, PP_ALIGN.CENTER)
text(s, 0.55, 5.75, 12.2, 0.3, "Aprobar un entregable no cierra el caso: el cierre es una decisión distinta y auditada. Reabrir solo está permitido de finalizada a en_proceso.", 8.8, GRAY)
rect(s, 0.55, 6.15, 12.25, 0.6, SOFT_AMBER, AMBER)
text(s, 0.72, 6.23, 11.9, 0.45,
     "Cinco roles implementados; el servidor fuerza el alcance. UC-13 lo comparten coordinador (área) y director (global).",
     9.5, RGBColor(0x5F, 0x4A, 0x00))
s.notes_slide.notes_text_frame.text = "Juan: no dibujamos actores que no existen; los roles del diagrama son los 5 implementados."

# ---------------------------------------------------------------------------
# 5. Componentes
# ---------------------------------------------------------------------------
s = blank()
header(s, "04 · Componentes", "Tres apps, una sola verdad transaccional",
       "Cada app tiene un límite claro; los servicios de dominio concentran las reglas que no deben duplicarse.", 5)
apps = [
    ("accounts", "Identidad y reglas académicas", ["CustomUser", "Empresa", "PerfilEstudiante", "signals.py"],
     "Quién entra y qué requisitos académicos cumple.", SOFT_TEAL, TEAL),
    ("scheduling", "Agenda, estados y evidencia", ["FranjaHoraria", "CitaAsesoria", "CitaEvento", "CitaInteraccion"],
     "Qué se agenda, en qué estado va y qué evidencia deja.", SOFT_AMBER, AMBER),
    ("portal", "Presentación y decisión", ["views.py", "indicadores.py", "forms.py", "templates"],
     "Cómo se presenta cada rol y qué puede decidir.", SOFT_GREEN, GREEN),
]
for i, (name, desc, items, purpose, fill, accent) in enumerate(apps):
    x = 0.55 + i * 4.2
    rect(s, x, 1.95, 3.9, 2.0, fill, accent)
    text(s, x + 0.2, 2.05, 3.5, 0.3, name, 18, NAVY, True, font=FONT_B)
    text(s, x + 0.2, 2.38, 3.5, 0.3, desc, 10, GRAY)
    text(s, x + 0.2, 2.7, 3.5, 0.4, " · ".join(items), 9.2, NAVY)
    text(s, x + 0.2, 3.42, 3.5, 0.4, purpose, 9.2, accent, True, font=FONT_B)
text(s, 0.6, 4.2, 12.0, 0.3, "SERVICIOS DE DOMINIO COMPARTIDOS", 9.5, TEAL, True, font=FONT_B)
services = [("trazabilidad.py", "eventos y transiciones"), ("indicadores.py", "métricas y CSV"),
            ("subespecialidades.py", "catálogo real"), ("role_required", "control de acceso")]
for i, (name, desc) in enumerate(services):
    x = 0.55 + i * 3.15
    rect(s, x, 4.55, 2.9, 0.62, WHITE, TEAL)
    text(s, x + 0.12, 4.61, 2.65, 0.22, name, 10, NAVY, True, font=FONT_B)
    text(s, x + 0.12, 4.84, 2.65, 0.22, desc, 7.8, GRAY)
text(s, 0.6, 5.45, 12.0, 0.3, "INFRAESTRUCTURA", 9.5, GRAY, True, font=FONT_B)
infra = [("Django ORM", "SQLite / PostgreSQL"), ("Templates", "31 plantillas + CSS"),
         ("MEDIA_ROOT", "adjuntos autorizados"), ("Django Admin", "solo lectura histórica")]
for i, (name, desc) in enumerate(infra):
    x = 0.55 + i * 3.15
    rect(s, x, 5.8, 2.9, 0.62, SOFT_GRAY, BORDER)
    text(s, x + 0.12, 5.86, 2.65, 0.22, name, 10, NAVY, True, font=FONT_B)
    text(s, x + 0.12, 6.09, 2.65, 0.22, desc, 7.8, GRAY)
text(s, 0.6, 6.65, 12.0, 0.3, "Sin DRF: JSON solo para calendario y reserva.  El admin es herramienta administrativa, no el dashboard del director.",
     8.8, GRAY)
s.notes_slide.notes_text_frame.text = "Juan: la separación por apps permite extraer servicios después, sin reescribir el dominio."

# ---------------------------------------------------------------------------
# 6. Arquitectura por capas
# ---------------------------------------------------------------------------
s = blank()
header(s, "05 · Arquitectura", "Monolito modular MVT con servicios de dominio",
       "La petición recorre capas explícitas; las reglas críticas no viven en el template.", 6)
layers = [
    ("PRESENTACIÓN", "Navegador · URLconf · Vistas FBV · Templates · Formularios", SOFT_TEAL, TEAL, 1.95),
    ("APLICACIÓN", "Middleware/Auth · trazabilidad.py · indicadores.py · decoradores", SOFT_AMBER, AMBER, 2.95),
    ("DOMINIO", "Modelos accounts/scheduling · máquina de estados · reglas académicas", SOFT_GREEN, GREEN, 3.95),
    ("INFRAESTRUCTURA", "ORM · SQLite/PostgreSQL · MEDIA_ROOT · python-dotenv", SOFT_GRAY, GRAY, 4.95),
]
for label, desc, fill, accent, y in layers:
    rect(s, 0.55, y, 8.4, 0.78, fill, accent)
    text(s, 0.7, y + 0.1, 1.9, 0.25, label, 9, accent, True, font=FONT_B)
    text(s, 2.45, y + 0.08, 6.3, 0.55, desc, 10.2, NAVY)
# path
text(s, 9.35, 1.95, 3.5, 0.3, "RECORRIDO DE UNA PETICIÓN", 9.5, TEAL, True, font=FONT_B)
steps = ["1  URL", "2  Auth / rol", "3  Vista", "4  Servicio", "5  ORM", "6  DB", "7  Template"]
for i, step in enumerate(steps):
    y = 2.3 + i * 0.55
    rect(s, 9.35, y, 3.3, 0.38, WHITE if i % 2 == 0 else SOFT_GRAY, BORDER)
    text(s, 9.5, y + 0.07, 3.0, 0.22, step, 10, NAVY, i in (2, 3), font=FONT_B if i in (2, 3) else FONT)
    if i < len(steps) - 1:
        text(s, 10.75, y + 0.36, 0.25, 0.18, "↓", 8, GRAY, True, PP_ALIGN.CENTER)
rect(s, 9.35, 6.25, 3.3, 0.85, SOFT_AMBER, AMBER)
text(s, 9.5, 6.32, 3.0, 0.7, "Atajo mental: URL → Auth → View → Service → ORM → DB → Template.", 8.4, RGBColor(0x5F, 0x4A, 0x00))
text(s, 0.55, 6.15, 8.4, 0.7,
     "Las capas no son carpetas: son una regla de dependencia. Un template no decide permisos y una vista no arma SQL a mano.",
     10, GRAY)
s.notes_slide.notes_text_frame.text = "Santiago: las reglas de negocio están en modelos/servicios; el template solo presenta."

# ---------------------------------------------------------------------------
# 7. Drivers
# ---------------------------------------------------------------------------
s = blank()
header(s, "06 · Drivers arquitectónicos", "Tres drivers que cambiaron el diseño",
       "No elegimos un estilo por moda: cada driver tiene una consecuencia verificable en el código.", 7)
drivers = [
    ("01", "Seguridad y acceso por rol", ["5 roles + área", "Login con portal esperado", "IDOR y CSRF probados"], "El servidor fuerza el alcance; no el frontend."),
    ("02", "Trazabilidad transaccional", ["CitaEvento append-only", "Servicios explícitos", "Todo en transaction.atomic()"], "Si la operación falla, no queda evento de éxito."),
    ("03", "Mantenibilidad y evolución", ["3 apps con límites", "107 pruebas", "Servicios y documentación"], "Permite extraer módulos sin reescribir el dominio."),
]
for i, (num, title, items, consequence) in enumerate(drivers):
    x = 0.55 + i * 4.2
    rect(s, x, 1.95, 3.9, 3.7, WHITE, BORDER)
    tag(s, x + 0.2, 2.1, 0.55, num, SOFT_TEAL, TEAL, 11)
    text(s, x + 0.2, 2.55, 3.5, 0.6, title, 14.5, NAVY, True, font=FONT_B)
    text(s, x + 0.2, 3.25, 3.5, 1.2, "\n".join("• " + it for it in items), 10.5, GRAY)
    text(s, x + 0.2, 4.55, 3.5, 0.85, "CONSECUENCIA\n" + consequence, 9.2, TEAL, True, font=FONT_B)
rect(s, 0.55, 5.95, 12.2, 0.65, SOFT_AMBER, AMBER)
text(s, 0.72, 6.03, 11.8, 0.5,
     "Restricción real: 2 personas, 10 semanas, sin presupuesto de infraestructura. La arquitectura debía ser operable y demostrable, no sobredimensionada.",
     9.8, RGBColor(0x5F, 0x4A, 0x00))
s.notes_slide.notes_text_frame.text = "Santiago: los drivers explican por qué no usamos microservicios ni una SPA."

# ---------------------------------------------------------------------------
# 8. Alternativas y ADRs
# ---------------------------------------------------------------------------
s = blank()
header(s, "07 · Decisiones", "Elegimos consistencia y claridad, no complejidad accidental",
       "10 ADRs documentados: contexto, alternativas, decisión, consecuencias y evidencia.", 8)
rows = [
    ("Decisión", "Alternativa evaluada", "Trade-off aceptado"),
    ("Monolito modular MVT", "Microservicios / SOA", "Un solo despliegue; menos independencia, más consistencia transaccional."),
    ("Templates Django + JSON mínimo", "SPA + DRF", "Menos superficie y estado en el cliente; menos interactividad rica."),
    ("SQLite dev / PostgreSQL prod", "Una sola base para todo", "Demo simple; producción requiere Postgres para concurrencia real."),
    ("Servicios de dominio explícitos", "Señales globales", "Más código explícito; eventos sin duplicados ni efectos ocultos."),
]
tbl = s.shapes.add_table(len(rows), 3, Inches(0.55), Inches(1.95), Inches(12.2), Inches(3.85)).table
tbl.columns[0].width = Inches(3.3)
tbl.columns[1].width = Inches(3.1)
tbl.columns[2].width = Inches(5.8)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.text = val
        cell.margin_left = Inches(0.1); cell.margin_right = Inches(0.1)
        cell.margin_top = Inches(0.05); cell.margin_bottom = Inches(0.05)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:
            p.line_spacing = 1.0
            for run in p.runs:
                run.font.name = FONT_B if r == 0 else FONT
                run.font.size = Pt(10.5 if r == 0 else 9.2)
                run.font.bold = r == 0
                run.font.color.rgb = WHITE if r == 0 else NAVY
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r == 0 else (WHITE if r % 2 else SOFT_GRAY)
text(s, 0.55, 6.05, 12.2, 0.3, "La decisión no es “Django es mejor”: es que el contexto no justificaba el costo operativo de microservicios.",
     10.2, GRAY, False)
tag(s, 0.55, 6.55, 2.2, "ADR-01 a ADR-10", SOFT_AMBER, NAVY)
s.notes_slide.notes_text_frame.text = "Juan: explicar el trade-off, no la tecnología. La consistencia transaccional era el requisito dominante."

# ---------------------------------------------------------------------------
# 9. ISO 25010
# ---------------------------------------------------------------------------
s = blank()
header(s, "08 · Calidad", "ISO/IEC 25010: medimos lo que podemos defender",
       "Evidencia real en base de pruebas aislada; los límites se declaran, no se maquillan.", 9)
quality = [
    ("Eficiencia de desempeño", ["Landing: 2.8 ms · 0 consultas", "Dashboard cliente: 14.8 ms · 9", "Trazabilidad: 28.1 ms · 32", "API reserva: 15.6 ms"], TEAL),
    ("Seguridad", ["Matriz 5 roles × portales", "IDOR: 404 / 403", "CSRF + contraseñas", "Adjuntos autorizados"], GREEN),
    ("Mantenibilidad", ["3 apps + servicios", "107 pruebas / 18 clases", "Migraciones al día", "Documentación por fase"], AMBER),
    ("Usabilidad", ["5 paneles por rol", "Responsive 390–1440", "Estados vacíos honestos", "Feedback y confirmaciones"], GRAY),
]
for i, (title, items, accent) in enumerate(quality):
    x = 0.55 + i * 3.15
    rect(s, x, 1.95, 2.9, 3.6, WHITE, accent)
    text(s, x + 0.18, 2.08, 2.55, 0.55, title, 12, NAVY, True, font=FONT_B)
    text(s, x + 0.18, 2.7, 2.55, 2.6, "\n".join("• " + it for it in items), 9.2, GRAY)
rect(s, 0.55, 5.8, 12.2, 0.8, SOFT_AMBER, AMBER)
text(s, 0.72, 5.9, 11.8, 0.6,
     "Lectura honesta: no hay prueba de carga ni cobertura formal; los tiempos son locales y la muestra es pequeña. El límite se declara en el documento.",
     9.5, RGBColor(0x5F, 0x4A, 0x00))
text(s, 0.55, 6.75, 12.0, 0.25, "Priorizados: Eficiencia de desempeño · Seguridad · Mantenibilidad · Usabilidad.", 9.5, TEAL, True, font=FONT_B)
s.notes_slide.notes_text_frame.text = "Santiago: 107 pruebas y mediciones reales; no afirmamos más de lo que podemos probar."

# ---------------------------------------------------------------------------
# 10. Escalabilidad
# ---------------------------------------------------------------------------
s = blank()
header(s, "09 · Escalabilidad", "¿Qué pasaría si mañana se multiplican usuarios y solicitudes?",
       "La respuesta no es “Django escala solo”: identificamos cuellos de botella y una ruta por fases.", 10)
text(s, 0.6, 1.95, 4.8, 0.3, "CUELLOS DE BOTELLA HOY", 9.5, RGBColor(0xC0, 0x39, 0x2B), True, font=FONT_B)
bottlenecks = ["SQLite: un solo escritor", "WSGI síncrono: un request por worker", "Media local sin CDN", "Sin caché ni colas de tareas"]
for i, item in enumerate(bottlenecks):
    y = 2.35 + i * 0.7
    rect(s, 0.6, y, 4.7, 0.5, RGBColor(0xFD, 0xE0, 0xE0), RGBColor(0xD3, 0x2F, 0x2F))
    text(s, 0.75, y + 0.12, 4.4, 0.25, item, 10, RGBColor(0x8B, 0x1A, 0x1A), True, font=FONT_B)
text(s, 5.8, 1.95, 6.8, 0.3, "RUTA DE ESCALAMIENTO", 9.5, GREEN, True, font=FONT_B)
phases = [
    ("Fase 1", "PostgreSQL + PgBouncer + Gunicorn + Nginx"),
    ("Fase 2", "Redis (caché/sesiones) + tareas async + S3/CDN"),
    ("Fase 3", "Réplicas de lectura + servicios extraídos + observabilidad"),
]
for i, (phase, desc) in enumerate(phases):
    y = 2.35 + i * 0.95
    rect(s, 5.8, y, 6.9, 0.75, SOFT_GREEN if i == 0 else (SOFT_TEAL if i == 1 else SOFT_GRAY), GREEN if i == 0 else (TEAL if i == 1 else GRAY))
    text(s, 5.95, y + 0.1, 1.0, 0.25, phase, 9.5, GREEN if i == 0 else (TEAL if i == 1 else GRAY), True, font=FONT_B)
    text(s, 7.0, y + 0.1, 5.5, 0.5, desc, 10.5, NAVY, True, font=FONT_B)
text(s, 5.8, 5.35, 6.9, 0.9,
     "El límite modular permite extraer identidad, notificaciones o reportes como servicios sin reescribir el dominio.",
     10.2, GRAY)
rect(s, 0.6, 6.35, 12.1, 0.55, SOFT_AMBER, AMBER)
text(s, 0.75, 6.43, 11.8, 0.4,
     "Decisión: no escalar antes de medir. Primero Postgres y workers; después caché, asincronía y almacenamiento externo.",
     9.3, RGBColor(0x5F, 0x4A, 0x00))
s.notes_slide.notes_text_frame.text = "Juan: responder con bottlenecks concretos y una ruta, no con una promesa abstracta."

# ---------------------------------------------------------------------------
# 11. Despliegue
# ---------------------------------------------------------------------------
s = blank()
header(s, "10 · Despliegue", "De GitHub a producción con límites claros",
       "El mismo código, dos entornos: demo local reproducible y producción con Postgres, WSGI y HTTPS.", 11)
# Dev
rect(s, 0.55, 1.95, 5.7, 3.7, SOFT_TEAL, TEAL)
text(s, 0.75, 2.05, 5.2, 0.3, "DESARROLLO LOCAL", 9.5, TEAL, True, font=FONT_B)
text(s, 0.75, 2.35, 5.2, 0.3, "Windows · venv raíz", 12, NAVY, True, font=FONT_B)
text(s, 0.75, 2.7, 5.1, 2.6,
     "runserver :8000\n↓\nSQLite db.sqlite3\n↓\nMEDIA_ROOT local\n\nseed_demo idempotente\n107 pruebas en base aislada",
     10.2, NAVY)
# Prod
rect(s, 6.55, 1.95, 6.25, 3.7, SOFT_GREEN, GREEN)
text(s, 6.75, 2.05, 5.8, 0.3, "PRODUCCIÓN", 9.5, GREEN, True, font=FONT_B)
prod = [
    ("GitHub", "origin/main"),
    ("Nginx", "HTTPS · proxy"),
    ("Gunicorn / uWSGI", "workers WSGI"),
    ("Django 5", "config.wsgi"),
    ("PostgreSQL", "DATABASE_URL"),
    ("MEDIA_ROOT", "volumen / S3 futuro"),
]
for i, (name, desc) in enumerate(prod):
    x = 6.75 + (i % 3) * 1.9
    y = 2.45 + (i // 3) * 1.15
    rect(s, x, y, 1.75, 0.75, WHITE, GREEN)
    text(s, x + 0.08, y + 0.08, 1.6, 0.22, name, 8.5, NAVY, True, font=FONT_B)
    text(s, x + 0.08, y + 0.32, 1.6, 0.35, desc, 7.2, GRAY)
text(s, 6.75, 4.9, 5.8, 0.55, "DJANGO_ENV=produccion · DJANGO_SECRET_KEY · ALLOWED_HOSTS · HSTS · cookies seguras", 8.3, GRAY)
rect(s, 0.55, 5.9, 12.25, 0.7, SOFT_AMBER, AMBER)
text(s, 0.72, 6.0, 11.9, 0.5,
     "Límite actual: no hay Docker, Procfile ni CI/CD; el despliegue es manual y las dependencias no están pinneadas. Está documentado como trabajo futuro.",
     9.4, RGBColor(0x5F, 0x4A, 0x00))
s.notes_slide.notes_text_frame.text = "Santiago: el mismo Django, sin reescritura; la diferencia es la infraestructura y el endurecimiento."

# ---------------------------------------------------------------------------
# 12. Demo
# ---------------------------------------------------------------------------
s = blank()
header(s, "11 · Demostración", "La arquitectura se demuestra operándola",
       "1:05 min · cada clic se conecta con una vista, un servicio y una tabla/evento.", 12)
shots = [
    ("demo_cliente.png", "1 · Cliente", "Seguimiento: vista + CitaAsesoria + CitaEvento"),
    ("demo_docente.png", "2 · Docente", "Entrega: publicar_entrega + CitaInteraccion + evento"),
    ("demo_director.png", "3 · Director", "Indicadores: agregaciones ORM + CSV"),
]
for i, (name, label, cue) in enumerate(shots):
    x = 0.55 + i * 4.2
    add_picture_fit(s, BASE / "evidencias" / name, x, 1.95, w=3.7)
    tag(s, x, 4.75, 1.4, label, SOFT_TEAL, NAVY, 9)
    text(s, x, 5.15, 3.9, 0.7, cue, 9.5, GRAY)
rect(s, 0.55, 6.15, 12.2, 0.55, SOFT_AMBER, AMBER)
text(s, 0.72, 6.23, 11.8, 0.4,
     "Respaldo: video de 2 min + capturas de las fases 03/04. Si falla la red, se demuestra con evidencia visual.",
     9.2, RGBColor(0x5F, 0x4A, 0x00))
s.notes_slide.notes_text_frame.text = "Juan opera; Santiago narra el componente y la regla. El objetivo no es mostrar pantallas, sino el recorrido de datos."

# ---------------------------------------------------------------------------
# 13. Cierre
# ---------------------------------------------------------------------------
s = blank()
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SW), Inches(SH))
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.14), Inches(SH))
bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
text(s, 0.72, 0.7, 11.5, 0.3, "CIERRE", 11, TEAL, True, font=FONT_B)
text(s, 0.72, 1.05, 11.5, 0.9, "Un sistema funcional, trazable\ny con límites honestos", 34, WHITE, True, font=FONT_B, line_spacing=1.0)
text(s, 0.72, 2.55, 11.0, 0.5, "La arquitectura es adecuada para el contexto y tiene una ruta clara de evolución.", 15,
     RGBColor(0xD7, 0xE2, 0xEE))
metrics = [("107/107", "pruebas OK"), ("8", "modelos reales"), ("5", "estados formales")]
for i, (num, label) in enumerate(metrics):
    x = 0.72 + i * 4.0
    text(s, x, 3.6, 3.4, 0.8, num, 40, GREEN if i == 0 else (TEAL if i == 1 else AMBER), True, font=FONT_B)
    text(s, x, 4.4, 3.4, 0.3, label, 12, RGBColor(0xCF, 0xDA, 0xE6))
text(s, 0.72, 5.35, 11.4, 0.3, "LÍMITES DECLARADOS", 9.5, TEAL, True, font=FONT_B)
text(s, 0.72, 5.65, 11.4, 0.8,
     "I-5 MIXTO · SEG-14/21/22/23 · sin CI/CD ni pruebas de carga · media local · FullCalendar por CDN.",
     11.5, RGBColor(0xD7, 0xE2, 0xEE))
text(s, 0.72, 6.75, 11.4, 0.3, "No defiendan un diagrama. Defiendan las decisiones que lo hicieron posible.", 10, TEAL, True, font=FONT_B)
s.notes_slide.notes_text_frame.text = "Juan: cerrar con resultados, límites y evolución; no prometer lo que no está implementado."

# ---------------------------------------------------------------------------
# R1. Respaldo ER
# ---------------------------------------------------------------------------
s = blank()
header(s, "RESPALDO · R1", "Modelo ER real: 8 entidades", "Diagrama generado desde backend/accounts/models.py y backend/scheduling/models.py.", 14)
add_picture_fit(s, DIAG / "08_er_real.png", 0.35, 1.9, h=5.1)
bullets(s, 7.4, 2.0, 5.4, 4.6, [
    "Empresa 1–N CustomUser.",
    "CustomUser 1–1 PerfilEstudiante (solo estudiantes).",
    "FranjaHoraria 1–N CitaAsesoria.",
    "CitaAsesoria 1–N NotaBitacora, CitaEvento y CitaInteraccion.",
    "UniqueConstraint parcial (franja, cliente) en estados activos.",
], 9.8, NAVY, 5)
s.notes_slide.notes_text_frame.text = "Respaldo para preguntas sobre el modelo de datos."

# ---------------------------------------------------------------------------
# R2. Matriz de seguridad
# ---------------------------------------------------------------------------
s = blank()
header(s, "RESPALDO · R2", "Matriz de seguridad y control de acceso", "Rutas y acciones permitidas por rol; el servidor fuerza el alcance.", 15)
rows = [
    ("Rol", "Landing / login", "Mis solicitudes", "Detalle del caso", "Asignar", "Trazabilidad", "Admin"),
    ("Cliente", "✓", "Solo propias", "Solo propias", "—", "—", "—"),
    ("Estudiante", "✓", "Casos de apoyo", "Solo asignados", "—", "—", "—"),
    ("Docente", "✓", "Casos asignados", "Solo asignados", "—", "—", "—"),
    ("Coordinador", "✓", "Bandeja del área", "Solo su área", "Sí, su área", "Solo su área", "—"),
    ("Director", "✓", "Global", "Global (solo lectura)", "—", "Global", "Si es staff"),
]
tbl = s.shapes.add_table(len(rows), 7, Inches(0.5), Inches(1.95), Inches(12.3), Inches(3.3)).table
widths = [1.35, 1.5, 1.8, 2.0, 1.5, 1.7, 1.5]
for i, w in enumerate(widths):
    tbl.columns[i].width = Inches(w)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.07); cell.margin_right = Inches(0.07)
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for run in p.runs:
                run.font.name = FONT_B if r == 0 or c == 0 else FONT
                run.font.size = Pt(8.8 if r == 0 else 8.5)
                run.font.bold = r == 0 or c == 0
                run.font.color.rgb = WHITE if r == 0 else NAVY
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r == 0 else (WHITE if r % 2 else SOFT_GRAY)
bullets(s, 0.6, 5.55, 12.0, 1.2, [
    "Controles: role_required, login con portal esperado, IDOR (404), CSRF, validadores de contraseña, adjuntos con vista autorizada.",
    "El admin es solo para staff y el historial de eventos es de solo lectura; los cambios de estado pasan por el mismo servicio auditado.",
], 9.5, GRAY, 3)
s.notes_slide.notes_text_frame.text = "Respaldo para preguntas de seguridad."

# ---------------------------------------------------------------------------
# R3. Evidencia de pruebas
# ---------------------------------------------------------------------------
s = blank()
header(s, "RESPALDO · R3", "Evidencia: 107 pruebas automatizadas", "Suite ejecutada en base aislada; el db.sqlite3 de desarrollo no se toca.", 16)
text(s, 0.6, 1.9, 4.0, 1.0, "107/107", 48, GREEN, True, font=FONT_B)
text(s, 0.6, 2.85, 4.0, 0.35, "pruebas OK · 18 clases", 12, NAVY, True)
text(s, 0.6, 3.35, 5.2, 0.3, "manage.py test", 9.5, GRAY, True, font=FONT_B)
rect(s, 0.6, 3.7, 5.4, 1.3, NAVY, NAVY, False)
text(s, 0.78, 3.82, 5.0, 1.05, "Ran 107 tests in 67.524s\n\nOK", 12, WHITE, False, font="Consolas", line_spacing=1.2)
text(s, 6.4, 1.95, 6.2, 0.3, "COBERTURA FUNCIONAL", 9.5, TEAL, True, font=FONT_B)
cats = [
    "Matriz de roles 5×5 y login por portal",
    "Reservas, cupos, 409 y constraint única",
    "Máquina de estados y transiciones formales",
    "IDOR y aislamiento por área",
    "Seed idempotente y comandos",
    "Trazabilidad, eventos y transacción fallida",
    "Indicadores, filtros y CSV",
    "Seguimiento, interacciones y aprobaciones",
]
bullets(s, 6.4, 2.3, 6.2, 2.7, cats, 9.8, NAVY, 3)
rect(s, 6.4, 5.15, 6.2, 0.9, SOFT_AMBER, AMBER)
text(s, 6.55, 5.24, 5.9, 0.7,
     "Comandos de cierre: check 0 issues · makemigrations sin cambios · seed_demo idempotente · 107/107 tests.",
     9.2, RGBColor(0x5F, 0x4A, 0x00))
text(s, 0.6, 6.45, 12.0, 0.4, "Evidencia completa: docs/sustentacion/evidencias/fase0_test.txt", 9, GRAY)
s.notes_slide.notes_text_frame.text = "Respaldo para preguntas sobre pruebas y calidad."

prs.save(str(OUT))
print(f"PPTX generado: {OUT} ({OUT.stat().st_size/1024/1024:.1f} MB)")
