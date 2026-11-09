# AUDITORÍA DE SEGURIDAD — CITI

**Estándar de referencia:** OWASP Top 10 (2021) + checklist de seguridad de Django.
**Clasificación:** CRÍTICO / ALTO / MEDIO / BAJO. Cada hallazgo incluye evidencia y pasos de reproducción cuando fueron confirmados. Los no confirmados se marcan como **riesgo potencial** o **no verificado**.

---

## Hallazgos confirmados por ejecución

### SEG-01 — CRÍTICO — Fallo de la autorización por `NameError`: toda URL cruzada devuelve HTTP 500

- **Archivo/ubicación:** `backend/portal/decorators.py:21` (función `role_required`).
- **Problema:** el decorador llama `redirect(dashboard_url_for_role(user.role))` sin haber importado `redirect` de `django.shortcuts`. Cuando un usuario autenticado accede a una URL de otro rol (la ruta "amable" del decorador), Python lanza `NameError` → respuesta 500. Con `DEBUG=1` la página muestra traceback, settings y código fuente.
- **Evidencia:**
  - Prueba T05 (base de datos de pruebas): las 20 combinaciones rol×portal cruzadas devolvieron `EXC NameError: name 'redirect' is not defined`.
  - Reproducción en servidor real (`runserver`): docente autenticado navega a `/panel/cliente/` → `Internal Server Error: /panel/cliente/ ... NameError: name 'redirect' is not defined` en la consola y página *"NameError at /panel/cliente/"* en el navegador (captura: `.playwright-mcp/auditoria-500-cruz-rol.png`).
  - El defecto está en el commit publicado `86b15ac` en GitHub, no solo en el árbol local.
- **Impacto:** (a) caída visible de la aplicación ante cualquier navegación entre portales (un docente que escriba `/panel/cliente/` ve un traceback con la configuración); (b) exposición de código fuente y settings mientras `DEBUG=1`; (c) la denegación de acceso funciona por accidente (nadie ve datos ajenos), pero el canal de error filtra estructura interna.
- **Reproducción:** iniciar sesión como docente y abrir `/panel/cliente/` (o cualquier panel de otro rol).
- **Solución:** `from django.shortcuts import redirect` en `decorators.py`. Añadir prueba automatizada de la matriz rol×URL.
- **Prioridad:** 1 (una línea; bloqueante de demo).

### SEG-02 — CRÍTICO (si se despliega) — Credenciales demo públicas y auto-sembradas por GET anónimo

- **Archivo/ubicación:** `backend/accounts/demo_seed.py` (contraseña fija `DEMO_PASSWORD`, 7 cuentas), `backend/portal/views.py:73-76` (`landing`) y `backend/accounts/views.py:33-36` (`login_view`).
- **Problema:** toda visita anónima a `/` o `/cuenta/login/` ejecuta `ensure_demo_users()`, que crea coordinadores, docentes, estudiantes y un cliente con contraseña fija y **hardcoded en el repositorio público de GitHub** (y documentada además en `AGENTS.md`). No hay forma de desactivar el seed ni en producción.
- **Evidencia:** prueba T01: GET `/` anónimo en BD limpia creó 7 usuarios (`antes=0 despues=7`); T02: login exitoso con esas credenciales.
- **Impacto:** quien tenga el repo (alumnos, jueces, internet) puede entrar a todos los portales con datos reales si el sistema se expone en red (incluso en la LAN del campus). Escalada trivial a datos de clientes/empresas.
- **Reproducción:** `git clone` → `migrate` → abrir `/` → iniciar sesión con el correo sembrado y la contraseña del repo.
- **Solución:** mover el seed detrás de un comando de gestión (`seed_demo_users`, ya existe) y quitar la llamada automática de `landing`/`login`; desactivar en producción con flag; no publicar contraseñas en el repo (o usar una distinta por instalación y no documentarla).
- **Prioridad:** 1 si hay cualquier exposición de red; 2 si la demo es 100 % local (documentar la decisión).

### SEG-03 — CRÍTICO condicional / ALTO para la demo — Configuración insegura por defecto

- **Archivo/ubicación:** `backend/config/settings.py:7-14` (fallback de `SECRET_KEY`, `DJANGO_DEBUG` default `'1'`), ausencia total de endurecimiento HTTPS/cookies.
- **Problema:** sin variables de entorno, la app arranca con `DEBUG=True` y una `SECRET_KEY` conocida (está en el repo). Consecuencias: (a) las páginas de error filtran fuente y settings (combinado con SEG-01, ya se observó en vivo); (b) con la clave pública un atacante puede forjar cookies de sesión firmadas; (c) no hay `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `X_FRAME_OPTIONS` explícito, ni CSP.
- **Evidencia:** lectura de `settings.py`; cabeceras observadas en `runserver` (sin HSTS/CSP; `X-Frame-Options: DENY` por default de Django).
- **Impacto:** nulo en localhost académico; severo en cualquier hosting real.
- **Solución:** invertir el default (`DEBUG` solo con `DJANGO_DEBUG=1` explícito en docs), exigir `SECRET_KEY` (fallar el arranque si falta), bloque de seguridad condicional `if not DEBUG:` con HSTS/HTTPS/cookies. Documentar variables obligatorias.
- **Prioridad:** 2 (antes de presentar si el sistema sale del portátil; bloque rápido de settings).

### SEG-04 — ALTO — Subida/descarga de archivos sin validación ni control de acceso

- **Archivo/ubicación:** `backend/scheduling/views.py:112-161` (`reservar_cita_api`), `backend/scheduling/models.py:89-94` (`archivo_adjunto`), `backend/config/urls.py:13-14` (`static(MEDIA_URL)` en DEBUG), `backend/templates/portal/partials/cita_info_block.html:44-49` y `coordinador_asignar.html:19-26` (enlaces directos a `archivo.url`).
- **Problema:**
  1. El servidor **no valida tipo MIME, extensión ni tamaño** del archivo (el `accept="pdf,doc,zip..."` es solo del navegador; se omite con `curl`). `CitaAsesoria.clean()` no toca el campo. Un `.html`/`.svg` subido se sirve después desde el **mismo origen** bajo `/media/` → XSS almacenado para cualquiera que abra el enlace o lo inyecte en el modal de detalle.
  2. `/media/` se sirve en DEBUG **sin autenticación ni verificación de rol**: cualquier persona que sepa/acierte la ruta (el nombre original del archivo se conserva — en la BD real hay `Punto_3_y_4.docx` — y el formato `documentos_citas/YYYY/MM/` es predecible) puede descargar documentos confidenciales de empresas. Los enlaces del portal apuntan a esas URLs directas en lugar de a una vista con permisos.
  3. Sin `DEBUG`, **no hay ninguna vista que sirva el adjunto** → la descarga dejaría de funcionar en producción (funcionalidad incompleta además de riesgo).
- **Evidencia:** código; presencia de archivos reales con nombre legible en `backend/media/documentos_citas/2026/10/`; ausencia de `FileField(validators=...)`, de vista de descarga y de `validators` de tamaño. Riesgo de tamaño: `DATA_UPLOAD_MAX_MEMORY_SIZE`/`FILE_UPLOAD_MAX_MEMORY_SIZE` no limitan el tamaño total de subida → disco lleno (DoS).
- **Reproducción sugerida (no ejecutada para no ensuciar el repo):** `curl -F "franja_id=…; subespecialidad=web; archivo_adjunto=@evil.html" /agenda/api/reservar/` autenticado como cliente y abrir `/media/documentos_citas/.../evil.html`.
- **Impacto:** robo de documentos entre clientes/empresas, XSS almacenado, DoS por disco.
- **Solución:** validar en el servidor (extensión/MIME en lista blanca, tope de tamaño, renombrar con `uuid`), servir descargas por una vista `login_required` + chequeo de rol/propiedad con `FileResponse(as_attachment=True)`; en producción, media detrás de auth.
- **Prioridad:** 3.

### SEG-13 — ALTO/MEDIO — Registro público sin validación de contraseñas

- **Archivo/ubicación:** `backend/accounts/forms.py:8-43` (`ClientRegistrationForm.save`).
- **Problema:** no se llama `validate_password()`; los `AUTH_PASSWORD_VALIDATORS` de settings solo se aplican en `createsuperuser`/admin. Las únicas reglas son "password1 == password2".
- **Evidencia:** prueba T04 confirmada: usuario registrado con contraseña `"123"` y login posterior posible.
- **Impacto:** cuentas cliente con contraseñas triviales; diccionario obvio de cuentas demo.
- **Solución:** `password_validation.validate_password(user.password1, user)` en `save()`/`clean()`.
- **Prioridad:** 4.

### SEG-14 — MEDIO — Enumeración de cuentas y revelación de rol en el login

- **Archivo/ubicación:** `backend/accounts/forms.py:75-79`.
- **Problema:** si las credenciales son correctas pero el `expected_role` no coincide, el mensaje dice «Esta cuenta pertenece al portal «X»»: confirma al atacante que el correo existe y su rol. No hay throttling/rate-limit en el login.
- **Evidencia:** prueba T03 (respuesta contenía "pertenece al portal").
- **Solución:** mensaje neutro ("correo, contraseña o portal incorrectos") + `django_ratelimit` o `Axes` en `/cuenta/login/`.
- **Prioridad:** 5.

### SEG-15 — MEDIO — Fuga de detalles internos en la API de reserva

- **Archivo/ubicación:** `backend/scheduling/views.py:149-153`.
- **Problema:** `except Exception as exc: {'error': str(exc)}` devuelve texto crudo de excepciones (incluidos mensajes de base de datos y validación) al cliente; además el cliente lo inyecta en `innerHTML` (ver SEG-22).
- **Solución:** errores conocidos → mensajes controlados; genéricos → log + mensaje fijo.
- **Prioridad:** 6.

### SEG-21 — BAJO — Logout por GET

- **Archivo/ubicación:** `backend/accounts/views.py:58-62` + URL `path('logout/')`.
- **Problema:** `GET /cuenta/logout/` cierra sesión sin CSRF token (el formulario del sidebar usa POST, pero el endpoint acepta GET). Permite logout forzado desde una página hostil (molestia, no compromiso).
- **Solución:** `@require_POST`.
- **Prioridad:** 8.

### SEG-22 — BAJO (latente) — `innerHTML` con cadenas del servidor en el dashboard cliente

- **Archivo/ubicación:** `backend/templates/portal/dashboard_cliente.html:183, 304`.
- **Problema:** `showAlert(data.error)` inserta en `innerHTML` el string devuelto por la API. Hoy esos strings no reflejan entrada del usuario (validaciones propias), pero con SEG-15 cualquier mensaje de excepción futuro (p. ej., un dato importado vía admin) podría contener HTML → DOM-XSS.
- **Solución:** `textContent` en lugar de `innerHTML` (montando el div con API DOM).
- **Prioridad:** 8.

### SEG-23 — BAJO — Sesiones tras desactivar usuario

- Usuario `is_active=False` desde admin conserva sesión activa hasta expiración (14 días por default) porque no se re-valida por request. Efecto estándar de Django; mencionar en operación. **No verificado en runtime** (riesgo conocido de framework).

---

## Controles que SÍ existen y fueron verificados

| Control | Verificación | Resultado |
|---|---|---|
| CSRF global (`CsrfViewMiddleware`) | T24: POST `/agenda/api/reservar/` sin token (cliente con `enforce_csrf_checks`) | ✅ 403 |
| Tokens en formularios y modal | Revisión de plantillas (`{% csrf_token %}` en login, registro, asignación, bitácora, feedback, modal) | ✅ presentes |
| XSS por plantillas | Grep: ningún uso de `|safe` ni `mark_safe`; autoescape activo; `json_script` para datos; `escapejs` en labels | ✅ |
| SQL injection | ORM exclusivamente; ningún `raw()`, `extra()` ni `execute()` con concatenación | ✅ |
| IDOR citas/detalle/acta/bitácora/feedback | T11, T12, T13, T28, T32 (docente B vs cita A, coordinador vs otra área, cliente vs cita ajena, estudiante no asignado) | ✅ 404 en todos |
| Autorización en backend (no solo botones ocultos) | Matriz T05 + T06 anónimos + filtros de queryset en todas las vistas | ✅ (funcional aparte del crash SEG-01) |
| Aislamiento de área de coordinadores | T12: bandeja, asignar y detalle filtrados por `franja__area` | ✅ |
| `/admin/` protegido | T33: roles no-staff no acceden | ✅ |
| Contraseñas hasheadas | PBKDF2 default de Django (columna `password` del DB read-only) | ✅ |
| `limit_choices_to` y validación de modelo en FKs de cita | T20: docente no pudo inyectar estudiante no-elegible | ✅ |
| `X-Frame-Options` | Default de `XFrameOptionsMiddleware` = DENY | ✅ |
| No hay CORS abierto | Sin `django-cors-headers` ni cabeceras `Access-Control-Allow-*` | ✅ (no aplica) |
| Restricción de registro público a rol cliente | Lectura de `ClientRegistrationForm.save()` (fuerza `role=CLIENTE`) + prueba T04 (cuenta creada rol cliente) | ✅ |

## Riesgos potenciales no reproducibles en esta fase

- **R-01 Race de reserva (overbooking):** ver `AUDITORIA_FUNCIONAL.md` FUN-05. Ausencia total de `transaction.atomic`/`select_for_update` (grep en todo `backend/` = 0 coincidencias). No se generó carga concurrente real.
- **R-02 Escaneo CVE de dependencias:** no ejecutado (sin herramienta externa autorizada). Estado de versiones: Django 5.2.18 (rama 5.2 = LTS), psycopg2-binary 2.9.13, asgiref 3.12.1, sqlparse 0.6.0, python-dotenv 1.2.4, tzdata 2026.5. Sin dependencias conocidas vulnerables según revisión de versiones; no sustituye un `pip-audit`.
- **R-03 Comportamiento real en HTTPS/producción:** el proyecto nunca se ha desplegado; todos los hallazgos condicionales (SEG-03, parte de SEG-04) dependen de ello.
- **R-04 Ficción de sesiones concurrentes:** `django_session` tiene 3 sesiones vigentes en la BD local (incluida la de esta auditoría); sin impacto.
