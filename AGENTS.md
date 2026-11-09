# AGENTS.md

## Repository shape
- `backend/` is the real application: Django project `config` + apps `accounts`, `scheduling`, `portal`.
- Root `accounts/`, `portal/`, `scheduling/` are empty default Django app stubs. Never edit them; real code is only under `backend/`.
- Root `app/`, `dashboards/`, `plantillas/`, `docs/`, `assets/`, and top-level `*.html` are a static prototype/spec. Django serves templates from `backend/templates` and assets from `backend/static` + root `assets/` (see `STATICFILES_DIRS`). Editing root `app/js` does not change the running Django site.

## Commands
Run from `backend/` and use the root `venv` (has Django 5.2.18, matching `requirements.txt`):
```powershell
..\venv\Scripts\python.exe manage.py check
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
..\venv\Scripts\python.exe manage.py seed_demo
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test
```
- Do not use `.venv` (Django 6.1.2, violates the `<6` requirement) or `backend/venv` (Django not installed).
- Automated tests exist under `backend/portal/tests.py` (105 tests: role matrix, reservas, estados, IDOR, registro, seed, E2E, trazabilidad, indicadores, seguimiento/interacciones/aprobaciones/modalidades). They run on an isolated test database; the real `db.sqlite3` is untouched.
- No lint/format config exists. Match existing style: single quotes, Django function-based views, Spanish user-facing text.
- `runserver --noreload` does NOT reload Python after editing views/models/settings (templates DO reload in DEBUG). Restart the server after every code change before browser validation; check only one server listens on the port (stale second process caused wrong renders twice in Fase 03).
- Playwright MCP screenshots can only be written inside project roots; evidence goes in `.playwright-mcp/` (scratch dir, currently untracked but NOT in `.gitignore` — don't commit it).

## Configuration / environment
- Default DB is SQLite at `backend/db.sqlite3`. Setting `DATABASE_URL=postgres://user:pass@host:5432/db` switches to PostgreSQL.
- Recognized env vars: `DJANGO_ENV` (`desarrollo` default | `produccion`), `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`1`/`0`; forced to `0` in `produccion`), `DJANGO_ALLOWED_HOSTS` (comma-separated), `DATABASE_URL`, `CITI_DEMO_PASSWORD`, `DJANGO_HSTS_SECONDS`, `CITI_MIN_SEMESTRE_TUTOR` (default 8), `CITI_MIN_CREDITOS_TUTOR` (default 130), `CITI_MIN_PROMEDIO_TUTOR` (default 4.0).
- `backend/.env` IS now auto-loaded via `python-dotenv` (see `config/settings.py`); copy `backend/.env.example` to start. In `produccion`, missing `DJANGO_SECRET_KEY` or `DJANGO_ALLOWED_HOSTS` raises `ImproperlyConfigured` (no known fallback). Details: `docs/demo/VARIABLES_ENTORNO.md`.
- `DATABASES` only switches to PostgreSQL if `DATABASE_URL` starts with `postgres`; other schemes silently keep SQLite. Locale is `es-co` / `America/Bogota`.
- Uploads (`CitaAsesoria.archivo_adjunto`) land in `backend/media/documentos_citas/<YYYY>/<MM>/`; `runserver` serves `/media/` only in DEBUG.

## Domain and access rules
- Custom email-based user `accounts.CustomUser`; roles: `director`, `coordinador`, `docente`, `estudiante`, `cliente`. Public registration creates only `cliente`; all other roles must be created in `/admin/`.
- Login is role-aware: `RoleLoginForm` submits a hidden `expected_role` and rejects users whose role doesn't match ("Esta cuenta pertenece al portal …"). `/cuenta/login/?rol=<role>` presets it. When testing flows, log in through the matching role URL.
- Students have `student_type` `consultor`/`tutor`. `PerfilEstudiante.save()` and the `post_save` signal auto-promote/demote based on semester, credit, and average thresholds (defaults: 8, 130, 4.0). Do not set tutor status manually.
- `CustomUser.save()` always runs `full_clean()` (unless `skip_validation=True`): estudiantes need a `student_type`, tutores must meet the academic thresholds, and clientes must be linked to an `Empresa`. Internal code bypasses this with `save(skip_validation=True)` (see `accounts/signals.py`) — use that kwarg when seeding or programmatically toggling `student_type`, or saves will raise.
- Appointments: availability in `FranjaHoraria` (capacity), bookings in `CitaAsesoria` with states `solicitada -> asignada -> en_proceso -> finalizada` (or `cancelada`). A DB constraint allows only one active booking per client per slot.
- Access control is `portal.decorators.role_required` plus `portal.role_routing.dashboard_url_for_role`. Coordinators are area-locked (`portal/area_helpers.py`). `Area` choices are `sistemas`, `civil`, `mixto`; `CitaAsesoria.clean()` requires assigned docente/estudiante `area` to match the franja's area (`mixto` matches both).
- One detail view dispatches by role: `portal.cita_detalle_interactivo` renders `templates/portal/partials/cita_detalle_<role>.html` and accepts an `embed` GET/POST flag that changes redirects (modal vs full page).
- Django `ModelForm` with `instance=cita` mutates that instance during `is_valid()`. When a view must audit "before vs after", capture `anterior_estado`/`anterior_apoyo_id` BEFORE binding POST data (regression covered in tests; applies to new comment/approval flows).
- `coordinador_asignar` / coordinator detail write a `revisada` event on GET (once per user, via `nota_asignacion`). Seed-created timelines are retro-dated and every description is tagged "(simulación seed_demo)" — keep that honesty convention for any new seeded history.
- Demo data is EXPLICIT (post-audit B-4): views no longer seed anything on GET. Run `manage.py seed_demo` (idempotent, refuses to run with `DJANGO_ENV=produccion`) to create users, future slots, and requests in every state. Demo accounts (emails `*@citi.ucc.edu.co`, `cliente@empresatolima.co`) share password `CITIPass2026*` locally (override with `CITI_DEMO_PASSWORD`). See `docs/demo/`.
- APIs are plain Django JSON views, not DRF: `/agenda/api/eventos/` and `/agenda/api/reservar/` (reserva uses `transaction.atomic` + `select_for_update` on the franja).
- Fase 03 (traceability): `scheduling.CitaEvento` is an append-only event log (admin read-only; created ONLY via `scheduling/trazabilidad.py` helpers called from views/API/admin inside `transaction.atomic`). `CitaAsesoria` carries `asignada_en`/`cerrada_en` set on real transitions. Metrics/CSV live in `portal/indicadores.py` (formulas documented there; cancelled counts as received, never as delivered; averages show "No disponible" when sample is empty; `parse_filtros` is the single entry that enforces the coordinador's `area_forzada` before any query). Executive views: `portal:director_dashboard` (director only) and `portal:trazabilidad`/`portal:trazabilidad_csv` (director global, coordinador area-locked server-side). The student dashboard KPI is real (assigned/closed cases + average rating) — the old arbitrary hours/credits formula was removed.
- Admin safety rails (Fase 03): `CitaAsesoria` is undeletable for non-superusers (protects the event log); admin state changes route through `cambio_estado` so they emit events; demo `director@…` is `is_staff` with accounts/scheduling domain perms granted by seed, NOT superuser.
- Organigrama image (`citi-organigrama.png`): REMOVIDO de la interfaz en Fase 04 (landing, modal, JS y estilos `.org-*` eliminados; verificación desktop+móvil sin referencias). Los PNG se conservan en `backend/static/images/` y `assets/` raíz como activo institucional (sin otros usos en el sitio Django; el prototipo estático raíz no cuenta). No debe volver a referenciarse.
- Fase 04 (seguimiento e interacción): `scheduling.CitaInteraccion` (migración 0005, aditiva) guarda comentarios/entregas/aprobaciones con `tipo`, `rol_autor` instantáneo y `para_cliente` (nota_interna siempre privada). Escrituras SOLO vía `trazabilidad.registrar_interaccion/publicar_entrega/registrar_decision_cliente` dentro de `transaction.atomic()`; cada una deja su evento espejo (decisiones y entregas también dejan `entrega_publicada`/`decision_cliente`). Aprobar un entregable NO finaliza la cita; ajustes reabren `finalizada→en_proceso` (única arista hacia atrás). Tabla formal de estados: `CitaAsesoria.TRANSICIONES` + `transicion_legal()`, aplicada en `cambio_estado`, acciones rápidas y `DocenteCasoForm` (I-2). Consultoría (`especializada`) exige docente al salir de solicitada — `clean()` + `asignar_cita` (I-6). Cliente: `/panel/cliente/mis-solicitudes/`, `/panel/cliente/solicitud/<id>/seguimiento/` (cancelación propia con confirmación = I-4; decisión exige observación no vacía), `/panel/cliente/notificaciones/`; equipo: `/panel/seguimiento/` (staff_seguimiento, alcance por rol en servidor); global: `/panel/perfil/`; descarga autorizada `/panel/cita/<id>/adjunto/` (I-3 — los enlaces a `archivo_adjunto.url` ya no deben usarse). Métricas de aprobación en `indicadores.metricas_interaccion` + columna CSV `Aprobación de entregables` (mismo criterio que `CitaAsesoria.entrega_pendiente`). Seed etiqueta interacciones demo como "(simulación seed_demo)" e idempotencia por `cita.interacciones.exists()`.

## Docs caveat
`docs/erd-mermaid.md` describes a planned/legacy schema (Solicitud, Informe, Firma, etc.) that does not match the implemented models. Treat `backend/accounts/models.py` and `backend/scheduling/models.py` as the source of truth.
