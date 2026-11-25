# Contenido público de demostración (Fase 05)

Añadido por `seed_public_content()` en `backend/accounts/demo_public.py`,
invocado desde `seed_all()` y por tanto disponible en `seed_demo` y
`seed_demo_data`. Claves de idempotencia: `slug` en portafolio/talleres y
`codigo` en solicitudes.

## Portafolio (6 proyectos publicados)

| Slug | Línea | Organización | Destacado |
|---|---|---|---|
| `trazabilidad-casos-fundacion` | Sistemas | Fundación Horizonte | Sí |
| `diagnostico-seguridad-pyme` | Sistemas | Comercializadora del Tolima | — |
| `estudio-suelos-vivienda-rural` | Civil | Constructora Andina | Sí |
| `optimizacion-red-agua` | Civil | JAC El Espinal | — |
| `asistente-ia-atencion` | Innovación / IA | Centro de Servicios Regional | Sí |
| `alfabetizacion-digital-mayores` | Impacto Social | Club de Pensionados del Tolima | — |

Las tarjetas usan `imagen_static` (assets de `backend/static/images/landing/`)
para que en Docker se vean sin depender del volumen de media.

## Talleres (4 activos)

| Slug | Público | Modalidad | Nivel |
|---|---|---|---|
| `ia-aplicada-fundaciones-ong` | Fundaciones y ONG | Híbrida | Básico |
| `herramientas-digitales-emprendedores` | Emprendedores jóvenes | Presencial | Básico |
| `alfabetizacion-digital-adultos-mayores` | Adultos mayores | Presencial | Básico |
| `gestion-tecnologica-pymes` | Pymes | Virtual | Intermedio |

## Solicitudes públicas (intake)

| Código | Solicitante | Necesidad | Estado | Para demostrar |
|---|---|---|---|---|
| `DEMO-SOL-001` | Fundación | Capacitación (taller de IA) | `recibida` | Aprobar un taller sin crear cita |
| `DEMO-SOL-002` | Emprendimiento | Asesoría (sin NIT) | `en_revision` | Cliente nuevo con NIT placeholder al convertir |
| `DEMO-SOL-003` | Empresa | Consultoría profesional | `aprobada` | Conversión + asignación de docente |
| `DEMO-SOL-004` | Comunidad | Capacitación (adultos mayores) | `aprobada` | Taller aprobado, sin cita |

`DEMO-SOL-003` es el caso más completo: ya está clasificada en Sistemas /
Bases de Datos y lista para elegir franja, docente y tutor.

## Comandos equivalentes

| Comando | Uso |
|---|---|
| `manage.py seed_demo` | Seed histórico completo + contenido público |
| `manage.py seed_demo_data` | Igual, con resumen del contenido público. Es el que ejecuta Docker |
| `manage.py seed_demo_data --solo-usuarios` | Solo cuentas demo (sin contenido ni citas) |

Ambos están bloqueados con `DJANGO_ENV=produccion`.
