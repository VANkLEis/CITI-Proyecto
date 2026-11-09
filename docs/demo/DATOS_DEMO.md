# Datos de demostración — CITI

Qué crea `manage.py seed_demo`, cómo se comporta con datos existentes y cómo
se comprueba la integridad. Implementación: `backend/accounts/demo_seed.py`.

## Principios

| Principio | Detalle |
|---|---|
| Explícito | Nada se crea desde vistas/GET. Solo comando (B-4) |
| Idempotente | Re-ejecutar no duplica: usuarios por email, franjas por (inicio, fin, área), citas del plan por (cliente, subespecialidad), notas por contenido |
| No destructivo | **Nunca elimina registros.** Las franjas vencidas pasan a `activa=False` (históricas) y las solicitudes activas huérfanas sobre franja terminada pasan a `cancelada` **con nota de bitácora** que deja trazabilidad |
| Frescura en demo | Si la ejecución de la demo es días después, volver a correr el seed: las citas del plan cuya franja quedó vencida se **reubican** a la franja futura libre más cercana del área, conservando estado, docente, tutor, cierre y calificación |

## Conjunto resultante

### Usuarios (8 cuentas, ver `CUENTAS_DE_PRUEBA.md`)
Director (staff), coordinadores Sistemas/Civil, docentes Sistemas/Civil,
estudiantes con perfil académico real que los **promueve a tutor**
(9°/150/4,50 y 10°/168/4,30) y cliente-empresa *Empresa Tolima Demo*.

### Franjas horarias (patrón determinista, días hábiles +1..+12)

| Área | Bloques | Capacidad | Zona horaria |
|---|---|---|---|
| Sistemas | 09:00–11:00 y 15:00–17:00 | 2 | `America/Bogota` (construidas con `timezone.get_current_timezone()`; `USE_TZ=True`) |
| Civil | 11:00–13:00 y 16:00–18:00 | 2 | idem |

- Sin conflictos de horario: bloques por franjas de 2 h, no solapadas; los
  bloques de Sistemas y Civil comparten agenda por diseño de capacidad (2
  atendidos simultáneos por área).
- Reservabilidad comprobada por `FranjaHoraria.esta_disponible` (activa +
  futuro + cupos libres).

### Solicitudes del cliente demo — cobertura de estados

> Fase 03: cada cita del plan recibe además una **línea de tiempo de eventos
> marcada como "(simulación seed_demo)"** — creada, revisada, docentes/tutores
> asignados, iniciada, finalizada, acta y feedback, con fechas retro-proyectadas
> coherentes y responsables plausibles. Es material de demostración etiquetado
> como simulación; el historial de citas reales generadas en vivo no lleva esa
> marca. Las citas anteriores a la trazabilidad muestran el aviso honesto
> "el seguimiento histórico no estaba habilitado". El seed es idempotente
> también para eventos (no duplica si ya existen).

| Subesp. | Área | Tipo servicio | Estado | Docente | Tutor | Extras |
|---|---|---|---|---|---|---|
| Desarrollo Web | Sistemas | Especializada | `solicitada` (pendiente en bandeja) | — | — | **La bandeja del coordinador Sistemas tiene trabajo real** |
| Planos | Civil | Especializada | `solicitada` | — | — | ídem, coordinador Civil |
| Bases de Datos | Sistemas | Especializada | `asignada` | docente Sistemas | — | gestión docente disponible |
| Vías | Civil | Orientación | `en_proceso` | docente Civil | estudiante Civil | **bitácora con 1 nota sembrada** |
| Redes | Sistemas | Orientación | `asignada` | docente Sistemas | estudiante Sistemas | tutor tiene tarea en su portal |
| Ciberseguridad | Sistemas | Especializada | `finalizada` | docente Sistemas | — | resumen de cierre + calificación **5** + comentario |
| Estructuras | Civil | Orientación | `finalizada` | docente Civil | estudiante Civil | resumen + calificación **4** + comentario |

Además quedan franjas futuras **libres** (ej. 11/11 09:00 Sistemas, 11/11
11:00 Civil, 11/11 15:00 Sistemas, 11/11 16:00 Civil, 12/11 09:00 …) para
**ejecutar la reserva en vivo** sin ensuciar el conjunto.

### Trazabilidad de la limpieza
Las solicitudes heredadas sobre franjas vencidas (2026/10/26–27) fueron
`cancelada` + `NotaBitacora` firmada por el director con texto identificable
("Archivo automático (seed_demo)…"). Las franjas vencidas quedaron
`activa=False` pero intactas.

## Integridad verificada (post-seed)

Consulta usada (solo lectura) y resultados esperados:

```text
Cliente demo          -> 7 solicitudes visibles en su portal (los 4 estados)
Coordinador Sistemas  -> 1 solicitud nueva en bandeja (web) + KPIs coherentes
Coordinador Civil     -> 1 solicitud nueva en bandeja (planos)
Docente Sistemas      -> 2 casos activos: bd (asignada) + redes (asignada con tutor)
Docente Civil         -> 1 caso activo: vias (en_proceso); estructuras queda como historial
Estudiante Sistemas   -> 1 caso de apoyo activo (redes) con acceso a bitácora
Estudiante Civil      -> 1 caso de apoyo activo (vias en_proceso); estructuras como historial
Director              -> usuarios=11, franjas activas=40, citas ocupando cupo=5
Franjas futuras       -> 40; todas con inicio > ahora en tz Bogota
Cupos: cada franja del plan ocupa 1 de 2 -> sigue habiendo cupo disponible
```

Cobertura automatizada de estas invariantes: `SeedDemoTests` (42 pruebas en
`backend/portal/tests.py`) — idempotencia, promoción de tutor por umbrales,
reubicación tras vencimiento, bloqueo en producción.

## Reinicio recomendado el día de la demo

```powershell
cd backend
..\venv\Scripts\python.exe manage.py seed_demo   # reubica y refresca
..\venv\Scripts\python.exe manage.py test        # opcional, humo rápido
```
Si el presentador consumió en vivo reservas del set (nuevas solicitudes),
no se duplican al re-sembrar (clave por subespecialidad); simplemente
conviven como solicitudes adicionales legítimas.
