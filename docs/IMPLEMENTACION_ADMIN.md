# Implementación del área de administración — Fase 03 (Módulo B)

## Principio rector

Dos interfaces deliberadamente distintas:

- **Django Admin** (`/admin/`) = herramienta administrativa de registros (CRUD, filtros, acciones).
- **Panel del Director** (`/panel/director/`) + **Trazabilidad** (`/panel/trazabilidad/`) = interfaces de consulta ejecutiva del CITI.

El admin NO es el dashboard del director, ni el dashboard sustituye al admin.

## Personalización del Django Admin (100 % nativo, sin librerías externas)

*Justificación: `django-admin-interface`/`simpleui` no aportan sobre las capacidades nativas de Django 5.2 (AdminSite con `site_header`, templates `base_site`, CSS propio, fieldsets, inlines, acciones) y añadirían superficie de compatibilidad y dependencias a auditar. Se usó solo API pública de Django.*

| Pieza | Archivo | Contenido |
|---|---|---|
| Marca institucional | `portal/apps.py::PortalConfig.ready` | `site_header='Administración CITI — UCC'`, `site_title`, `index_title='Gestión de registros del consultorio'` |
| Plantilla raíz | `templates/admin/base_site.html` | logo UCC + marca, usuario conectado, enlaces "Ver portal público / Cambiar contraseña / Cerrar sesión" |
| CSS | `static/css/admin-citi.css` | paleta UCC (azul fundadores, verde solidario), cabecera, módulos, botones, detalle responsive; solo presentación |
| Agrupación | `accounts/apps.py`, `scheduling/apps.py` (`verbose_name`) | secciones ordenadas: **Identidad: usuarios, empresas y perfiles** → **Agenda, solicitudes y trazabilidad** |

### Entidades organizadas (mapa de la especificación)

| Concepto | Registro admin | Dónde |
|---|---|---|
| 1. Usuarios | `CustomUser` con badges de rol por color, filtros por rol/tipo/área/activo, búsqueda (incl. empresa), fieldsets (datos / rol CITI / permisos plegables / fechas colapsados) | accounts |
| 2. Empresas y clientes | `Empresa` con nº de contactos clientes (`prefetch_related`) | accounts |
| 3-4. Solicitudes / citas y franjas | `CitaAsesoria` (código `CITI-00001`, empresa, área, estado, docente, valoración, `date_hierarchy` por creación, filtros cruzados, `raw_id` para FKs) y `FranjaHoraria` (cupos ocupados/disponibles calculados, boolean "Futura", fecha jeraquy) | scheduling |
| 5-6. Áreas y especialidades | se expresan en `FranjaHoraria.area` (filtro) y `CitaAsesoria.subespecialidad` (filtro de catálogo); no son tablas separadas — se documenta aquí porque el catálogo vive en `subespecialidades.py` | scheduling |
| 7. Asignaciones | visibles como FKs dentro de la cita (`raw_id` + inlines), con validación de área en `CitaAsesoria.clean` | scheduling |
| 8. Historial de actividad | **`CitaEvento` (solo lectura)** + inline "Historial de eventos" en cada cita + inline de bitácoras | scheduling |

### Reglas de negocio respetadas desde el admin

- `CitaAsesoriaAdminForm`: no permite finalizar sin `resumen_cierre` (mismo criterio que el portal).
- `save_model`: un cambio de estado guardado desde admin pasa por `cambio_estado()` → misma validación `full_clean`, mismas marcas `asignada_en`/`cerrada_en` y **su evento en el historial** (traza "desde el panel administrativo").
- Acciones seguras y auditadas: "Cancelar solicitudes seleccionadas (registra evento)" (omite finalizadas/canceladas con aviso) y "Marcar como revisadas".
- `PerfilEstudianteInline.autorizado_como_tutor` permanece **solo lectura** (lo computa el modelo).
- Campos de auditoría readonly en citas: `creada_en`, `asignada_en`, `cerrada_en`, `actualizada_en`.
- `CitaEventoAdmin`: sin add/cambio/borrado; inline en cita igualmente readonly.

## Panel ejecutivo del Director (nuevo)

Ruta `/panel/director/` (`role_required(DIRECTOR)`; sin acceso cruzado). Contenido verificado en navegador:

- Encabezado: bienvenida con nombre, fecha localizada, descripción del panel y **chips de periodo** (7/30/90 días, año actual, rango personalizado, histórico).
- 9 tarjetas: los 6 KPIs del ciclo + franjas activas futuras (ahora sí filtradas por fecha) + usuarios + tasa de finalización con fracción visible (2/11 → 18,2 %).
- Gráficos CSS puros (sin dependencias externas): solicitudes por estado, demanda por área (nota honesta sobre MIXTO), evolución 6 meses recibidas vs finalizadas con leyenda y escala compartida.
- Tabla "Actividad reciente" (código, empresa, área, servicio, fecha, responsable, estado) con apertura del detalle modal existente + enlace al módulo de trazabilidad completo.
- Todo calculado con agregaciones ORM sobre la BD (`kpis_base`, `por_estado`, `por_area`, `evolucion_mensual` en `portal/indicadores.py`).

## Permisos probados

- Director demo del seed con permisos de dominio (accounts+scheduling), **sin** `is_superuser`.
- Los demás roles no entran a `/panel/trazabilidad/` (regresión en `IndicadoresTests.test_roles_sin_acceso_a_trazabilidad`) y el coordinador accede con aislamiento de área forzado en servidor.
- La matriz rol×portal de 42+ pruebas anteriores sigue verde.
