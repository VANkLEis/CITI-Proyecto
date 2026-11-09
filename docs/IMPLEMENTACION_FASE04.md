# Implementación Fase 04 — Seguimiento del cliente, interacción y diferenciación de servicios

Regla aplicada: TODO es aditivo sobre la arquitectura de Fases 01–03. No se
reemplazó ningún mecanismo: las interacciones reutilizan `CitaEvento` +
`scheduling/trazabilidad.py`; los estados conservan `CitaAsesoria.Estado`; el
feedback/calificación existente sigue intacto.

---

## 1. Modelo de interacciones (justificación de la migración)

Evaluación previa (Fase 0 del brief): `NotaBitacora` no sirve — es interna del
equipo, sin tipos ni visibilidad. `CitaEvento` es solo-lectura/auditoría, no
objeto de conversación. Ninguno permite autoría editable ni lectura por partes.
**Justificación**: se crea un modelo propio y se Migra de forma aditiva
(`scheduling/migrations/0005_alter_citaevento_tipo_citainteraccion.py`:
tabla nueva + ensanche de `CitaEvento.tipo` de 30→34 chars para 3 tipos nuevos;
ninguna columna existente se altera ni pierde datos).

`scheduling.CitaInteraccion`:
- `cita` FK, `autor` FK (SET_NULL), `rol_autor` (instantánea), `tipo`,
  `texto`, `datos_extra` JSON (ficha de consultoría), `para_cliente`, `fecha`.
- Tipos (7 del brief + 1 de soporte): `general`, `observacion` (profesional),
  `respuesta` (cliente), `ajuste` (equipo), `entrega_resultados`,
  `aprobacion`, `rechazo_ajuste`, y `nota_interna` (visibilidadFalse).
- `clean()` cruzada: los tipos de cliente solo los escribe el cliente y viceversa;
  una nota interna NUNCA es `para_cliente` (normalizado en `save()` y `__init__`).

`CitaEvento.Tipo` nuevos: `interaccion`, `entrega_publicada`,
`decision_cliente` — toda interacción deja su evento espejo (con `metadata
{interaccion_id, privada?}`); los cambios de estado siguen siendo asunto
exclusivo de `cambio_estado` (comentario ≠ estado, probado).

## 2. Flujo de aprobación (5.3)

`trazabilidad.publicar_entrega()` → el cliente decide desde su página de
seguimiento:
- **Aprobar**: crea `aprobacion` + evento `decision_cliente`; NO toca
  `estado` (regla verificada: la cita sigue `en_proceso`; el cierre lo hace
  el docente con su acta según las reglas existentes).
- **Solicitar ajustes**: crea `rechazo_ajuste`; si el caso estaba
  `finalizada`, se reabre a `en_proceso` ÚNICAMENTE por la arista formal
  `finalizada→en_proceso` (con su evento de transición); en cualquier otro
  estado activo el estado no se modifica.
- Sin entrega pendiente o decisión duplicada → `ValidationError` dentro del
  `transaction.atomic()` del flujo: no queda registro parcial (probado).

## 3. Tabla formal de transiciones (incidencia I-2 — IMPLEMENTADA)

`CitaAsesoria.TRANSICIONES` (single source of truth) +
`CitaAsesoria.transicion_legal()`:

| desde | permitidas |
|---|---|
| solicitada | asignada, cancelada |
| asignada | en_proceso, finalizada, cancelada |
| en_proceso | finalizada, cancelada |
| finalizada | en_proceso (solo reapertura por ajuste del cliente) |
| cancelada | — (terminal) |

Aplicada en: `cambio_estado()` (servicio), acciones rápidas del docente
(página y modal), `DocenteCasoForm` (guarda previa antes de `form.save()`),
y cancelación del cliente. No hay retrocesos manuales (el caso
`en_proceso→asignada` fue eliminado tras detectar en tests que era un
caballo de Troya). Regresiones: `StateMachineTests` históricas siguen verdes.

## 4. Incidencias cerradas en esta fase

| # | Estado | Evidencia |
|---|---|---|
| I-2 transiciones formales | ✅ Implementada + probada | `TransicionesFormalTests` (3 tests) |
| I-3 uploads sin vista autorizada | ✅ Implementada + probada | `portal.views.cita_adjunto` (`/panel/cita/<id>/adjunto/`): dueña, docente/tutor asignado, coordinador del área o director; `PermissionDenied` para el resto; `FileResponse as_attachment`. Todos los enlaces de descarga del sitio apuntan aquí. `CancelacionI4AdjuntoI3Tests` |
| I-4 cancelación desde portal | ✅ Implementada + probada | POST autenticado en `cliente_seguimiento` con `confirmar=si` + confirmación JS doble capa; solo en `solicitada/asignada`; evento `cancelada` con actor. Valida estado otra vez en el servicio. 3 tests |
| I-6 tipo_servicio sin efecto | ✅ Implementada + probada | `CitaAsesoria.clean()`: consultoría `especializada` en estados de ejecución exige docente; `asignar_cita()` lo exige antes de persistir (mensaje en español); la ficha `ctx_*` de reserva solo aplica a consultoría (400 en asesoría). Demostrado en vivo: el coordinador que intentó asignar la CITI-00017 sin docente recibió el rechazo. 5 tests en `ModalidadesServicioTests` |
| I-5 MIXTO | ⏳ Pendiente (sin cambios) | Como en Fases 01–03: sin franjas ni citas mixtas en la BD; se documenta en la UI con aviso honesto. No se inventó flujo. |
| SEG-14/21/22/23 | ⏳ Pendientes | Ver `docs/audit/PLAN_CORRECCIONES.md`; no se declaran resueltas. |

## 5. Diferenciación asesoría vs consultoría (6)

- **Reserva (portal cliente)**: las tarjetas de tipo explican cada modalidad;
  al elegir consultoría aparecen campos de ficha (objetivos/alcance +
  entregables esperados) que se almacenan como interacción `general` con
  `datos_extra {alcance, entregables, origen: solicitud_cliente}`.
- **Ficha del entregable (docente)**: para consultoría ofrece diagnóstico,
  alcance, metodología y entregables (todos opcionales por diseño: "no todos
  los campos deben ser requisitos"); para asesoría basta título + contenido.
- **Plantillas**: `modalidad-note` diferenciada en asignación, entregables y
  detalle; landing con sección `#modalidades` (dos tarjetas comparativas con
  características REALES del sistema — aprobación de entregables existe ahora).
- No se creó una segunda aplicación ni se inventaron servicios/certificaciones.

## 6. Portal de seguimiento del cliente (4)

- `GET /panel/cliente/mis-solicitudes/` — tarjetas con código CITI-%05d,
  servicio, tipo, área, especialidad, profesional, estado y última
  actualización; filtros por estado y tipo; estados vacíos útiles (sin
  solicitudes vs sin resultados de filtro).
- `GET/POST /panel/cliente/solicitud/<id>/seguimiento/` — pertenencia forzada
  (`cliente=request.user`, ajena = 404). Encabezado (código, servicio, estado,
  radicación), responsables (área, coordinador del área resuelto en servidor,
  profesional, tutor), **línea de progreso real** (`CitaAsesoria.timeline` +
  banner de cancelada independiente, sin progresión ficticia), historial
  `CitaEvento` (reutilizado), panel de entrega pendiente con aprobar/ajustes,
  formulario de comentario, y cancelación con confirmación (I-4).
- `GET /panel/cliente/notificaciones/` — datos reales: entregables pendientes
  (derivados de interacciones), casos sin valorar, mensajes recientes del
  equipo. Sin inventos.
- La página `dashboard_cliente` añade el bloque "Requieren su decisión" y el
  botón "Seguimiento" por fila; el modal del cliente también muestra y permite
  comentar (con enlace a la vista completa).

## 7. Navegación por rol (7)

Todos los enlaces apuntan a rutas reales existentes y protegidas en servidor:

| Rol | Barra lateral |
|---|---|
| Cliente | Agenda y solicitud · Mis solicitudes · Notificaciones · Mi perfil |
| Docente | Mis casos · Seguimiento y entregables (`/panel/seguimiento/` filtrado a sus casos) · Mi perfil |
| Estudiante | Mis casos de apoyo · Mi perfil |
| Coordinador | Bandeja · Seguimiento de mi área · Trazabilidad de mi área · Mi perfil |
| Director | Resumen ejecutivo · Seguimiento global · Trazabilidad e indicadores · Reportes (CSV) · Mi perfil · Administración |

- `GET /panel/perfil/` — perfil real solo lectura (cuenta, rol, empresa o
  perfil académico con habilitación de tutor calculada) + enlace autenticado
  de cambio de contraseña para `is_staff`.
- `GET /panel/seguimiento/` (`staff_seguimiento`) — docente: sus casos;
  coordinador: su área (servidor); director: global. KPIs de interacción +
  filtros (enfoque/estado/tipo/búsqueda por código o empresa) + apertura del
  detalle con comentarios.
- No se incluyó "Historial" como enlace decorativo en docente: el historial
  vive en cada caso y en Trazabilidad (documentado en la guía).

## 8. Reportes e indicadores (8)

`portal/indicadores.py::metricas_interaccion(qs)` (fórmulas en su docstring):
entregas publicadas, casos con entrega, pendientes de aprobación (última
entrega sin decisión — mismo criterio que `CitaAsesoria.entrega_pendiente`),
aprobaciones, ajustes solicitados y valoración media con `n`. Consultadas con
agregaciones por cita (sin N+1). Visibles en `/panel/trazabilidad/` con las
fórmulas a la vista y "No disponible" honesto. El CSV añade la columna
"Aprobación de entregables" (`pendiente|aprobada|con ajustes`, derivada con el
mismo criterio vía `_mapa_aprobacion_citas`); sin correos personales.
`Kpis` del staff_seguimiento usan los conteos por alcance.

## 9. Organigrama eliminado (9) — sin reemplazo

- `landing.html`: removidos la tarjeta `#quienes-somos .org-card`, el modal
  `#orgModal` y TODO su JavaScript (`orgAmpliarBtn`/`orgScrollImg`); la sección
  queda solo con el texto institucional (sin imagen, diagrama ni tarjetas de
  estructura).
- `styles.css`: eliminados los bloques `.org-*` (tarjeta, scroll, modal,
  keyframes) y las reglas huérfanas en media queries y `prefers-reduced-motion`.
- Verificado en navegador real desktop (1440) y móvil (390): cero referencias
  a `citi-organigrama` en el HTML servido (capturas `p4-paso15-*`).
- Los archivos PNG (`backend/static/images/citi-organigrama.png` y la copia en
  `assets/` raíz) se CONSERVAN: son activo institucional y la instrucción es
  retirar su uso en la interfaz, no destruirlo. El prototipo estático de raíz
  (`visualizacion.html`) tampoco se toca (no forma parte del sitio Django).

## 10. Seguridad verificada (11)

Matriz probada en `InteraccionComentariosTests`, `AprobacionesEntregablesTests`
y `CancelacionI4AdjuntoI3Tests`: cliente solo lee/comenta lo suyo (ajeno=404);
no puede elegir tipos de equipo (aunque forgee los campos: la vista filtra por
elección del rol y el modelo por `clean()`); docente no asignado = 404;
coordinador aislado por área; director global; decisiones autenticadas y
asociadas a usuario real; eventos históricos inmutables (el admin sigue sin
add/change/delete y las interacciones se registran como inline readonly);
adjunto tras vista autorizada (I-3); toda escritura de interacción/decisión
dentro de `transaction.atomic()` — la prueba de transacción fallida verifica
cero eventos de éxito.

## 11. Defectos detectados y corregidos durante la validación

1. El evento espejo de una `nota_interna` copiaba el texto al historial que
   lee el cliente → ahora el evento privado no lleva el contenido y el partial
   lo oculta a clientes (`metadata.privada`).
2. `estado_rapido` del docente no pasaba por la tabla de transiciones
   (retroceso en_proceso→asignada posible) → guardas en ambas vistas.
3. Decisión con observación vacía se registraba igualmente → ahora exige
   texto (formulario ligado y válido; re-render con error en otro caso).
4. Desborde horizontal en móvil de TODAS las páginas de panel (topbar flex sin
   wrap + bloque de correo) → `flex-wrap` y `overflow-wrap` en
   `.topbar-dash` (regla aditiva).
5. La asesoria del E2E quedó sin docente visible para el portal por diseño del
   formulario de asignación (el coordinador podía asignar solo tutor) → se
   completó la asignación por el servicio (evento registrado), y la UI ahora
   orienta según la modalidad.

## 12. Pruebas

`manage.py test`: **105 pruebas OK** = 61 heredadas (intactas) + 44 nuevas:
`SeguimientoClienteTests` (6), `InteraccionComentariosTests` (9),
`AprobacionesEntregablesTests` (7), `ModalidadesServicioTests` (6),
`TransicionesFormalTests` (3), `CancelacionI4AdjuntoI3Tests` (5),
`ReportesInteraccionTests` (3), `NavegacionRegresionF4Tests` (5).
Cobertura según la lista 12 del brief: seguimiento, comentarios, aprobaciones,
modalidades, reportes/permisos y regresión (landing sin organigrama, rutas de
navegación, accesos por rol).

## 13. Seed de demo

`_simular_interacciones_demo()`: guiones coherentes por cita del plan
(entrega→aprobación en 'ciber'; entrega→rechazo→v2→aprobación en
'estructuras'; observación/respuesta en 'vias' pendiente de aprobación;
nota interna en 'bd'), todos etiquetados **"(simulación seed_demo)"** y
retro-fechados contra la timeline sembrada; idempotente (omite citas con
interacciones existentes); el comando reporta "interacciones simuladas".

## 14. Archivos

Nuevos: `scheduling/migrations/0005_…`, `templates/portal/cliente_seguimiento.
html`, `cliente_mis_solicitudes.html`, `cliente_notificaciones.html`,
`perfil_propio.html`, `staff_seguimiento.html`, `partials/
interaccion_list.html`.
Modificados: `scheduling/models.py`, `scheduling/trazabilidad.py`,
`scheduling/admin.py`, `scheduling/views.py`, `portal/views.py`,
`portal/forms.py`, `portal/urls.py`, `portal/indicadores.py`,
`accounts/demo_seed.py`, `accounts/management/commands/seed_demo.py`,
`templates/base.html` (cache-busting), `portal/landing.html`,
`dashboard_cliente.html`, los 5 dashboards + `trazabilidad.html` +
`docente_caso_detalle.html` + `coordinador_asignar.html` + 4 partials de
detalle, `static/css/styles.css` (aditivo + remoción dirigida de `.org-*`).
## 15. Validación E2E en navegador (Playwright, 15 pasos del brief)

Flujo completo ejecutado en vivo (cuentas demo, servidor local 8899):
1-3. Cliente reservó **asesoría** (CITI-00016) y **consultoría con ficha**
(CITI-00017) — los campos de ficha solo aparecen/aceptan en consultoría.
4. Coordinador: intentó asignar CITI-00017 **sin docente → rechazado en vivo**
(I-6); asignó ambas luego (16 con tutor; 16 quedó visible al docente tras
completar responsable como haría coordinación).
5-7. Docente: en proceso, observación en 16, **publicó entregable v1 con ficha**
en 17 (visible al cliente, evento `entrega_publicada`).
8-9. Cliente: seguimiento muestra código/estado/responsables(progresión real),
comentó y **solicitó ajustes** (decisión con observación; sin observación →
error visible y nada registrado).
10. Docente respondió y **publicó v2**.
11. Cliente **aprobó v2**: mensaje honesto de que la aprobación no cierra;
la cita quedó `en_proceso` (verificado en pantalla y BD). Tras una tercera
entrega, segunda aprobación igual de correcta (decisiones por entrega).
12. Director: KPIs + métricas de interacción (6 entregas, 1 pendiente,
2 ajustes, 3 aprobaciones, 4,67/5 n=3) + CSV con columna "Aprobación de
entregables" (CITI-00017 = `aprobada`).
13-14. Navegación por los 4 roles verificada (24 rutas barridas, **cero
errores de servidor**, cero errores de consola) y móvil 390 px: portal cliente,
seguimiento, notificaciones, perfil, bandeja, seguimiento y trazabilidad sin
desborda-miento horizontal (se corrigieron 3 defectos responsive reales:
topbar, `min-width` del flex principal y radios absolutas ocultas).
15. Organigrama: cero referencias en el HTML servido en 1440 y 390.

Evidencia (`.playwright-mcp/`): `p4-paso4-coordinador.png`,
`p4-paso7-entrega-publicada.png`, `p4-paso8-seguimiento-cliente.png`,
`p4-paso11-aprobacion.png`, `p4-paso12-trazabilidad.png`,
`p4-paso13-seguimiento-global.png`, `p4-paso14-landing-390.png`,
`p4-paso15-landing-modalidades.png`, `p4-cliente-390.png`,
`p4-mis-solicitudes-390.png`, `p4-seguimiento-390.png`,
`p4-modal-estudiante.png`, `p4-docente-caso-entregas.png`,
`p4-coordinador-seguimiento.png`, `p4-cliente-seguimiento-full.png`.

Sin dependencias nuevas. Sin datos borrados.

