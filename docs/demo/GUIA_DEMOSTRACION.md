# Guía de demostración — CITI (recorrido por los cinco roles)

Duración estimada: 12–15 min. Toda la interacción ocurre en el navegador, sin
tocar el admin, salvo donde se indica.

## 0. Preparación (1 vez, minutos antes)

```powershell
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py seed_demo_data  # idempotente: contenido público + citas + franjas
..\venv\Scripts\python.exe manage.py runserver       # http://127.0.0.1:8000/
```

Abrir la landing (`/`) y verificar que el login ofrece los 5 portales.
Credenciales: `CUENTAS_DE_PRUEBA.md` (contraseña única).

> La sesión es local: si se reinició el servidor tras cambiar `SECRET_KEY`,
> los navegadores con cookies viejas piden login de nuevo (esperado).

## 0.b Recorrido corto de 6–8 minutos (zona pública → triage → cita)

Guion recomendado para la exposición. Cada paso tiene un objetivo verificable.

| Min | Pantalla | Qué mostrar | Qué debe verse |
|---|---|---|---|
| 0:00–1:30 | `/` (portada) | Hero con video/poster, copy de posicionamiento, franja de cifras | "Transformamos desafíos reales…", CTAs de diagnóstico y portafolio, sin lenguaje asistencialista |
| 1:30–2:30 | `#modalidades` | Las dos líneas de atención | Línea 1 (proyección social) y Línea 2 (consultoría profesional) con ejemplos concretos |
| 2:30–3:30 | `/portafolio/` | Filtros por línea y detalle de un caso | Proyectos sembrados; filtro Civil deja solo casos de Civil |
| 3:30–4:30 | `/talleres/` → "Solicitar este taller" | Catálogo y formulario público | 4 talleres; el formulario pide entidad, público objetivo y fecha tentativa |
| 4:30–5:30 | `/diagnostico/` | Enviar una solicitud en vivo | Radicado `SOL-XXXXXXXX` en la pantalla de gracias |
| 5:30–6:30 | `/panel/solicitudes/` (Director) | Bandeja de intake con la solicitud recién creada | Contador en el sidebar, badge de línea y estado "Recibida" |
| 6:30–7:30 | Detalle → Aprobar → Convertir | Clasificar y crear la cita con docente | La solicitud pasa a "Convertida" y abre `CITI-000xx` |
| 7:30–8:00 | Cita abierta | Historial de eventos | Evento "Solicitud creada" con el código del radicado en la metadata |

Atajos para no improvisar:

- Si el tiempo aprieta, usar `DEMO-SOL-003` (ya aprobada): abrir su detalle y
  saltar directo a **Convertir y asignar**.
- Para mostrar que un taller no genera cita, usar `DEMO-SOL-001` y aprobarlo:
  el mensaje confirma que se agenda directamente con la organización.
- La cuenta `emprendimiento@citi.ucc.edu.co` no tiene NIT: al convertir
  `DEMO-SOL-002` se crea el cliente con NIT `PENDIENTE-…`, demostrando la
  salvaguarda de validación.

## 1. Cliente / Empresa — `cliente@empresatolima.co`

1. Login portal **cliente** → *Agenda de citas*.
2. **Calendario**: franjas coloreadas por área; "Disponible (n)" vs
   "Ocupado"; filtro de área arriba a la izquierda.
3. **Mis citas recientes**: muestra el set (Pendiente/Asignada/En
   proceso/Finalizada) — resaltar los badges de estado.
4. **Reserva en vivo** (nucleo de la demo):
   - Clic en una franja *Disponible (2)* de un día futuro.
   - El panel derecho fija el área de la franja y cargó sus
     subespecialidades. Elegir tipo de servicio + subespecialidad + asunto
     ("Modernización de infraestructura de datos de la empresa").
   - (Opcional) adjuntar un PDF/docx (términos de referencia).
   - *Confirmar solicitud* → alerta verde → recarga → aparece la cita como
     **Solicitada**.
5. **Feedback**: abrir detalle de la cita "Ciberseguridad – Finalizada":
   línea de tiempo del flujo; si aún no calificada, botón *Calificar*
   (1–5 + comentario). La calificación persiste y aparece en "últimos
   comentarios".

## 2. Coordinador de área — `coordinador@citi.ucc.edu.co`

1. Login portal **coordinador** → KPIs (nuevas/en proceso/finalizadas)
   **solo de Sistemas** (mostrar que el área Civil no aparece).
2. Bandeja: la solicitud "web" sembrada + la recién creada por el cliente.
3. Clic sobre la fila → **modal de detalle** (sin salir del panel).
4. *Asignar*: elegir docente (solo docentes del área) y, si aplica, tutor
   (solo estudiantes que cumplen 8°/130/4.0 — sin ellos, no aparecen).
5. Confirmar → cita pasa a **Asignada**; KPI "nuevas" baja.
6. Demo de aislamiento: abrir `/panel/docente/` con esta sesión → el sistema
   **redirige al portal propio** (corregido en B-1: antes daba error 500).

## 3. Docente asesor — `docente@citi.ucc.edu.co`

1. Login **docente**: casos asignados del área.
2. Abrir el caso "Bases de Datos": *Acciones rápidas*
   → *Marcar en proceso* (transición solicitada por el cliente).
3. *Gestión del caso*: agregar nota de avance (bitácora visible para el
   tutor) + resumen de cierre → *Marcar finalizada*.
4. *Descargar acta* (HTML imprimible; botón "Imprimir/Guardar como PDF").
5. En caso con tutor, la bitácora alimenta el historial.

## 4. Estudiante tutor — `estudiante@citi.ucc.edu.co`

1. Login **estudiante**: banner "Habilitado como Estudiante Consultor"
   (perfil real 9°/150/4,5 — demostrar el filtro académico).
2. Bandeja "apoyo técnico": caso "Redes".
3. *Bitácora*: registrar avance → nota aparece en el caso del docente.
4. (Opcional, explica el filtro): el coordinador solo puede asignar a este
   estudiante porque **cumple**; un estudiante sin perfil no aparece.
   No se fuerza la condición de tutor manualmente: se cumple por semestre,
   créditos y promedio (`PerfilEstudiante`).

## 5. Director CITI — `director@citi.ucc.edu.co`

1. Login **director**: panel general (usuarios, franjas activas, citas
   reservadas) — cifras coherentes con lo operado en vivo.
2. Botón *Ir al administrador Django* → mostrar (sin edits): Usuarios,
   Empresas, Franjas, Citas, Bitácora. Login mismo correo/contraseña
   (es `is_staff`).
3. Volver al panel; cerrar sesión (ojo: cerrar sesión con POST del sidebar).

## 6. Cierre recomendado

1. Cliente → "Mis citas recientes": la reserva de la demo ya aparece en la
   bandeja como Asignada/En proceso/Finalizada según el recorrido.
2. Mostrar `manage.py test` (141 pruebas, 0 fallos) como red de seguridad:
   ```powershell
   ..\venv\Scripts\python.exe manage.py test
   ```

## Intervenciones manuales necesarias (documentadas)

| Paso | Por qué |
|---|---|
| Ejecutar `seed_demo_data` antes de presentar | El seed es explícito por seguridad (B-4); mantiene frescura, reubica citas y crea el contenido público |
| El "Docente" finaliza con *Marcar finalizada* y completa resumen en el formulario de gestión | El cierre exige resumen; la UI lo recuerda con aviso |
| Crear **cuentas internas nuevas** solo desde `/admin/` | El registro público solo crea clientes (diseño) |

## Guion de contingencia (si algo falla en vivo)

- ¿Calendario sin franjas? → reejecutar `seed_demo` (reubica/crea).
- ¿No aparece el tutor al asignar? → verificar `estudiante@citi.ucc.edu.co`
  (el seed lo promueve); o actualizar su perfil en admin.
- ¿Sesión "corrupta" tras reiniciar servidor? → cerrar sesión y volver a
  entrar (cookies firmadas con clave anterior).
