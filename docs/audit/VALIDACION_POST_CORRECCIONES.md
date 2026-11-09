# Validación post-correcciones — Fase 02 (bloqueantes)

**Fecha:** 8/11/2026 · **Alcance:** B-1 a B-5 de `PLAN_CORRECCIONES.md` +
preparación de datos demo + validación E2E y visual.
**Base de datos:** las 42 pruebas corren en BD de pruebas aislada; la base de
desarrollo `db.sqlite3` solo fue escrita por el comando legítimo `seed_demo`
(más dos artefactos de validación propios, borrados explícitamente).

---

## 1. Cambios aplicados

| # | Archivo | Cambio | Hallazgo que cierra |
|---|---|---|---|
| 1 | `backend/portal/decorators.py` | Import `redirect` faltante en `role_required` | **SEG-01 / B-1** |
| 2 | `backend/portal/views.py` | Eliminado autoseed desde `landing` y `_ensure_demo_franjas_horarias` del dashboard cliente (función suprimida); limpieza de imports | **SEG-02 / B-4, FUN-12** |
| 3 | `backend/accounts/views.py` | Eliminado `ensure_demo_users()` de `login_view` | **SEG-02 / B-4** |
| 4 | `backend/accounts/demo_seed.py` | Reescrito como semilla demo **explícita e idempotente**: +director staff, perfiles académicos reales que promueven tutores por umbrales (sin forzar rol), franjas futuras deterministas (tz Bogotá, sin solapes, capacidad 2), 7 solicitudes cubriendo pendiente/asignada/en proceso/finalizada+feedback, archivo no destructivo de vencidas con nota de trazabilidad y **reubicación** de citas del plan cuando su franja vence | **B-2, SEG-02** |
| 5 | `backend/accounts/management/commands/seed_demo.py` | Nuevo comando con `--solo-usuarios` y **rechazo en `DJANGO_ENV=produccion`** | **B-4** |
| 6 | `backend/accounts/management/commands/seed_demo_users.py` | Delegado a `ensure_demo_users()` (compatibilidad) | B-4 |
| 7 | `backend/config/settings.py` | Modelo de entornos `desarrollo`/`produccion`; `SECRET_KEY` sin fallback en producción (falla el arranque); `DJANGO_DEBUG` controlado (producción fuerza 0 y rechaza 1); `ALLOWED_HOSTS` obligatorio en producción; carga `.env` vía python-dotenv; bloque de endurecimiento (HSTS/SSL/cookies) solo en producción → localhost/HTTP de la demo **no** se rompe | **SEG-03 / B-3** |
| 8 | `backend/.env.example` | Nueva — documenta todas las variables (ver `docs/demo/VARIABLES_ENTORNO.md`) | B-3 |
| 9 | `backend/accounts/forms.py` | `ClientRegistrationForm` aplica `validate_password()` (longitud/común/numérica/similitud) | **SEG-13 / B-5** |
| 10 | `backend/portal/tests.py` | **Nueva suite: 42 pruebas** (matriz de roles, reservas, máquina de estados vigente, IDOR, registro, seed idempotente/reubicación/bloqueo producción, CSRF, E2E completo) | **B-5** |
| 11 | `backend/{portal,accounts,scheduling}/__init__.py` | Paquetes de app explícitos — el discovery de `unittest` no encontraba tests en namespace packages (causa del "0 tests" original) | B-5 (habilitador) |
| 12 | `AGENTS.md` | Actualizadas afirmaciones obsoletas (autoseed, .env, presencia de pruebas, comando seed_demo) | documentación |

## 2. Pruebas automatizadas

```text
manage.py check                          → 0 issues
manage.py makemigrations --check         → No changes detected
manage.py test                           → Ran 42 tests — OK  (43 s, BD aislada)
```

Cobertura P0 solicitada (todas verdes):

| P0 | Prueba | Resultado |
|---|---|---|
| 1 | Matriz 5 roles × 5 portales: propio=200, cruzado=302 al propio, anónimo=302 login, **sin ningún 500** | ✅ `RoleAccessMatrixTests` (5 casos) |
| 2 | Reserva válida + duplicada (misma cliente/franja 409) + capacidad agotada + subesp de otra área + franja inactiva/vencida + constraint parcial a nivel SQL | ✅ `ReservasApiTests` (10) + `test_constraint_doble_reserva_activa` |
| 3 | Transiciones permitidas (solicitada→asignada→en_proceso→finalizada) y denegadas (cancelada por docente, volver a solicitada, cambio de estado por cliente, tutor no elegible) | ✅ `StateMachineTests` (7) |
| 4 | IDOR: docente/coordinador/cliente/estudiante contra citas ajenas (detalle, gestión, acta, bitácora, feedback) | ✅ `IdorTests` (4) |
| 5 | Registro: contraseñas débiles/comunes/numéricas rechazadas, coincidencia exigida, email duplicado, rol forzado a cliente, login posterior | ✅ `RegistroValidacionTests` (5) |
| — | Semilla: landing/login/dashboard NO escriben; `seed_demo` idempotente; reubicación tras vencimiento; bloqueo en producción; tutor por umbrales | ✅ `SeedDemoTests` (5) |
| — | Regresiones auditadas: feedback una vez y rango, bitácora+timeline, promoción/degradación, CSRF API, acta+admin | ✅ `RegresionesAuditTests` (6) |

### Equivalencia con las 34 pruebas de la auditoría (MATRIZ_DE_PRUEBAS.md Fase 01)

T01/T26 → inveridos y reforzados (ahora verifican que **no** se siembra en GET);
T02–T04 → cubiertos (login portal correcto/incorrecto, registro con
validación); T05–T06 → `test_matriz_rol_x_portal`/anonimos; T07–T10 →
`ReservasApiTests`; T11–T14 → `IdorTests`+matriz; T15–T20 →
`StateMachineTests`; T21–T22 → promoción/degradación; T23 → eventos sin `end`;
T24 → CSRF; T27 → matriz E2E (KPI director se renderiza con datos); T28–T32 →
acta/feedback/bitácora; T33 → admin 302; T34 → la franja MIXTO sigue siendo
hallazgo I-5 **abierto** (no bloqueante; cubierto por `test_…mixto` de reserva
400). Ninguna cobertura anterior quedó reducida.

## 3. Validación de extremo a extremo (sección 7)

Automatizada en `EndToEndDemoTests.test_ciclo_completo` (aislada) **y** en vivo
sobre la base de desarrollo:

| Paso | Resultado en vivo (runserver + navegador Playwright) |
|---|---|
| 1–2. Login cliente → franjas | 14 eventos en la semana; calendario con "Disponible (2)" |
| 3. Reservar en vivo (clic franja → subesp web → confirmar) | `POST /agenda/api/reservar/ → 200`, cita apareció en "Mis citas" (8 filas) |
| 4. Verificar solicitud | fila "Desarrollo Web – Solicitada" visible; **artefacto de prueba eliminado después** (cleanup documentado, solo borra lo creado por esta validación) |
| 5–6. Coordinador → asignación modal | bandeja Sistemas con solicitud; modal carga cita #5 con datos del cliente |
| 7–8. Docente → gestionar y finalizar | KPI "2 casos"; caso #8 finalizado muestra botón de acta; `GET …/acta/ → 200` con calificación impresa |
| 9. Cliente feedback | 2 finalizadas sembradas con calificación 5 y 4 persistidas |
| 10–11. Director | `/panel/director/` 200: 11 usuarios / 40 franjas / 5 citas reservadas — coherente con el estado |
| Cruce de roles (regresión B-1) | docente → `/panel/cliente/` → **302 a su portal** (antes: 500 NameError); log del servidor confirma `GET /panel/cliente/ 302` |
| Estudiante | banner "Habilitado como Estudiante Consultor", 1 caso, promedio 4,50 |

Capturas: `.playwright-mcp/validacion-1-cliente-calendario.png`,
`validacion-2-coordinador.png`, `validacion-3-director.png` y
`auditoria-500-cruz-rol.png` (evidencia ANTES para contraste).

## 4. Verificación visual (sección 8, preliminar sin rediseño)

- Cinco portales renderizan con datos reales; login por portal de rol correcto.
- Calendario de reservas pueblado (el bloqueante de la Fase 01 estaba en datos).
- Formularios (asignar, caso docente, bitácora, feedback, registro) presentan
  errores de validación legibles.
- Errores: ninguno nuevo. El favicon 404 y la barra lateral de navegación vacía
  siguen como UX pendiente (F-5/F-6 del plan), no bloqueantes.
- Nota operativa: tras el cambio de `SECRET_KEY` de desarrollo, sesiones de
  navegador antiguas se invalidan una vez ("Session data corrupted" en log →
  nuevo login). Efecto único esperado, no regresión.

## 5. Criterios de aceptación de la fase — estado

| Criterio | Estado |
|---|---|
| SEG-01 corregido | ✅ (código + prueba + verificación en vivo) |
| Cinco portales accesibles según permisos | ✅ matriz 5×5 verde |
| Existe Director de prueba | ✅ `director@citi.ucc.edu.co` (is_staff) |
| Existe tutor válido (promovido por requisitos, sin forzar rol) | ✅ 2 estudiantes; señal/save del modelo |
| Hay franjas futuras reservables | ✅ 40 activas futuras; reserva en vivo 200 |
| Cliente demo puede registrar solicitudes | ✅ verificado en navegador real |
| Ciclo de asesoría completa | ✅ E2E automatizado y manual |
| Pruebas P0 pasan | ✅ 42/42 |
| Pruebas anteriores no reducidas | ✅ equivalencia mapeada en §2 |
| DEBUG y secretos gestionados | ✅ modo `produccion` exige secreto/hosts y fuerza DEBUG=0; `.env.example` documentado |
| Autoseed explícito e idempotente | ✅ `seed_demo`; GETs ya no escriben |
| Sin funcionalidad eliminada | ✅ único side-effect GET retirado se sustituye por comando; nada más suprimido |

## 6. Problemas abiertos (heredan el plan, no bloquean la demo)

| Ref | Problema | Plan |
|---|---|---|
| FUN-05 | Carrera de sobre-reserva sin `select_for_update` (no reproducido bajo carga; riesgo real en PostgreSQL) | I-1 |
| FUN-06 | Máquina de estados laxa: docente reabre finalizada y cambia tutor | I-2 |
| SEG-04 | Uploads sin validación servidor; `/media/` sin vista con permisos | I-3 |
| FUN-07/08 | Cancelación y recuperación de contraseña inexistentes | I-4 / F-1 |
| FUN-09 | Área MIXTO huérfana | I-5 |
| FUN-10 | `tipo_servicio` sin efecto operativo | I-6 |
| FUN-11 | KPI "horas/créditos" con fórmula arbitraria | I-8 |
| SEG-14/15/21/22 | Enumeración de cuentas, errores internos en API, logout GET, innerHTML | I-7 |
| UX | Sidebar sin navegación y oculto en móvil sin menú; acta=HTML | F-4/F-5 |
| Docs | ERD desfasado aún (se documentó la discrepancia; reescribirlo es I-10) | I-10 |
