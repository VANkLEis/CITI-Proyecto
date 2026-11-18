"""Genera el diagrama 02 de casos de uso en 5 paneles por actor (PNG compuesto).

Uso:
  <venv-docs>/python.exe docs/sustentacion/scripts/gen_use_cases.py

Requiere Java + plantuml.jar (PLANTUML_JAR) y Pillow.
"""
from __future__ import annotations

import os
import subprocess
from puml_clean import clean
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "sustentacion"
FUENTES = BASE / "fuentes"
SALIDA = BASE / "diagramas"
JAR = Path(os.environ.get("PLANTUML_JAR", r"C:\Users\Santiago\AppData\Local\Temp\opencode\plantuml.jar"))
FUENTES.mkdir(parents=True, exist_ok=True)
SALIDA.mkdir(parents=True, exist_ok=True)

COMMON = r"""
skinparam backgroundColor #FFFFFF
skinparam shadowing false
skinparam defaultFontName "Segoe UI"
skinparam defaultFontSize 18
skinparam dpi 200
skinparam ArrowColor #5F6B7A
skinparam ArrowThickness 1.4
skinparam actorBackgroundColor #E8F6FA
skinparam actorBorderColor #00ACC9
skinparam actorFontColor #132740
skinparam usecaseBackgroundColor #F7FAFC
skinparam usecaseBorderColor #00ACC9
skinparam usecaseFontColor #132740
skinparam packageBackgroundColor #FFFFFF
skinparam packageBorderColor #DDE3EA
skinparam noteBackgroundColor #FFF8E1
skinparam noteBorderColor #D99A00
"""

PANELS = {
    "02a_cliente": ("Cliente / Empresa", [
        ("uc01", "UC-01\\nRegistrarse / iniciar sesión"),
        ("uc02", "UC-02\\nSolicitar asesoría o consultoría"),
        ("uc03", "UC-03\\nConsultar mis solicitudes\\ny seguimiento"),
        ("uc04", "UC-04\\nComentar / solicitar ajuste"),
        ("uc05", "UC-05\\nAprobar o rechazar entregable"),
        ("uc06", "UC-06\\nCancelar solicitud"),
    ]),
    "02b_estudiante": ("Estudiante (consultor / tutor)", [
        ("uc07", "UC-07\\nRegistrar bitácora de apoyo"),
        ("uc08", "UC-08\\nConsultar casos de apoyo"),
    ]),
    "02c_docente": ("Docente asesor", [
        ("uc09", "UC-09\\nGestionar caso y publicar entregable"),
        ("uc10", "UC-10\\nEmitir acta de cierre"),
    ]),
    "02d_coordinador": ("Coordinador de área", [
        ("uc11", "UC-11\\nRevisar bandeja y asignar responsables"),
        ("uc12", "UC-12\\nSeguimiento e interacciones de su área"),
        ("uc13", "UC-13\\nConsultar trazabilidad y exportar CSV"),
    ]),
    "02e_director": ("Director CITI", [
        ("uc13", "UC-13\\nConsultar trazabilidad y exportar CSV"),
        ("uc14", "UC-14\\nPanel ejecutivo e indicadores"),
        ("uc15", "UC-15\\nAdministrar registros"),
    ]),
}


def source_for(actor: str, cases: list[tuple[str, str]]) -> str:
    lines = [
        "@startuml",
        f"title <b>{actor}</b>",
        "left to right direction",
        COMMON.strip(),
        f'actor "{actor}" as actor',
        'rectangle "Sistema CITI" {',
    ]
    for alias, label in cases:
        lines.append(f'  usecase "{label}" as {alias}')
    lines.append("}")
    for alias, _ in cases:
        lines.append(f"actor --> {alias}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def render(name: str, source: str) -> Path:
    puml = FUENTES / f"{name}.puml"
    puml.write_text(clean(source), encoding="utf-8")
    subprocess.run(
        ["java", "-Dfile.encoding=UTF-8", "-DPLANTUML_LIMIT_SIZE=16384",
         "-jar", str(JAR), "-charset", "UTF-8", "-tpng", "-o", str(SALIDA), str(puml)],
        check=True, capture_output=True, text=True,
    )
    return SALIDA / f"{name}.png"


def trim(im: Image.Image, margin: int = 30) -> Image.Image:
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, "white")
    from PIL import ImageChops
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        im = im.crop(bbox)
    out = Image.new("RGB", (im.width + margin * 2, im.height + margin * 2), "white")
    out.paste(im, (margin, margin))
    return out


def main() -> None:
    panels = []
    for name, (actor, cases) in PANELS.items():
        panels.append((actor, render(name, source_for(actor, cases))))

    # Lienzo 3x2: 5 paneles + una celda de lectura.
    canvas = Image.new("RGB", (4200, 3000), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 54)
    sub_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 30)
    cell_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 34)
    body_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
    draw.text((80, 40), "CITI · Casos de uso reales por actor", fill="#132740", font=title_font)
    draw.text((80, 105), "Cinco roles vigentes; cada óvalo es un caso de uso implementado.",
              fill="#5F6B7A", font=sub_font)
    draw.line((80, 155, 4120, 155), fill="#DDE3EA", width=3)

    cells = [(80, 190), (1460, 190), (2840, 190), (80, 1580), (1460, 1580), (2840, 1580)]
    cell_w, cell_h = 1260, 1250
    for (actor, path), (x, y) in zip(panels, cells):
        im = trim(Image.open(path))
        scale = min((cell_w - 30) / im.width, (cell_h - 30) / im.height, 1.6)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        # Tarjeta con borde suave
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=18,
                               outline="#DDE3EA", width=2, fill="#FFFFFF")
        px = x + (cell_w - im.width) // 2
        py = y + 20 + (cell_h - 20 - im.height) // 2
        canvas.paste(im, (px, py))

    # Celda de lectura
    x, y = cells[-1]
    draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=18,
                           outline="#DDE3EA", width=2, fill="#FFF8E1")
    draw.text((x + 30, y + 30), "Cómo leer este diagrama", fill="#132740", font=cell_font)
    notes = [
        "• UC-13 lo comparten coordinador y director.",
        "• El coordinador solo ve su área.",
        "• El director tiene alcance global.",
        "• El cliente solo ve sus solicitudes.",
        "• El docente solo ve casos asignados.",
        "• El estudiante solo ve casos de apoyo.",
    ]
    for i, line in enumerate(notes):
        draw.text((x + 30, y + 110 + i * 58), line, fill="#5F4A00", font=body_font)

    out = SALIDA / "02_casos_uso.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"{out.name}: {canvas.width}x{canvas.height} ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
