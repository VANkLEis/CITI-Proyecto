# CITI — Consultorio de Ingeniería, Tecnología e Innovación (UCC)

Plataforma del CITI de la Universidad Cooperativa de Colombia, campus
Ibagué–El Espinal. Tiene dos zonas:

- **Zona pública:** portada, portafolio de proyectos, catálogo de talleres y
  formulario de diagnóstico estratégico.
- **Zona privada:** paneles por rol (cliente, estudiante, docente, coordinador,
  director), reserva de citas, seguimiento, entregables, actas, trazabilidad e
  indicadores. Incluye una bandeja de **triage** para clasificar las solicitudes
  públicas y convertirlas en citas.

Django 5.2 · SQLite/PostgreSQL · Gunicorn + WhiteNoise · Docker Compose.

---

## Inicio rápido

### Opción A · Windows, un doble clic

1. Abre **Docker Desktop** y espera a que el motor esté activo.
2. Ejecuta **`iniciar_citi.bat`** en la raíz del proyecto.
3. El script construye la imagen, levanta PostgreSQL 16, siembra los datos demo
   y abre **<http://localhost:8000>**.

### Opción B · Manual

```bash
docker compose up -d --build
```

Luego abre **<http://localhost:8000>**.

Qué hace el contenedor al arrancar (`entrypoint.sh`):

1. `manage.py migrate` sobre PostgreSQL 16.
2. `manage.py seed_demo_data` (idempotente): usuarios de los 5 roles, franjas,
   citas en todos los estados, portafolio, talleres y solicitudes públicas.
3. Gunicorn en `0.0.0.0:8000` con estáticos servidos por WhiteNoise.

Espera a que PostgreSQL esté sano (`pg_isready`) antes de arrancar la app.

### Comandos útiles

```bash
docker compose logs -f web          # ver el arranque
docker compose exec web python manage.py seed_demo_data   # recargar sin borrar
docker compose exec web python manage.py test             # suite completa
docker compose down                 # detener (conserva datos)
docker compose down -v              # detener y BORRAR base + media
docker compose up -d --build        # reconstruir tras cambiar código
```

Variables opcionales: copiar `docs/demo/env.docker.example` a `.env` (puerto,
contraseña demo, workers). El puerto también se cambia con `PORT=8080`.

---

## Estructura del proyecto

La raíz solo tiene tres carpetas de contenido: `backend/`, `docs/` y `tools/`.
Los entornos virtuales, cachés, medios y estáticos recolectados quedan fuera del
paquete de entrega.

```text
CITI-Proyecto/
├─ iniciar_citi.bat              Arranque rápido en Windows
├─ Dockerfile
├─ docker-compose.yml
├─ render.yaml                   Blueprint de Render (free)
├─ entrypoint.sh
├─ requirements.txt
├─ README.md · AGENTS.md
├─ backend/                      Único proyecto Django (patrón MVT)
│  ├─ manage.py
│  ├─ config/                    settings.py · urls.py · wsgi.py
│  ├─ accounts/                  Usuarios, empresas, perfiles, seed
│  ├─ scheduling/                Franjas, citas, eventos, solicitudes públicas
│  ├─ portal/                    Vistas públicas, paneles, triage, indicadores
│  ├─ templates/                 portal/index.html, paneles y partials
│  └─ static/                    CSS, JS, imágenes, videos y fuentes locales
├─ docs/
│  ├─ demo/                      Credenciales, datos y guion de demostración
│  ├─ presentacion/              Entregables finales de la sustentación
│  ├─ sustentacion/              Diagramas, fuentes, evidencias y scripts
│  ├─ prototipo/                 Archivo histórico del prototipo Hi-Fi
│  └─ audit/                     Auditoría técnica de referencia
└─ tools/                        Generación reproducible de imágenes y videos
```

> `docs/prototipo/` conserva la maqueta visual anterior como evidencia. No es
> la plataforma real, no usa el backend y no se copia a la imagen Docker.

---

## Arquitectura MVT (Model · View · Template)

El proyecto sigue el patrón **MVT de Django** dentro de `backend/`. No hay una
SPA separada ni apps duplicadas en la raíz: los modelos, las vistas, las URLs y
las plantillas viven en un único proyecto.

| Capa | Responsabilidad | Archivos principales |
|---|---|---|
| **Enrutador** | Punto de entrada y despacho de URLs | `backend/config/urls.py` · `backend/portal/urls.py` |
| **Models** | Entidades, relaciones, validaciones y reglas de datos | `backend/accounts/models.py` · `backend/portal/models.py` · `backend/scheduling/models.py` |
| **Views** | Control de la petición, permisos, consultas y respuesta | `backend/accounts/views.py` · `backend/portal/views.py` · `backend/portal/views_public.py` · `backend/scheduling/views.py` |
| **Templates** | HTML con herencia, partials y contexto | `backend/templates/portal/index.html` (portada principal) · `backend/templates/base.html` · `backend/templates/dashboard_base.html` |
| **Config** | Settings, WSGI y estáticos | `backend/config/settings.py` · `backend/config/wsgi.py` |

### Flujo de una petición a la portada

```text
GET /
  └─ backend/config/urls.py          include('portal.urls')
      └─ backend/portal/urls.py      path('', views_public.landing, name='landing')
          └─ backend/portal/views_public.py
              ├─ backend/portal/models.py            ProyectoPortafolio · Taller
              └─ backend/templates/portal/index.html   respuesta HTML
```

`backend/templates/portal/index.html` es la portada principal. Hereda de
`public_base.html`, recibe los proyectos y talleres publicados desde la vista y
renderiza el HTML final. Las plantillas de los paneles heredan de
`dashboard_base.html`.

---

## Credenciales de demostración

Contraseña única: **`CITIPass2026*`** (configurable con `CITI_DEMO_PASSWORD`).

| Rol | Correo | Portal |
|---|---|---|
| Director CITI | `director@citi.ucc.edu.co` | `/cuenta/login/?rol=director` |
| Coordinador Sistemas | `coordinador@citi.ucc.edu.co` | `/cuenta/login/?rol=coordinador` |
| Docente Sistemas | `docente@citi.ucc.edu.co` | `/cuenta/login/?rol=docente` |
| Estudiante tutora | `estudiante@citi.ucc.edu.co` | `/cuenta/login/?rol=estudiante` |
| Cliente / Empresa | `cliente@empresatolima.co` | `/cuenta/login/?rol=cliente` |

Variantes del set demo, misma contraseña:
`coordinador.civil@citi.ucc.edu.co`, `docente.civil@citi.ucc.edu.co`,
`estudiante.civil@citi.ucc.edu.co`, `fundacion@citi.ucc.edu.co`,
`emprendimiento@citi.ucc.edu.co` y `pyme@citi.ucc.edu.co`.

El login es **por rol**: si la cuenta no coincide con el portal elegido, el
sistema lo indica. Detalle completo en
[`docs/demo/CUENTAS_DE_PRUEBA.md`](docs/demo/CUENTAS_DE_PRUEBA.md) y guion en
[`docs/demo/GUIA_DEMOSTRACION.md`](docs/demo/GUIA_DEMOSTRACION.md).

---

## Rutas principales

| Ruta | Qué es |
|---|---|
| `/` | Portada pública |
| `/portafolio/` | Portafolio filtrable por línea |
| `/talleres/` | Catálogo de talleres |
| `/talleres/solicitar/` | Solicitud de charla o taller |
| `/diagnostico/` | Formulario de diagnóstico estratégico |
| `/privacidad/` | Tratamiento de datos |
| `/panel/solicitudes/` | **Triage** de solicitudes públicas (Director y Coordinador) |
| `/panel/director/` | Panel ejecutivo |
| `/panel/coordinador/` | Bandeja de asignación |
| `/panel/docente/`, `/panel/estudiante/`, `/panel/cliente/` | Paneles por rol |
| `/panel/seguimiento/` | Seguimiento del equipo |
| `/panel/trazabilidad/` | Trazabilidad e indicadores (+ CSV) |
| `/admin/` | Administración (Director demo es `is_staff`, no superusuario) |

---

## Recorrido de demostración (6–8 minutos)

1. `/` → hero, dos líneas de atención (`#modalidades`), capacidades.
2. `/portafolio/` → filtrar por Civil y abrir un caso.
3. `/talleres/` → solicitar un taller.
4. `/diagnostico/` → enviar una solicitud y anotar el radicado `SOL-…`.
5. Login **director** → `/panel/solicitudes/` → abrir la solicitud →
   **Aprobar** (línea + área + subespecialidad) → **Convertir y asignar**
   (franja + docente + tutor).
6. Abrir la cita creada: el historial muestra el evento con el código del
   radicado.

Guion detallado y contingencias:
[`docs/demo/GUIA_DEMOSTRACION.md`](docs/demo/GUIA_DEMOSTRACION.md).

Solicitudes ya sembradas para no improvisar:

| Código | Estado | Sirve para |
|---|---|---|
| `DEMO-SOL-001` | Recibida | Aprobar un taller (no genera cita) |
| `DEMO-SOL-002` | En revisión | Cliente sin NIT → NIT `PENDIENTE-…` |
| `DEMO-SOL-003` | Aprobada | Convertir + asignar docente |
| `DEMO-SOL-004` | Aprobada | Taller aprobado, sin cita |

---

## Desarrollo local (sin Docker)

Requiere Python 3.12+ y el `venv` de la raíz (Django 5.2.x).

```powershell
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py seed_demo_data
..\venv\Scripts\python.exe manage.py runserver
```

Abrir <http://127.0.0.1:8000>.

> Hay tres entornos virtuales en el repositorio: usar **`venv/`** (raíz).
> `.venv/` tiene otra instalación de Django 5.2.19 y `backend/venv/` no tiene Django.

### Pruebas

```powershell
cd backend
..\venv\Scripts\python.exe manage.py check
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test
```

200 pruebas: matriz de roles, reservas, estados, IDOR, registro, seed,
trazabilidad, indicadores, seguimiento, interacciones, aprobaciones, la zona
pública + triage (`backend/portal/test_public.py`), seguridad de sesión, botón
Volver y medios únicos.

---

## Contenido público y medios

- 8 proyectos publicados (4 Civil y 4 entre Sistemas/IA/Impacto) y 6 talleres
  activos (3 Sistemas y 3 Civil).
- 17 imágenes únicas en `backend/static/images/landing/`, 3 videos Ken Burns en
  `backend/static/videos/`, FullCalendar 6.1.15 y Open Sans locales.
- Cero CDNs en la aplicación: los recursos se sirven desde `backend/static/`.
- Créditos y licencias de las imágenes:
  [`docs/demo/CREDITOS_IMAGENES.md`](docs/demo/CREDITOS_IMAGENES.md) (interno).

La portada usa `<video>` con `poster` y una imagen de respaldo. Los 3 MP4 están
incluidos y se generaron con efecto Ken Burns desde los pósters locales. Siguen
siendo reemplazables: si se eliminan, se ve el poster y la imagen de respaldo.
Especificaciones y regeneración en
[`backend/static/videos/README.md`](backend/static/videos/README.md) y
[`tools/README.md`](tools/README.md).

---

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/demo/GUIA_DEMOSTRACION.md`](docs/demo/GUIA_DEMOSTRACION.md) | Guion de la demo y contingencias |
| [`docs/demo/CUENTAS_DE_PRUEBA.md`](docs/demo/CUENTAS_DE_PRUEBA.md) | Credenciales y portales |
| [`docs/demo/CONTENIDO_PUBLICO.md`](docs/demo/CONTENIDO_PUBLICO.md) | Portafolio, talleres e imágenes |
| [`docs/demo/VARIABLES_ENTORNO.md`](docs/demo/VARIABLES_ENTORNO.md) | Variables y despliegue |
| [`docs/presentacion/`](docs/presentacion/) | Entregables finales (PDF/PPTX/DOCX) |
| [`docs/sustentacion/`](docs/sustentacion/) | Diagramas, fuentes y evidencias |
| [`docs/audit/`](docs/audit/) | Auditoría técnica de referencia |

---

## Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `docker compose` no arranca la app | PostgreSQL tarda en estar sano; revisar `docker compose logs db`. El `healthcheck` bloquea hasta que responde |
| No aparecen datos demo | `CITI_SEED_ON_START=0` o el seed falló: `docker compose exec web python manage.py seed_demo_data` |
| `/media/` da 404 en el contenedor | Falta `CITI_SERVE_MEDIA=1` (ya viene en `docker-compose.yml`; es solo demo) |
| Quiero empezar de cero | `docker compose down -v && docker compose up --build` |
| Error de línea `\r` al ejecutar `entrypoint.sh` | `.gitattributes` fuerza `eol=lf` para `*.sh`; si se editó en Windows, volver a clonar o convertir a LF |
| Login rechaza la cuenta | El portal elegido no coincide con el rol de la cuenta |
| El navegador no abre la plataforma | Ejecuta `iniciar_citi.bat` o abre manualmente <http://localhost:8000> |

---

## Aviso

Este paquete es una **demostración académica**. Las cuentas, la contraseña
compartida, `CITI_SERVE_MEDIA` y la clave de Django por defecto son válidas solo
para local. Para un despliegue real: `IS_PRODUCTION=True` (o
`DJANGO_ENV=produccion`), `SECRET_KEY` o `DJANGO_SECRET_KEY`, hosts propios,
HTTPS, y servir estáticos y medios con Nginx u otro servidor
(ver `docs/demo/VARIABLES_ENTORNO.md`).

---

## Despliegue en Render

El repositorio incluye `render.yaml`, un Blueprint con **plan free** para evitar
cobros:

- `citi-db`: PostgreSQL gratuito.
- `citi-portal`: servicio web Docker gratuito, con health check en
  `/cuenta/login/`.
- `DATABASE_URL` se inyecta desde `citi-db`; `RENDER_EXTERNAL_HOSTNAME` lo
  agrega Render automáticamente a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
- `IS_PRODUCTION=True` activa HTTPS, cookies seguras, HSTS y el proxy
  `X-Forwarded-Proto`; `SECRET_KEY` se genera automáticamente.

Pasos:

1. Sube el repositorio a GitHub.
2. En Render, entra a **New → Blueprint** y conecta el repositorio.
3. Render detecta `render.yaml` y crea `citi-db` y `citi-portal` en plan free.
4. Espera el build y el health check; abre la URL
   `https://citi-portal.onrender.com`.

> El plan free de Render puede tardar en despertar tras inactividad. El seed de
> demostración se omite automáticamente cuando `IS_PRODUCTION=True`; la base de
> producción solo recibe migraciones y datos reales.
