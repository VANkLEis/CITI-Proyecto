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
..\venv\Scripts\python.exe manage.py seed_demo_users
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test
```
- Do not use `.venv` (Django 6.1.2, violates the `<6` requirement) or `backend/venv` (Django not installed).
- There are no automated tests; `manage.py test` currently reports 0 tests. Verify behavior with `check` plus a manual role flow.
- No lint/format config exists. Match existing style: single quotes, Django function-based views, Spanish user-facing text.

## Configuration / environment
- Default DB is SQLite at `backend/db.sqlite3`. Setting `DATABASE_URL=postgres://user:pass@host:5432/db` switches to PostgreSQL.
- Recognized env vars: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`1`/`0`), `DJANGO_ALLOWED_HOSTS` (comma-separated), `DATABASE_URL`, `CITI_MIN_SEMESTRE_TUTOR` (default 8), `CITI_MIN_CREDITOS_TUTOR` (default 130), `CITI_MIN_PROMEDIO_TUTOR` (default 4.0).
- `.env` is NOT auto-loaded: `config/settings.py` reads `os.environ` directly and never calls `load_dotenv`, even though `python-dotenv` is in `requirements.txt`. Set variables in the shell or add loading explicitly.

## Domain and access rules
- Custom email-based user `accounts.CustomUser`; roles: `director`, `coordinador`, `docente`, `estudiante`, `cliente`. Public registration creates only `cliente`; all other roles must be created in `/admin/`.
- Students have `student_type` `consultor`/`tutor`. `PerfilEstudiante.save()` and the `post_save` signal auto-promote/demote based on semester, credit, and average thresholds (defaults: 8, 130, 4.0). Do not set tutor status manually.
- Appointments: availability in `FranjaHoraria` (capacity), bookings in `CitaAsesoria` with states `solicitada -> asignada -> en_proceso -> finalizada` (or `cancelada`). A DB constraint allows only one active booking per client per slot.
- Access control is `portal.decorators.role_required` plus `portal.role_routing.dashboard_url_for_role`. Coordinators are area-locked (`portal/area_helpers.py`).
- `landing` and `login` implicitly call `ensure_demo_users()`; demo accounts use password `CITIPass2026*` (`accounts/demo_seed.py`). The client dashboard also auto-creates demo slots when none are active.
- APIs are plain Django JSON views, not DRF: `/agenda/api/eventos/` and `/agenda/api/reservar/`.

## Docs caveat
`docs/erd-mermaid.md` describes a planned/legacy schema (Solicitud, Informe, Firma, etc.) that does not match the implemented models. Treat `backend/accounts/models.py` and `backend/scheduling/models.py` as the source of truth.
