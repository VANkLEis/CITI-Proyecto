# AGENTS.md

## Repository shape
- `backend/` is the real Django project: `config` + apps `accounts`, `scheduling`, `portal`.
- Root `accounts/`, `portal/`, `scheduling/` are unused default-app stubs. Never edit them.
- Root `app/`, `dashboards/`, `plantillas/`, `docs/`, and top-level `*.html` are a static prototype/spec. Django renders templates from `backend/templates` and serves `backend/static` + root `assets/` (see `STATICFILES_DIRS`). Editing root `app/js` does not change the running site.
- Current size: 3 apps, 11 models, 39 routes, 163 tests. All three apps have models/migrations; `portal` also has `admin.py`.

## Commands
Run from `backend/` with the **root** venv (Django 5.2.18, matches `requirements.txt`):
```powershell
..\venv\Scripts\python.exe manage.py check
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
..\venv\Scripts\python.exe manage.py seed_demo_data   # full demo set (idempotent)
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test
..\venv\Scripts\python.exe manage.py test portal.test_public   # single module
..\venv\Scripts\python.exe manage.py test portal.tests.RoleAccessMatrixTests  # single class
```
- Three venvs exist; only the root one works: `venv/` = Django 5.2.18 (matches the `<6` pin), `.venv/` = Django 6.1.2 (violates it), `backend/venv/` = no Django installed. Picking the wrong interpreter is the easiest way to get confusing failures here.
- Tests live in **two** files: `backend/portal/tests.py` (107 legacy) and `backend/portal/test_public.py` (56 public/triage/seed). `accounts` and `scheduling` have no `tests.py`. They use an isolated test DB - the real `db.sqlite3` is untouched.
- No lint/format config. Match existing style: single quotes, function-based views, Spanish user-facing text.
- `runserver --noreload` does NOT reload Python after editing views/models/settings (templates DO reload in DEBUG). Restart after every code change before browser validation, and confirm only one process holds the port — a stale second server caused wrong renders twice in Fase 03.

## Configuration / environment
- `backend/.env` is auto-loaded via `python-dotenv`; start from `backend/.env.example`.
- `IS_PRODUCTION` derives **only** from `DJANGO_ENV in ('produccion','production','prod')` — never from `DJANGO_DEBUG`. So `DJANGO_ENV=desarrollo` + `DJANGO_DEBUG=0` is legal (it is what Docker uses) and `seed_demo_data` still runs. Under `produccion`: `DEBUG` forced off, missing `DJANGO_SECRET_KEY`/`DJANGO_ALLOWED_HOSTS` raises, cookies/SSL/HSTS harden, and seeding is refused.
- Other env vars: `DATABASE_URL`, `CITI_DEMO_PASSWORD`, `DJANGO_HSTS_SECONDS`, `CITI_MIN_SEMESTRE_TUTOR` (8), `CITI_MIN_CREDITOS_TUTOR` (130), `CITI_MIN_PROMEDIO_TUTOR` (4.0), plus container-only `CITI_USE_WHITENOISE`, `CITI_SERVE_MEDIA`, `CITI_SEED_ON_START`, `PORT`, `GUNICORN_WORKERS`. Details: `docs/demo/VARIABLES_ENTORNO.md`.
- `DATABASES` switches to PostgreSQL only when `DATABASE_URL` starts with `postgres`; other schemes silently keep SQLite.
- `/media/` is served by `runserver` only when `DEBUG=True`; with `CITI_SERVE_MEDIA=1` (Docker demo) `config/urls.py` adds an explicit `serve` route. Never enable that in real production.
- `CITI_USE_WHITENOISE=1` inserts `WhiteNoiseMiddleware` and switches `STORAGES['staticfiles']` to `CompressedStaticFilesStorage`. `collectstatic` writes to `backend/staticfiles/` (gitignored).
- Locale `es-co` / `America/Bogota` with `USE_TZ=True` — build datetimes with `timezone.now()`, never naive `datetime`.

## Domain and access rules
- Custom email user `accounts.CustomUser`; roles `director`, `coordinador`, `docente`, `estudiante`, `cliente`. Public registration creates only `cliente`; all other roles are created in `/admin/`.
- **`CustomUser.save()` always runs `full_clean()`** unless called with `skip_validation=True`. Estudiantes need a `student_type`, tutores must clear the academic thresholds, and clientes must have an `Empresa`. Seeding or toggling `student_type` without that kwarg raises. This is the most common save-time failure.
- Login is role-aware: `RoleLoginForm` posts a hidden `expected_role` and rejects mismatches ("Esta cuenta pertenece al portal …"). `/cuenta/login/?rol=<role>` presets it. Always log in through the matching role URL when testing a flow.
- `student_type` (`consultor`/`tutor`) is auto-promoted/demoted by `PerfilEstudiante.save()` + a `post_save` signal based on semester/credits/average. Never set tutor status by hand.
- `FranjaHoraria` holds capacity; `CitaAsesoria` runs `solicitada -> asignada -> en_proceso -> finalizada` (or `cancelada`). A partial `UniqueConstraint` allows only one active booking per client per slot.
- Formal state table: `CitaAsesoria.TRANSICIONES` + `transicion_legal()`. Apply it (as `cambio_estado` and the quick actions do) instead of assigning `estado` directly; the only backward edge is `finalizada -> en_proceso` for rework.
- Access control is `portal.decorators.role_required` + `portal.role_routing.dashboard_url_for_role`; coordinators are area-locked via `portal/area_helpers.py`. `Area` is `sistemas`, `civil`, `mixto` (`mixto` matches both). `CitaAsesoria.clean()` requires the assigned docente/estudiante area to match the franja's.
- **`coordinador_asignar` is `@role_required(Role.COORDINADOR)` only** — the Director is read-only for existing citas. Director/Coordinador *can* triage public requests (see below). Don't "fix" the old view without checking the role matrix tests.
- `Subespecialidad` (`scheduling/subespecialidades.py`) is the real catalog: 14 codes, 4 Sistemas + 10 Civil. `valid_for_area()` gates assignment; `choices_for_area()` feeds forms and the landing.
- One detail view dispatches by role: `cita_detalle_interactivo` renders `templates/portal/partials/cita_detalle_<role>.html`; an `embed` GET/POST flag switches redirects between modal and full page.
- Django `ModelForm` with `instance=cita` mutates that instance during `is_valid()`. When a view must audit before/after, capture `anterior_estado`/`anterior_apoyo_id` **before** binding POST data (regression covered in tests; applies to every new comment/approval flow).
- `CitaEvento` is an append-only log (admin read-only). Create entries only through `scheduling/trazabilidad.py` helpers (`registrar_evento`, `registrar_interaccion`, `publicar_entrega`, `registrar_decision_cliente`), inside `transaction.atomic()`. Likewise `CitaInteraccion` is written only through those helpers; each write leaves a mirror event. Approving a deliverable does NOT close the case.
- `CitaAsesoria` is undeletable for non-superusers in admin; admin state changes route through `cambio_estado` so they emit events. Demo `director@…` is `is_staff` with domain perms from the seed, not superuser.
- Metrics/CSV live in `portal/indicadores.py`. `parse_filtros` is the single entry that enforces a coordinador's `area_forzada` before any query — never filter around it.
- Plain Django JSON views, not DRF: `/agenda/api/eventos/` and `/agenda/api/reservar/` (the latter uses `transaction.atomic` + `select_for_update`).

## Public zone and request triage (Fase 05)
- `scheduling.SolicitudPublica` is the **intake**: the web forms create it, never `CitaAsesoria`. `CitaAsesoria.cliente` stays required. Conversion is explicit through `scheduling/solicitudes.py`.
- `LineaAtencion` (`proyeccion_social` / `consultoria_profesional`) is the commercial classification. `LINEA_A_TIPO_SERVICIO` maps it to `tipo_servicio`; `CitaAsesoria.clean()` rejects a mismatch, so set both together (conversion derives `tipo_servicio` from the line).
- `SolicitudPublica.TRANSICIONES`: `recibida -> en_revision|aprobada|rechazada`, `en_revision -> aprobada|rechazada`, `aprobada -> convertida|rechazada`. `recibida -> aprobada` exists for workshops.
- Triage access: `solicitudes_visibles()` gives the Director everything and the Coordinator only their area or `Area.MIXTO`; out-of-area detail returns 404. Approval additionally requires a concrete academic area.
- Workshops (`tipo_necesidad == capacitacion`) are approved and closed in the triage: **never converted to a cita**. `convertir_solicitud` refuses them.
- `vincular_cliente()` links an existing `cliente` by email, else creates an inactive `CustomUser` with `set_unusable_password()` plus an `Empresa`. A blank NIT becomes `PENDIENTE-<code>` (Empresa has no NIT validator today, but keep the placeholder). It refuses to reuse an email owned by a non-cliente role.
- Conversion locks the solicitud and the franja with `select_for_update`, requires the franja area to match, and emits a `creada` event with `solicitud_codigo` metadata. Optional docente/estudiante go through `asignar_cita` (same academic filters).
- Public views (`portal/views_public.py`) only read published content (`publicado=True` / `activo=True`) and never seed. Honeypot field `website` plus a 10-minute duplicate window guard the forms.
- Copy rule: no "gratis", "gratuita", "sin costo" or "mínimo costo" anywhere public. Use "condiciones y alcance definidos en la sesión de diagnóstico".
- Landing constraints enforced by tests: keep `id="modalidades"`, render all 14 `Subespecialidad` labels, never reference `citi-organigrama.png`.
- Public videos are decorative: `<video autoplay muted loop playsinline preload="metadata" poster="…">` over an `<img>` fallback; a missing MP4 is expected (posters are real landing images). Don't remove the fallback.
- `ProyectoPortafolio` / `Taller` (in `portal/models.py`) are editable in `/admin/`; `imagen_static` is the fallback path under `static/` when no image was uploaded.
- Card media must stay inside a fixed `aspect-ratio` box with the `<img>` absolutely positioned (`position:absolute; inset:0; object-fit:cover; object-position:center top`). `area-sistemas.jpg` and `proceso-revision.jpg` are **portrait**; if the image returns to normal flow it stretches the whole grid row (regression seen in the portfolio grid).
- `Taller.puntos_clave` is a JSON list of up to 3 strings (rendered as the card syllabus); `Taller.area` (`sistemas`/`civil`) keeps the 50/50 balance visible in cards and admin; `Taller.grupo_publico(_label)` maps the 5 stored `publico_objetivo` codes to the 4 filter groups (`GRUPOS_PUBLICO`, where `pymes_comunidad` = `pymes` + `comunidad`).
- The demo set is intentionally balanced: 8 published projects (4 `civil`, 4 others, alternating `orden`) and 6 active workshops (3 `sistemas`, 3 `civil`, alternating `orden`). `PROYECTOS_RETIRADOS` / `TALLERES_RETIRADOS` unpublish/deactivate old demo slugs instead of deleting them (`validacion-tecnica-emprendimiento-juvenil`, `gestion-tecnologica-pymes`).
- `SolicitudPublica.madurez` (`idea`/`proceso`/`requerimientos`) is optional by design (`blank=True, default=''`); legacy rows show "No indicado". `linea_sugerida` reproduces `linea_para(tipo_necesidad)` and `accion_sugerida` is the triage guide shown in the "Diagnóstico de Filtro Sugerido" card.

## Demo data
- Demo data is EXPLICIT: no view seeds on GET. `manage.py seed_demo_data` (alias: `seed_demo`) is idempotent, refuses `DJANGO_ENV=produccion`, and creates users, franjas, citas, portfolio, workshops and `DEMO-SOL-*` requests. It is what `entrypoint.sh` runs.
- Accounts (`*@citi.ucc.edu.co`, `cliente@empresatolima.co`) share password `CITIPass2026*` locally (override with `CITI_DEMO_PASSWORD`). Inventory: `docs/demo/CUENTAS_DE_PRUEBA.md`, `CONTENIDO_PUBLICO.md`, `DATOS_DEMO.md`, guide in `GUIA_DEMOSTRACION.md`.
- Seeded history is retro-dated and every description is tagged `(simulación seed_demo)`; keep that honesty convention for any new seeded timeline.
- `coordinador_asignar` and the coordinator detail write a `revisada` event on GET, once per user via `nota_asignacion`.

## Docker
- `Dockerfile` (python:3.12-slim, Gunicorn, WhiteNoise) + `docker-compose.yml` (web + PostgreSQL 16 with `pg_isready` healthcheck and `depends_on: service_healthy`) + `entrypoint.sh` (migrate → seed → gunicorn).
- `entrypoint.sh` runs `manage.py seed_demo_data` on every boot; it must stay idempotent. `CITI_SEED_ON_START=0` disables it.
- `.gitattributes` forces `*.sh text eol=lf`; without it Docker fails with `sh\r: not found` on Windows checkouts.
- `Dockerfile` copies `assets/` because `STATICFILES_DIRS` depends on it. If that folder is removed, remove the `COPY assets/` line too.
- Docker CLI is **not installed** on this machine: the build was validated with `check`, `makemigrations --check`, `test` and `collectstatic`, but `docker compose up --build` must be run on a machine with Docker Desktop.

## Docs caveat
`docs/erd-mermaid.md` describes a planned/legacy schema (Solicitud, Informe, Firma, …) that does not match the implemented models. Treat `backend/accounts/models.py`, `backend/scheduling/models.py` and `backend/portal/models.py` as the source of truth.
