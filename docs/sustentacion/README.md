# Sustentación final · CITI UCC

Artefactos de la entrega de **Arquitectura y Modelamiento de Software** (noviembre de 2026).
El sistema implementado vive en `backend/`; esta carpeta conserva las fuentes,
diagramas y evidencias, mientras que los entregables finales están en
[`../presentacion/`](../presentacion/).

## Entregables

El paquete final vive en [`../presentacion/`](../presentacion/) para evitar copias duplicadas:

| Archivo | Contenido |
|---|---|
| [`CITI_Sustentacion_Final.pptx`](../presentacion/CITI_Sustentacion_Final.pptx) | 13 diapositivas principales + R1–R3 de respaldo, 16:9, notas del expositor |
| [`CITI_Sustentacion_Final.pdf`](../presentacion/CITI_Sustentacion_Final.pdf) | Exportación fiel de la presentación (16 páginas) |
| [`Guion_Sustentacion_10min.docx`](../presentacion/Guion_Sustentacion_10min.docx) | Guion palabra por palabra, cronograma 9:00 + 0:30, demo y banco de preguntas |
| [`Documentacion_Arquitectura_CITI_UCC.docx`](../presentacion/Documentacion_Arquitectura_CITI_UCC.docx) | Documento maestro: portada, TOC, índices, 13 capítulos, ADRs, ISO 25010 y anexos |
| [`Documentacion_Arquitectura_CITI_UCC.pdf`](../presentacion/Documentacion_Arquitectura_CITI_UCC.pdf) | Exportación del documento maestro (53 páginas) |

Esta carpeta conserva el material de apoyo (`diagramas/`, `fuentes/`, `evidencias/`, `scripts/`) y la versión [`Guion_Sustentacion_10min.pdf`](Guion_Sustentacion_10min.pdf).

## Contenido de apoyo

- `diagramas/`: 9 PNG de alta resolución (contexto, casos de uso, componentes, capas, dos secuencias, estados, ER y despliegue).
- `fuentes/`: fuentes PlantUML versionables de cada diagrama.
- `evidencias/`: salidas de `check`, `makemigrations` y las 107 pruebas; métricas de rendimiento; capturas de la demo y del modelado inicial.
- `scripts/`: generadores reproducibles de diagramas, presentación, guion y documento.

## Verificación de cierre

- `manage.py check`: 0 issues.
- `manage.py makemigrations --check --dry-run`: sin cambios.
- `manage.py test`: **201/201 OK** (base de pruebas aislada).
- Sin modificaciones en la lógica de negocio, modelos ni vistas de `backend/`.

## Reproducción

```powershell
# DESDE backend/
..\venv\Scripts\python.exe manage.py check
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test

# DESDE la raíz, con el venv temporal de documentación
& "$env:TEMP\opencode\citi_docs_venv\Scripts\python.exe" docs\sustentacion\scripts\gen_diagrams.py
& "$env:TEMP\opencode\citi_docs_venv\Scripts\python.exe" docs\sustentacion\scripts\gen_use_cases.py
& "$env:TEMP\opencode\citi_docs_venv\Scripts\python.exe" docs\sustentacion\scripts\build_deck.py
& "$env:TEMP\opencode\citi_docs_venv\Scripts\python.exe" docs\sustentacion\scripts\build_guion.py
& "$env:TEMP\opencode\citi_docs_venv\Scripts\python.exe" docs\sustentacion\scripts\build_doc.py
```

Los PDF se exportan con Microsoft Word/PowerPoint (COM); los `.docx`/`.pptx` son la fuente editable.
