# Implementación visual — Fase 03 (Módulo A)

## Qué cambió

**Landing (`backend/templates/portal/landing.html`, reescrita):**

| Sección | Contenido | Fuente de verdad |
|---|---|---|
| Hero | Titular concreto ("Asesorías de ingeniería y tecnología para el Tolima"), propuesta institucional, CTA primario *Solicitar una asesoría* → registro, secundario *Ver cómo funciona* → ancla `#proceso`, barra de 3 hechos | Los "8 especialidades técnicas" salen de `Subespecialidad.POR_AREA` (2×4 del catálogo real, pasado por contexto de la vista) |
| Servicios (`#servicios`) | Tarjeta por área (Sistemas/Civil) con foto, descripción, chips de especialidades y los 2 tipos de servicio con su responsable | `portal/views.py::landing` construye `catalogo` desde el código real, no texto plano |
| Cómo funciona (`#proceso`) | 5 pasos numerados + columna visual con los **4 estados reales** del flujo | Coinciden 1:1 con `CitaAsesoria.Estado` y las vistas portal/docente/acta/feedback |
| Banda "Gestión con evidencia" | Beneficios reales del sistema (centralización, responsables, historial, indicadores) | Todos implementados (Módulo C) |
| Quiénes somos / Líneas / Ventajas / Beneficios / Portales | Contenido institucional del manual CITI, conservado | Enlaces solo a rutas existentes |
| Banners ×2 | *Solicita una asesoría* → `/cuenta/registro/`; *Conoce nuestras áreas* → `#servicios` | Sin enlaces inventados; sin teléfonos/redes falsos |
| Footer | Identidad + navegación + línea de créditos de fotografía | — |

**Navegación:** los paneles de los 5 roles tienen ahora sidebar con enlaces reales (`dashboard_base` → bloque `sidebar_nav` rellenado en cada plantilla): el director enlaza *Resumen ejecutivo / Trazabilidad / Administración*; el coordinador, *Bandeja / Trazabilidad de mi área*.

**CSS (`backend/static/css/styles.css`, bloques nuevos):** hero editorial (kicker, barra de hechos, foto con etiqueta), `servicios-grid`, `proceso-steps`, banda oscura institucional, banners con gradiente+texto, timeline de eventos, paneles ejecutivos (`exec-grid`, `chart-bar`, `evo-chart`, `chip`, `metric`), menú móvil con hamburguesa accesible (`aria-expanded`). Se conserva todo el sistema existente (paleta UCC, tipografía Open Sans).

**Cache-busting:** `base.html` añade `?v=2026-11-08-a` a los CSS. *(Aprendizaje operativo de la fase: `runserver --noreload` NO recarga código Python (vistas/models); con DEBUG=True las plantillas sí se recargan desde disco. La verificación visual debe hacerse contra un proceso recién iniciado tras cada cambio de código, y conviene comprobar que exista un único servidor escuchando en el puerto.)*

## Imágenes

| Archivo (`backend/static/images/landing/`) | Uso | Origen/licencia |
|---|---|---|
| hero-equipo.jpg | Hero | Pexels ID 3863830 — licencia Pexels (uso libre, sin atribución obligatoria) |
| area-sistemas.jpg | Servicios · Sistemas | Pexels ID 7693685 |
| area-civil.jpg | Servicios · Civil | Pexels ID 6615107 (maqueta arquitectónica) |
| proceso-revision.jpg | Cómo funciona | Pexels ID 8117476 (revisión de planos) |
| banner-asesoria.jpg | Banner registro | Pexels ID 7108210 |
| banner-campo.jpg | Banner áreas | Pexels ID 8961260 (obra civil, amplia) |
| reportes-manos.jpg | Banda gestión | Pexels ID 3184292 (mesa de reportes) |

Criterios aplicados: fotografía profesional >1200px, tema ingeniería/consultoría/investigación, sin marcas institucionales falsas (verificado visualmente una a una; se descartaron candidatas con logotipo legible o contenido ajeno al tema). Locales en `static/`: la demo no depende de servicios externos (FullCalendar CDN del portal cliente sigue siendo externo y sigue condicionado a red — véase pendientes). Logo UCC y organigrama: activos institucionales preexistentes, no redibujados.

## Responsive

Verificado con navegador real (Playwright MCP) en 1440, 820 y 390: sin desbordamientos horizontales (`scrollWidth ≤ viewport`), menú hamburguesa operativo (6 enlaces, `aria-expanded` alternante), tarjetas 2→1 col, foto hero con `aspect-ratio` y `object-fit`, CTA full-width en móvil, hamburguesa con animación de cierre. Capturas: `p3-landing-hero-1440.png`, `p3-landing-full-1440.png`, `p3-landing-390-fold.png`, `p3-landing-390-menu.png`.

## Archivos tocados (Módulo A)

- `backend/templates/portal/landing.html` (reescrito)
- `backend/templates/base.html` (cache-busting)
- `backend/static/css/styles.css` (bloques nuevos; sin tocar reglas existentes)
- `backend/static/images/landing/*` (7 archivos nuevos + descartes eliminados)
- `backend/portal/views.py` (contexto `landing`: catálogo real y especialidades)
