# Contenido público de demostración (Fase 05)

Añadido por `seed_public_content()` en `backend/accounts/demo_public.py`,
invocado desde `seed_all()` y por tanto disponible en `seed_demo` y
`seed_demo_data`. Claves de idempotencia: `slug` en portafolio/talleres y
`codigo` en solicitudes.

## Portafolio (8 proyectos publicados: 4 Civil + 4 Sistemas/IA/Impacto)

| Slug | Línea | Organización | Destacado |
|---|---|---|---|
| `trazabilidad-casos-fundacion` | Sistemas | Fundación Horizonte | Sí |
| `diagnostico-seguridad-pyme` | Sistemas | Comercializadora del Tolima | — |
| `estudio-suelos-vivienda-rural` | Civil | Constructora Andina | Sí |
| `optimizacion-red-agua` | Civil | JAC El Espinal | — |
| `asistente-ia-atencion` | Innovación / IA | Centro de Servicios Regional | Sí |
| `alfabetizacion-digital-mayores` | Impacto Social | Club de Pensionados del Tolima | — |
| `patologia-estructural-sede-comunitaria` | Civil | JAC El Espinal | Sí |
| `topografia-drenaje-vial-rural` | Civil | Juntas Veredales del Tolima | — |

> El proyecto `validacion-tecnica-emprendimiento-juvenil` de una iteración
> anterior se **despublica** (no se borra) para mantener el set 4+4. El caso de
> emprendimiento juvenil sigue visible en la portada y en los talleres.

Las 8 tarjetas usan `imagen_static` con una **foto única por proyecto** en
`backend/static/images/landing/`. El seed migra automáticamente las rutas
antiguas (`area-civil.jpg`, `banner-campo.jpg`, etc.) sin sobrescribir imágenes
personalizadas desde `/admin/`. Créditos y licencias:
[`CREDITOS_IMAGENES.md`](CREDITOS_IMAGENES.md).

## Talleres (6 activos: 3 Civil + 3 Sistemas)

Cada taller incluye **3 puntos clave del temario** en `puntos_clave` (JSON) y
un campo `area` (`sistemas`/`civil`) que se muestra en la tarjeta pública. Sus
6 imágenes también son únicas (ver `CREDITOS_IMAGENES.md`).

| Slug | Área | Público | Modalidad | Nivel |
|---|---|---|---|---|
| `ia-aplicada-fundaciones-ong` | Sistemas | Fundaciones y ONG | Híbrida | Desde cero |
| `autoconstruccion-segura-vivienda` | Civil | Pymes y comunidad | Presencial | Desde cero |
| `herramientas-digitales-emprendedores` | Sistemas | Emprendimientos juveniles | Presencial | Desde cero |
| `cosecha-aguas-lluvias-saneamiento` | Civil | Fundaciones / ONG | Presencial | Desde cero |
| `alfabetizacion-digital-adultos-mayores` | Sistemas | Pensionados y adultos mayores | Presencial | Desde cero |
| `mantenimiento-preventivo-hogar` | Civil | Pensionados y adultos mayores | Presencial | Desde cero |

> `gestion-tecnologica-pymes` de una iteración anterior se **desactiva**
> (no se borra) para mantener el set 3+3.

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
