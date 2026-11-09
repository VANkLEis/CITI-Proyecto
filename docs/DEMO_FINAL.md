# Demo final — CITI (Fases 01–04)

Guion completo de la demostración académica, ahora con trazabilidad visible.
Tiempo estimado: 15–18 min. Requiere solo: PowerShell, navegador y `venv` raíz.

## Preparación (5 min antes)

```powershell
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py seed_demo    # idempotente; reubica si el tiempo pasó
..\venv\Scripts\python.exe manage.py runserver
```
Abrir `http://127.0.0.1:8000/`. Cuentas: `docs/demo/CUENTAS_DE_PRUEBA.md`
(contraseña única local). Recomendado: ventana del navegador a ~1440 px.

> El seed de demo ya carga una línea de tiempo simulada (etiquetada como tal).
> La magia de la presentación es que el caso reservado EN VIVO genera su
> propio historial 100 % genuino delante del público.

## Acto I — Identidad institucional (2 min)

1. Landing: hero concreto ("Asesorías de ingeniería y tecnología para el
   Tolima"), barra de hechos (2 áreas · 8 especialidades · 0 costo) — los 8
   servicios se leen del catálogo real de la plataforma.
2. Navegar Servicios → Cómo funciona (los 4 estados reales del sistema) →
   banda "Cada caso deja trazabilidad real" → banners (los dos enlazan a
   rutas verdaderas) → banco de recursos (PDFs reales).
3. (Opcional) menú hamburguesa en ventana estrecha: responsive.

## Acto II — Cliente: solicita en vivo (3 min)

Login portal **cliente** → `cliente@empresatolima.co`.
1. Calendario: franjas "Disponible (n)"; explicar capacidad/áreas.
2. Elegir franja libre → tipo de servicio → subespecialidad → asunto:
   "Caso de demostración en vivo — <tema del jurado si lo hay>".
3. Confirmar → aparece "Solicitada" en la tabla.

## Acto III — Coordinador: asigna y revisa (3 min)

Login portal **coordinador** → `coordinador@citi.ucc.edu.co` (Sistemas).
1. Bandeja: la solicitud nueva (y la pendiente sembrada). KPI "nuevas" subió.
2. Clic en la fila → modal de detalle: **Historial ya muestra "Solicitud
   creada" y "Solicitud revisada"** — generados por los pasos anteriores.
3. Asignar docente + tutor (solo aparecen docentes del área y tutores que
   cumplen 8°/130/4.0 — explicar el filtro académico). Confirmar.
4. Demo de seguridad (30 s): escribir `/panel/cliente/` → redirige al propio
   portal (antes de la Fase 02 esto devolvía un error 500).
5. Abrir `/panel/trazabilidad/`: su propia área aislada; el filtro de área
   aparece bloqueado por diseño.

## Acto IV — Docente + tutor: ejecutan y cierran (4 min)

Login portal **docente** → `docente@citi.ucc.edu.co`.
1. "Gestionar" el caso: *Marcar en proceso*.
2. En el historial aparece "Asesoría iniciada" en vivo.
3. Escribir resumen de cierre → *Finalizada* (el formulario lo pide).
4. *Descargar acta* → pestaña imprimible con código CITI-xxxxx.
5. Login portal **estudiante** → `estudiante@citi.ucc.edu.co`: banner de
   habilitación (perfil real que supera umbrales) + el caso en su bandeja +
   registrar nota de bitácora → **visible también en el historial del
   docente** (evento "Nota de bitácora").

## Acto IV.b — Cliente aprueba entregables (2 min, NUEVO Fase 04)

Volver al cliente. En «Mis solicitudes» (o el banner "Requieren su decisión")
abrir el **Seguimiento** de un caso con entregable:
1. Ver progreso real, responsables (incluye el coordinador del área) e
   historial vivo.
2. Comentar una duda → aparece en el historial del docente como evento.
3. **Solicitar ajustes** sobre un entregable (con observación): el caso vuelve
   al flujo del equipo; si estaba finalizado, se reabre por la única arista
   formal permitida.
4. El docente responde y publica la v2 → el cliente **aprueba**: message
   honesto: la aprobación NO cierra el caso; el cierre lo hace el docente.
5. (Opcional, 20 s) Cancelar una solicitud nueva `solicitada` con confirmación
   → evento `cancelada` con su correo como actor (I-4).

## Acto V — Cliente valora (1 min)

Volver al cliente → "Calificar" el caso recién cerrado → 5/5 + comentario.
Historial de la cita = 8+ eventos con autores, horas y estados.

## Acto VI — Dirección: los números (3–4 min)

Login portal **director** → `director@citi.ucc.edu.co`.
1. Panel ejecutivo: los KPIs reflejan el flujo operado (recibidas+1,
   finalizadas+1, tasa recalculada). Cambiar chips de periodo → todo se
   recalcula (sin recargar estados, es query).
2. Trazabilidad: filtros (área, estado, responsable, tipo, fechas) +
   **Exportar CSV en vivo** → abrir el archivo: período, generación,
   responsable y datos de gestión; sin correos personales.
3. Indicadores: tiempos medios con `n` visible (y "No disponible" honesto si
   la muestra no alcanza); evolución mensual con el pico real de la demo.
4. Admin (`/admin/`): mostrar el caso del vivo con su **Historial de eventos
   inmutable** (sin botones añadir/editar/borrar), las acciones de
   coordinación y los filtros; volver al panel.

## Acto VII — Cierre técnico (1 min)

```powershell
..\venv\Scripts\python.exe manage.py test          # 105 pruebas OK, base aislada
..\venv\Scripts\python.exe manage.py check         # 0 issues
```
Mensaje final: el sistema no es un prototipo — es un backend Django real,
auditado, con datos de origen verifiable y trazabilidad de extremo a extremo.

## Qué hacer si algo falla en vivo

| Síntoma | Causa probable | Acción |
|---|---|---|
| Calendario sin franjas | horas pasadas | `manage.py seed_demo` (reubica todo a franjas nuevas) |
| Login "pertenece al portal X" | rol equivocado en el selector | elegir el portal correcto del listado |
| Historial vacío en una cita vieja | existía antes de la trazabilidad | es el aviso honesto; mostrar el caso en vivo |
| Error 500 | proceso antiguo con código nuevo | matar `python`, relanzar `runserver` (los procesos `--noreload` no recargan Python) |

## Capturas de verificación (hechas con Playwright MCP en la fase)

`docs/…` no las incluye embebidas; están en `.playwright-mcp/`:
`p3-landing-hero-1440.png`, `p3-landing-full-1440.png`,
`p3-landing-servicios.png`, `p3-landing-proceso.png`,
`p3-landing-390-fold.png`, `p3-landing-390-menu.png`,
`p3-director-1440.png`, `p3-director-390.png`,
`p3-trazabilidad-1440.png`, `p3-traz-820.png`,
`p3-timeline-modal.png`, `p3-admin-1440.png`, `p3-admin-cita15.png`.
