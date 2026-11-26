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

## Arranque rápido con Docker (recomendado para la exposición)

Requisito: Docker Desktop instalado y en ejecución.

```bash
docker compose up --build
```

Luego abrir <http://localhost:8000>.

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
docker compose up --build           # reconstruir tras cambiar código
```

Variables opcionales: copiar `.env.docker.example` a `.env` (puerto,
contraseña demo, workers). El puerto también se cambia con `PORT=8080`.

---

## Credenciales de demostración

Contraseña única: **`CITIPass2026*`** (configurable con `CITI_DEMO_PASSWORD`).

| Rol | Correo | Acceso |
|---|---|---|
| Director CITI | `director@citi.ucc.edu.co` | `/cuenta/login/?rol=director` |
| Coordinador Sistemas | `coordinador@citi.ucc.edu.co` | `/cuenta/login/?rol=coordinador` |
| Coordinador Civil | `coordinador.civil@citi.ucc.edu.co` | `/cuenta/login/?rol=coordinador` |
| Docente Sistemas | `docente@citi.ucc.edu.co` | `/cuenta/login/?rol=docente` |
| Docente Civil | `docente.civil@citi.ucc.edu.co` | `/cuenta/login/?rol=docente` |
| Estudiante tutora | `estudiante@citi.ucc.edu.co` | `/cuenta/login/?rol=estudiante` |
| Estudiante tutor Civil | `estudiante.civil@citi.ucc.edu.co` | `/cuenta/login/?rol=estudiante` |
| Cliente / Empresa | `cliente@empresatolima.co` | `/cuenta/login/?rol=cliente` |
| Fundación (cliente) | `fundacion@citi.ucc.edu.co` | `/cuenta/login/?rol=cliente` |
| Emprendimiento (cliente) | `emprendimiento@citi.ucc.edu.co` | `/cuenta/login/?rol=cliente` |
| Pyme (cliente) | `pyme@citi.ucc.edu.co` | `/cuenta/login/?rol=cliente` |

El login es **por rol**: si la cuenta no coincide con el portal elegido, el
sistema lo indica. Detalle completo en
[`docs/demo/CUENTAS_DE_PRUEBA.md`](docs/demo/CUENTAS_DE_PRUEBA.md).

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
> `.venv/` tiene Django 6.x y `backend/venv/` no tiene Django.

### Pruebas

```powershell
cd backend
..\venv\Scripts\python.exe manage.py check
..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\venv\Scripts\python.exe manage.py test
```

160 pruebas: matriz de roles, reservas, estados, IDOR, registro, seed,
trazabilidad, indicadores, seguimiento, interacciones, aprobaciones y la zona
pública + triage (`backend/portal/test_public.py`).

---

## Estructura

```text
backend/            Proyecto Django real (config + accounts + scheduling + portal)
  accounts/         Usuarios, empresas, perfiles y seed de demostración
  scheduling/       Franjas, citas, eventos, interacciones y solicitudes públicas
  portal/           Vistas públicas, paneles privados, triage e indicadores
  templates/        Plantillas (público, paneles, partials)
  static/           CSS/JS/imágenes/videos
assets/             Assets institucionales adicionales (STATICFILES_DIRS)
docs/demo/          Credenciales, datos y guion de demostración
Dockerfile · docker-compose.yml · entrypoint.sh
```

Los directorios `accounts/`, `portal/`, `scheduling/`, `app/`, `dashboards/`,
`plantillas/` y los `*.html` de la raíz son **prototipo estático**: no los usa
Django.

---

## Videos de la portada

La portada usa `<video>` con `poster` y una imagen de respaldo. Los MP4 finales
(`backend/static/videos/hero-citi.mp4`, `progreso-ingenieria.mp4`,
`resultados-impacto.mp4`) son contenido reemplazable: mientras no existan, se ve
el poster y la imagen de respaldo. Especificaciones en
[`backend/static/videos/README.md`](backend/static/videos/README.md).

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

---

## Aviso

Este paquete es una **demostración académica**. Las cuentas, la contraseña
compartida, `CITI_SERVE_MEDIA` y la clave de Django por defecto son válidas solo
para local. Para un despliegue real: `DJANGO_ENV=produccion`,
`DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS` propios, HTTPS, y servir estáticos y
medios con Nginx u otro servidor (ver `docs/demo/VARIABLES_ENTORNO.md`).
