# Implementación de trazabilidad — Fase 03 (Módulo C)

## Modelo de eventos

**`scheduling.CitaEvento`** (nueva, migración `0004_citaasesoria_asignada_en_citaasesoria_cerrada_en_and_more` — *justificación*: nueva tabla de historial + dos campos nullable de marcas temporales en `CitaAsesoria`; sin alteraciones destructivas, todas aditivas):

| Campo | Tipo | Notas |
|---|---|---|
| `cita` | FK `CitaAsesoria` related `eventos` | CASCADE |
| `usuario` | FK SET_NULL | actor responsable; se conserva aunque el usuario se elimine |
| `actor_label` | CharField (instantánea) | correo/nombre al momento del hecho; legible sin usuario |
| `tipo` | choices | `creada`, `revisada`, `docente_asignado`, `tutor_asignado`, `asignada`, `iniciada`, `estado_cambiado`, `archivo_adjuntado`, `finalizada`, `acta_registrada`, `feedback`, `cancelada`, `bitacora` |
| `estado_anterior` / `estado_nuevo` | Char choices blank | trazado del cambio |
| `descripcion` | Text | qué ocurrió, en español |
| `metadata` | JSONField null | estructurados cuando aporta (p. ej. calificación) |
| `fecha` | DateTime auto_now_add + index | |

Índice compuesto `(cita, fecha)`; orden por defecto cronológico.

**Nuevas marcas en `CitaAsesoria`**: `asignada_en`, `cerrada_en` (nullable, `editable=False`). Se escriben SOLO cuando la transición ocurre de verdad (portal, API, admin o reubicación del seed). Base de los promedios de tiempos.

## Registro centralizado (no señales)

Módulo `backend/scheduling/trazabilidad.py` — API única usada por TODAS las mutaciones:

- `registrar_evento(cita, actor, tipo, …)` — crea el evento (actor puede ser None → `actor_label='sistema'`).
- `cambio_estado(cita, usuario, nuevo, desc)` — transición validada (`full_clean`) + marca temporal (`asignada_en`/`cerrada_en`) + evento. **Si `full_clean` falla, la transacción revierte: nunca queda evento de éxito de una operación fallida.**
- `asignar_cita(...)` — eventos `docente_asignado`, `tutor_asignado` y transición `asignada` en un bloque atómico.
- `nota_asignacion(...)` — deja `revisada` la primera vez que el coordinador abre la bandeja/asignación de esa solicitud (idempotente por usuario+cita).
- `auditar_guardado_form(...)` — tras `ModelForm.save()` del portal: captura TOMADA **antes** de instanciar el form con data (un ModelForm con `instance` muta la instancia en `is_valid()` — bug real detectado en validación visual y cubierto por regresión), registra `estado_cambiado`/`tutor_asignado` solo si cambiaron de verdad, y **nunca** inventa eventos si no hubo diferencia.

Puntos de instrumentación (todos dentro de `transaction.atomic()` cuando hay ≥2 escrituras):

| Acción | Dónde | Eventos |
|---|---|---|
| Reserva API | `scheduling/views.reservar_cita_api` (+ `select_for_update` de la franja) | `creada`, `archivo_adjuntado` si trae documento |
| Apertura bandeja/asignación (GET) | `portal/views.coordinador_asignar` y `cita_detalle_interactivo` | `revisada` (una vez) |
| Asignación | ambas vistas coordinador (página y modal) | `docente_asignado`, `tutor_asignado`, `asignada` |
| Acción rápida docente | `docente_caso_detalle` y modal | `iniciada` / `finalizada` / con anterior→nuevo |
| Gestión form docente | ambas vistas | `estado_cambiado`, `tutor_asignado`, `bitacora` (nota de avance) |
| Emisión de acta | `docente_generar_acta` | `acta_registrada` (solo la 1ª vez) |
| Bitácora del tutor | `estudiante_caso_nota` y modal | `bitacora` |
| Feedback cliente | `cliente_feedback` | `feedback` (con metadata calificación) |
| Acciones admin | `CitaAsesoriaAdmin.save_model/cancelar/marcar_revisadas` | los mismos tipos, actor = usuario admin |

## Línea de tiempo por solicitud

`templates/portal/partials/cita_eventos.html`, incluido en `cita_info_block.html` → visible en: modal de detalle de los 4 roles, página completa del docente, y bandeja del coordinador. Reglas visuales: punto verde=creada, azul=coordinación, teal=inicio, verde-oscuro=cierre/acta, naranja=feedback, rojo=cancelación. **Sin eventos registrados (citas anteriores a esta versión): muestra el aviso honesto** "El seguimiento histórico no estaba habilitado cuando se creó esta solicitud. Los cambios que se registren desde ahora aparecerán aquí." — no se reescribe historia falsa.

## Dashboard de trazabilidad

`GET /panel/trazabilidad/` — rol **Director** (global) y **Coordinador** (aislado a su área forzada en servidor: `area_forzada` ignora el parámetro `area` ajeno; el filtro de área se muestra deshabilitado). Componentes:

- 6 KPIs de estado; 4 indicadores de resultado con fórmulas y `n` visibles;
- gráficos: por estado, evolución 6 meses (recibidas vs finalizadas por mes de `creada_en`/`cerrada_en`), servicios top, área (solo áreas con flujo operativo);
- tabla de resultados con resolución (`CitaAsesoria.resolucion_txt`);
- filtros combinables (periodo 7/30/90/año/custom desde-hasta inclusive, área, estado, tipo de servicio, responsable) aplicados uniformemente a tarjetas, gráficos, tabla y CSV mediante una única función `parse_filtros` → `queryset` base agregado con `Count/aggregate` y `values_list` (sin N+1: los promedios recorren un `values_list` único).

**Fórmulas (documentadas en el propio módulo `portal/indicadores.py`)**:

```
tasa_finalización = finalizadas / recibidas × 100          (canceladas cuentan como recibidas, nunca como atendidas)
asignación_prom   = media(asignada_en − creada_en) sobre citas del periodo con marca
resolución_prom   = media(cerrada_en − creada_en) sobre finalizadas con ambas marcas
"No disponible"   cuando n < 1 (se muestra literal, nunca se estima)
```

## CSV

`GET /panel/trazabilidad/exportar.csv?<mismos filtros>` → `trazabilidad_csv`: mismo parse de permisos y filtros; 2 líneas de contexto (período + área + generado por/quién sin correos), 13 columnas de gestión (código, estado, empresa —nunca contacto personal—, área, servicio, tipo, docente, tutor, fechas, días de resolución, valoración). Codificación UTF-8 con BOM para Excel. El botón "Exportar CSV" propaga la querystring activa.

## Integridad y permisos

- Escritura de eventos exclusivamente desde backend; `CitaEventoAdmin` con `has_add/change/delete = False` (solo lectura/filtrado) y visible para roles con permisos de dominio (el seed otorga permisos de solo lectura+gestión de accounts/scheduling al director demo, sin superusuario).
- El portal no ofrece ninguna ruta para editar/borrar eventos.
- Falla la operación → la transacción revierte cita+evento (probado en `test_reserva_fallida_no_deja_evento` y en los 3 flujos de excepción de `TrazabilidadEventosTests`).

## Archivos

`backend/scheduling/models.py` (CitaEvento, resolucion_txt, marcas) · `backend/scheduling/migrations/0004_…py` · `backend/scheduling/trazabilidad.py` (nuevo) · `backend/scheduling/admin.py` (CitaEvento readonly + acciones auditadas) · `backend/portal/indicadores.py` (nuevo) · `backend/portal/views.py` (instrumentación + director/trazabilidad/csv) · `backend/portal/urls.py` · `backend/portal/apps.py` (branding admin) · plantillas: `dashboard_director.html` (nueva), `trazabilidad.html` (nueva), `partials/cita_eventos.html` (nueva), `partials/cita_info_block.html` (incluye timeline), `dashboard_cliente.html` (fix block JS), `dashboard_base.html` (nav lateral) · `static/css/styles.css` (timeline + paneles) · `static/css/admin-citi.css` (nuevo) · `templates/admin/base_site.html` (nuevo) · tests: 19 nuevos en `portal/tests.py` (total 61).
