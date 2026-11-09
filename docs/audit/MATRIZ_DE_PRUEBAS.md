# MATRIZ DE PRUEBAS — CITI

## 1. Entorno de ejecución

- **Comandos de sanity (sobre el proyecto real, solo lectura/verificación):**
  - `manage.py check` → *0 issues*.
  - `manage.py makemigrations --check --dry-run` → *No changes detected* (modelos ↔ migraciones sincronizados).
  - `manage.py showmigrations` → todas aplicadas en `db.sqlite3`.
  - `manage.py test` → **Ran 0 tests — NO TESTS RAN** (no existe ninguna prueba automatizada; los `tests.py` vacíos son de las apps stub raíz, no cuentan).
  - `pip list` (venv raíz) → Django 5.2.18, asgiref 3.12.1, psycopg2-binary 2.9.13, python-dotenv 1.2.4, sqlparse 0.6.0, tzdata 2026.5.
- **Pruebas funcionales (T01–T34):** sonda propia (`temp/.../citi_audit/probe.py`) usando `django.test.Client` + **base de datos de pruebas en memoria** del test runner — `db.sqlite3` y los archivos de la aplicación **no fueron modificados**. Resultado completo: `citi_audit/out2.json`.
- **Pruebas en vivo:** `manage.py runserver 8899` (DEBUG dev) + navegador automatizado (Playwright): login real docente y cliente, dashboard, calendario, reproducción del 500 (captura `.playwright-mcp/auditoria-500-cruz-rol.png`), consultas SQL **solo lectura** (`mode=ro`) a `db.sqlite3`.
- **No se realizaron:** pruebas de carga/concurrencia, escáner de CVEs externo, ataque alguno, escritura a BD real más allá de sesiones del navegador dev (equivalente a navegar).

## 2. Pruebas ejecutadas y resultados

| ID | Prueba | Resultado | Detalle |
|---|---|---|---|
| T01 | GET `/` anónimo auto-crea 7 cuentas demo | ✅ ejecutada | antes=0 despues=7 → confirma SEG-02 |
| T02 | Login demo cliente con portal correcto | ✅ PASS | 302 → `/panel/cliente/` |
| T03 | Login con portal (rol) equivocado | ✅ PASS con hallazgo | rechazado, pero revela el rol real → SEG-14 |
| T04 | Registro público con contraseña "123" | ❌ FAIL (seguridad) | cuenta creada con contraseña débil → SEG-13 |
| T05 | Matriz 5 roles × 5 dashboards (25 combinaciones) | ❌ FAIL (crítico) | las 20 cruzadas → **HTTP 500 NameError**; las 5 propias → 200. ningún 200 cruzado (no hay fuga de datos) → SEG-01 |
| T06 | Anónimo a los 5 dashboards | ✅ PASS | 5× 302 → login |
| T07 | Reserva 2º cliente en franja capacidad 1 | ✅ PASS | primero 200, segundo 409 (secuencial) |
| T08 | Misma cliente reserva 2× misma franja | ✅ PASS | 409 (constraint parcial funciona) |
| T09 | Subespecialidad de otra área | ✅ PASS | 400 |
| T10 | Reserva en franja MIXTO (sin catálogo de subesp.) | ✅ PASS (confirm. hallazgo) | 400 → mixto no reservable → FUN-09/F-26 |
| T11 | IDOR: docente B accede cita de docente A (detalle y gestión) | ✅ PASS | 404 / 404 |
| T12 | Coordinador Sistemas → cita Civil (detalle y asignar) | ✅ PASS | 404 / 404 (aislamiento OK) |
| T13 | Cliente A → detalle cita de Cliente B | ✅ PASS | 404 |
| T14 | Director → `/panel/cita/<id>/detalle/` | ✅ PASS (comport. actual) | 403 PermissionDenied (sin vista de director) |
| T15 | Coordinador asigna docente → cita ASIGNADA | ✅ PASS | 302; estado=asignada, docente_id set |
| T16 | Docente salta ASIGNADA→FINALIZADA | ⚠️ ejec. hallazgo | permitido → FUN-06 |
| T17 | Docente reabre FINALIZADA→ASIGNADA | ⚠️ ejec. hallazgo | permitido → FUN-06 |
| T18 | Docente intenta estado "cancelada" por form | ✅ PASS | rechazado (fuera de choices); estado intacto |
| T19 | Existe acción de cancelación en portal | ❌ NO IMPLEMENTADO | ninguna vista/URL → FUN-07 |
| T20 | Docente inyecta estudiante no-elegible como tutor | ✅ PASS | rechazado por form+limit_choices; apoyo no cambió |
| T21 | Promoción automática consultor→tutor al cumplir 8°/130/4.0 | ✅ PASS | student_type=tutor, autorizado=True |
| T22 | Degradación automática tutor→consultor | ✅ PASS | student_type=consultor |
| T23 | API eventos sin parámetro `end` | ✅ PASS | 400 controlado (no 500) |
| T24 | API reservar sin token CSRF (enforce) | ✅ PASS | 403 |
| T25 | Logout por GET | ⚠️ ejec. hallazgo | 302 y sesión cerrada → SEG-21 |
| T26 | GET dashboard cliente crea franjas demo si no hay activas | ➖ no disparó | había activas (todas vencidas); efecto verificado por lectura de código + estado real del calendario (T-live-1) |
| T27 | KPI director "franjas activas" | ⚠️ ejec. hallazgo | cuenta franjas vencidas (sin filtro de fecha) → FUN-26 |
| T28 | Acta: solo finalizada y solo docente dueño | ✅ PASS | 404 / 200 / 404 |
| T29 | Doble calificación del cliente | ✅ PASS | 302 luego 404; cal=5 única |
| T30 | Calificación 99 (fuera de rango) | ✅ PASS | rechazada; cal=None |
| T31 | Bitácora de estudiante asignado | ✅ PASS | 302; nota creada |
| T32 | Bitácora en cita ajena (estudiante no asignado) | ✅ PASS | 404 |
| T33 | Rol no-staff intenta `/admin/` | ✅ PASS | 302 a login admin |
| T34 | Cita sobre franja MIXTO: ¿algún coordinador puede verla/asignarla? | ⚠️ ejec. hallazgo | invisible y no asignable → FUN-09 confirmado |
| T-live-1 | Navegador real: login docente → dashboard con KPIs de BD; docente → `/panel/cliente/` | ❌ FAIL crítico | HTTP 500 "NameError at /panel/cliente/" con traceback |
| T-live-2 | Navegador real: cliente → calendario semana actual | ⚠️ hallazgo datos | 0 eventos: todas las franjas activas están en el pasado → FUN-12 |
| T-live-3 | `GET /agenda/api/eventos/` anónimo | ✅ PASS | 302 a login (endpoints API protegidos) |
| T-db-1 | Inspección read-only `db.sqlite3` | ✅ ejecutada | 10 usuarios, 9 franjas (todas ≤27/10), 4 citas (2 con subesp. vacía), 0 bitácoras; citas ligadas a cliente ≠ sembrado; duplicado de coordinador civil; sin cuenta director en seed |

## 3. Cobertura de pruebas automatizadas del proyecto

**Inexistente (0 tests).** No hay ni una sola prueba de: roles/permisos, ciclo de cita, reserva/cupo, elegibilidad de tutor, IDOR, registro, acta, feedback, migraciones. `manage.py test` pasa vació → da falsa sensación de salud.

## 4. Pruebas pendientes (a implementar, por prioridad)

**P0 — deben existir antes de la siguiente fase (unitarias/integración rápidas):**
1. `test_role_required_matrix`: las 25 combinaciones rol×URL → sin excepciones; cruzadas → 302 al propio dashboard. *(Atraparía SEG-01 de inmediato.)*
2. `test_reserva_capacidad_y_doble`: secuenciales como T07/T08 + **prueba de carrera** con dos hilos/futures sobre la misma franja (revela FUN-05; requiere SQLite WAL o PG para reproducirse).
3. `test_estadomaquina`: transiciones válidas/inválidas de `CitaAsesoria` (incl. prohibir reapertura y reasignación por docente → FUN-06/T20).
4. `test_idor_4x4`: docente/coordinador/cliente/estudiante contra citas ajenas (T11-T13, T28, T32).
5. `test_register_password_validators` (SEG-13) y `test_login_role_mismatch_message` (SEG-14).

**P1:**
6. `test_area_mixto`: reservable/asignable según la regla que se decida adoptar (FUN-09).
7. `test_cancelacion` cuando se implemente (FUN-07).
8. `test_seed_no_automatico`: GET `/` y `/cuenta/login/` no escriben usuarios (SEG-02).
9. `test_upload_validacion`: rechazar .html/exe, exceder tamaño, y la vista de descarga exige propiedad (SEG-04).

**P2:**
10. Smoke de migración limpia: `migrate` sobre SQLite vacío + `seed_demo_users` + `check`.
11. Test de KPIs del director con datos fronterizos (vencidas/inactivas).
12. Test de flujo completo E2E (Playwright) cliente→coordinador→docente→cliente (feedback).

**No pudo verificarse en esta fase:** comportamiento real bajo PostgreSQL, despliegue HTTPS, CVE scan externo, carga de concurrencia, y experiencia móvil en dispositivo físico (solo revisión CSS).
