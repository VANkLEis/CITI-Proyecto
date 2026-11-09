# Guía del Director CITI — nuevo panel operativo

Para quien presenta/demuestra el rol de Dirección: qué puede hacer, dónde está
cada cosa y qué significan los números.

## Acceso

- Portal: `/cuenta/login/?rol=director` → `director@citi.ucc.edu.co` (ver
  `docs/demo/CUENTAS_DE_PRUEBA.md`).
- El director demo además es `is_staff` con permisos **limitados al dominio
  CITI** (no es superusuario): entra a `/admin/` con la misma cuenta.

## 1. Panel ejecutivo (`/panel/director/`)

Interfaz de consulta, NO de edición (editar registros = Django Admin).

| Bloque | Qué muestra | De dónde sale |
|---|---|---|
| Encabezado | bienvenida, fecha, descripción | usuario + reloj Bogotá |
| Chips de periodo | 7/30/90 días, año actual, rango personalizado, histórico | parámetro `periodo` en URL; al elegir "Rango personalizado" aparecen `desde/hasta` |
| 6 KPIs de ciclo | recibidas, pendientes, asignadas, en proceso, finalizadas, canceladas | `CitaAsesoria` agregado (`Count` con `Q`), filtrado por periodo/rol |
| 3 tarjetas de contexto | franjas activas FUTURAS (las vencidas no cuentan), usuarios, tasa de finalización con fracción visible (ej. 25,0 % (3/12)) | `FranjaHoraria`/`CustomUser`/cálculo propio |
| Gráficos | por estado, demanda por área, evolución 6 meses (recibidas vs finalizadas) | mismo queryset filtrado; CSS puro (funcionan sin red) |
| Actividad reciente | últimas 8 solicitudes (código, empresa, área, servicio, fecha, responsable, estado) | `-actualizada_en`; "Ver" abre el detalle con historial |

Nota honesta del gráfico de áreas: MIXTO aparece excluido con aviso (su flujo
operativo no está implementado — hallazgo I-5 de la auditoría, en backlog).

## 2. Trazabilidad e indicadores (`/panel/trazabilidad/`)

Enlace en la barra lateral. Es la vista analítica completa:

- Filtros combinables: periodo/fechas + área + estado + tipo de servicio +
  responsable (solo los que aparecen en el alcance filtrado).
- Indicadores de resultado con fórmulas a la vista:
  - Atendidas = `finalizadas` (nunca se confunden con asignadas).
  - Tasa de finalización = finalizadas ÷ recibidas (canceladas cuentan como
    recibidas, no como atendidas).
  - Tiempo medio hasta asignación y de resolución (en horas, con `n`; si
    `n=0`: **"No disponible"**, nunca un número inventado).
- Evolución, servicios más solicitados y tabla de resultados (código, área,
  empresa, servicio, responsable, fechas, resolución, estado) hasta 100.
- **Exportar CSV** con los filtros activos aplicados; el archivo incluye
  período consultado, fecha/hora de generación y quién lo produjo; no incluye
  correos personales.

## 3. Historial por solicitud

En cualquier detalle (modal o página del caso) hay una sección "Historial de
la solicitud" con eventos reales: quién, qué hizo, sobre qué solicitud,
cuándo y estado resultante. Las citas anteriores a esta versión muestran el
aviso de que el seguimiento no estaba habilitado al crearse (no se inventa
historia). Las citas del seed de demostración llevan eventos etiquetados
"(simulación seed_demo)" y el caso 15 (validación en vivo) tiene línea de
tiempo 100 % genuína.

## 4. Django Admin (`/admin/`)

- Marca institucional UCC; dos secciones: **Identidad: usuarios, empresas y
  perfiles** y **Agenda, solicitudes y trazabilidad**.
- Citas: fieldsets (Solicitud / Documentación / Responsables / Estado y cierre
  / Marcas de tiempo), historial y bitácoras como inlines de solo lectura,
  cancelación masiva con registro de evento.
- Historial de eventos: solo lectura (sin añadir/editar/borrar desde UI).
- Borrar solicitudes: restringido a superusuario (protege la trazabilidad).
- Cambios de estado desde admin generan su evento (mismo canal que el portal).

## 5. Guion corto para la presentación (5 min)

1. Director: KPIs + cambiar a "Últimos 30 días" → reactividad de filtros.
2. Trazabilidad: filtro área Civil + estado Solicitada → tabla y CSV.
3. Descargar CSV en vivo (muestra período y generación en el archivo).
4. Admin: abrir caso con historial → mostrar eventos + botón bloqueado de borrado.
5. Volver al panel tras una reserva en vivo del cliente → tasa de finalización
   y evolución cambian con el nuevo caso.
