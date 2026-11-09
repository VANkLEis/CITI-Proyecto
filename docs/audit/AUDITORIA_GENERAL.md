# AUDITORÍA GENERAL — CITI (UCC Campus Ibagué–El Espinal)

**Fecha:** 8 de noviembre de 2026
**Alcance:** repositorio completo (`backend/` Django + prototipo estático raíz), base de datos local de desarrollo, ejecución en servidor de desarrollo y navegador real.
**Método:** revisión de código estática + 34 pruebas funcionales automatizadas ejecutadas contra una **base de datos de pruebas en memoria** (test runner de Django; `db.sqlite3` nunca fue modificado) + verificación en vivo con `runserver` y navegador (Playwright).
**Documentos hijos:** `AUDITORIA_SEGURIDAD.md`, `AUDITORIA_FUNCIONAL.md`, `AUDITORIA_ARQUITECTURA.md`, `MATRIZ_DE_PRUEBAS.md`, `PLAN_CORRECCIONES.md`.

---

## 1. Resumen ejecutivo

El sistema **existe y funciona**: no es un mockup. Los cinco portales de rol, la autenticación diferenciada, el ciclo solicitud → asignación → gestión → cierre → calificación, el aislamiento por área de coordinadores y el filtro académico de tutores están implementados en backend y fueron verificados con datos reales de prueba. `manage.py check` pasa, las migraciones están aplicadas y sincronizadas con los modelos, y no hay cambios de esquema pendientes.

Sin embargo, la auditoría encontró **3 fallos críticos** y varios altos que hoy harían fracasar una demostración o comprometer un despliegue:

| # | Hallazgo | Gravedad | Estado |
|---|----------|----------|--------|
| SEG-01 | `role_required` usa `redirect` sin importarlo: **cualquier acceso de un rol a URL de otro rol produce HTTP 500** (NameError). Confirmado en vivo y reproducible; el bug está en el commit publicado en GitHub (`86b15ac`). | CRÍTICO | Confirmado |
| SEG-02 | Credenciales de demostración fijas y **hardcoded en el repositorio público**, y las cuentas se **auto-crean solas** al visitar `/` o `/cuenta/login/` (incluso anónimos). | CRÍTICO (despliegue) | Confirmado |
| SEG-03 | `DEBUG=1` por defecto y `SECRET_KEY` de respaldo pública; sin HTTPS/HSTS/cookies seguras. En cualquier despliegue real sin variables de entorno: exposición de código fuente, settings y forja de sesiones. | CRÍTICO (condicional a despliegue) | Confirmado por código |
| SEG-04 | Subida de archivos sin validación servidor (tipo, tamaño); descarga `/media/` **sin autenticación ni chequeo de rol** en DEBUG. | ALTO | Confirmado por código; efecto de auth no reproducible fuera de DEBUG |
| FUN-05 | Sin transacciones ni bloqueos en la reserva: **overbooking (sobreasignación de cupo)** posible bajo peticiones concurrentes. | ALTO | Riesgo confirmado por código; no reproducido bajo carga |
| FUN-06 | Máquina de estados no imposta: el docente puede saltar, retroceder y reabrir estados, y reasignar el estudiante (campo de coordinación). | ALTO | Confirmado (T16, T17, T20) |

Y un **bloqueo de demostración por datos** (no por código): las 9 franjas horarias activas de `db.sqlite3` están todas en el pasado (última: 27/10/2026). El autoseed de franjas solo actúa si no existe **ninguna** franja activa, así que el calendario del cliente queda **vacío** y el flujo completo de reserva **no es demoable hoy** (verificado en navegador: 0 eventos en la semana actual).

## 2. ¿Qué preguntas clave responde la auditoría?

**¿Funciona realmente?** Sí en lo esencial: el backend resuelve login por rol, reserva, asignación, gestión, acta, bitácora y feedback con permisos de servidor. No es humo. Pero el cruce de roles revienta (SEG-01) y la reserva no es demoable con los datos actuales (FUN-12).

**¿Qué está solo simulado o es incompleto?**
- La cancelación existe en el modelo y en la UI de estado, pero **no existe ninguna acción que cancele** desde el portal (FUN-07).
- La recuperación de contraseña **no existe** (FUN-08).
- El área MIXTO es un elefante blanco: no tiene subespecialidades (no es reservable) y ningún coordinador puede asignarla (FUN-09).
- El KPI "Horas / créditos acumulados" del estudiante es una **fórmula inventada** (`casos×2 + créditos//10`), presentada como métrica real (FUN-11).
- El acta se anuncia "PDF" pero es HTML imprimible sin firma digital (UX-20).
- Los módulos del prototipo estático (talleres, correspondencia, bolsa de empleo, programa radial, convenios, prácticas) **no tienen implementación Django alguna** (ARQ-16).
- `docs/erd-mermaid.md` describe un esquema (Solicitud/Informe/Firma/…) que **no corresponde** a los modelos reales.

**¿Qué vulnerabilidades existen?** Ver `AUDITORIA_SEGURIDAD.md`: críticas SEG-01 (crash de autorización), SEG-02 (credenciales demo públicas/sembradas por GET) y SEG-03 (defaults de producción inseguros); altas SEG-04 (uploads/media sin control) y SEG-13 (contraseñas débiles en registro); medias SEG-14 (enumeración de cuentas) y SEG-15 (fuga de errores internos); bajas SEG-21/22/23. Los controles clásicos de Django (CSRF, escape de plantillas, inyección ORM, IDOR por objeto) **sí están presentes y funcionaron** en todas las pruebas.

**¿Qué puede romper una demostración?**
1. Navegar (o que un asistente escriba) cualquier URL de otro rol → pantalla de error 500 con traceback público (SEG-01).
2. Calendario de cliente vacío → no se puede reservar (FUN-12, datos).
3. El cliente demo sembrado `cliente@empresatolima.co` **no tiene citas**: las 4 citas existentes pertenecen a otra cuenta cliente (`carlos.ramirez@empresatolima.co`), y el portal del docente muestra la empresa "Soluciones Tecnológicas Tolima S.A.S." → narrativa inconsistente (FUN-12).
4. Los estudiantes demo son `consultor` con perfil académico en 0 → **ningún estudiante aparece como tutor elegible** en el formulario de asignación (requisitos 8°/130/4.0) (FUN-12).
5. El rol Director no se siembra: en un clon limpio no existe cuenta director (existe solo localmente un usuario personal con `is_staff`).

## 3. Estado general del proyecto

| Dimensión | Estado | Nota |
|---|---|---|
| Arquitectura | ⚠️ Funcional pero con capas muertas | Django real + prototipo estático conviviendo; duplicación raíz/backend |
| Seguridad | ❌ Inseguro por defecto | Los 3 críticos de arriba; buenos controles base de Django |
| Funcionalidad núcleo | ✅ 80 % verificado | Ciclo de cita completo funciona salvo cancelación/recuperación |
| Concurrency/integridad | ⚠️ Riesgo | Sin transacciones; constraint parcial sí protege doble cita mismo cliente |
| Base de datos | ✅ Migraciones consistentes | `makemigrations --check`: sin cambios; FK/índices correctos; datos de demo desalineados |
| Pruebas | ❌ Inexistentes | 0 tests; la matriz de esta auditoría es la primera cobertura |
| UX/UI | ⚠️ Aceptable en escritorio | Sin navegación lateral real; móvil pierde logout; dependencias CDN |

## 4. Auditoría visual y UX (preliminar — sin rediseño)

| Área | Estado observado | Problemas detectados |
|---|---|---|
| Landing | Renderiza bien en escritorio (verificada en navegador; redesign sin commitear aún) | Imágenes pesadas (organigrama 1.2 MB, mockup 2.5 MB) cargadas inline; dependencias externas (Google Fonts) que en demo sin red dejan tipografía fallback |
| Login / Registro | Correctos en escritorio; el panel de roles es funcional y el botón se habilita al elegir portal | Sin enlace "¿olvidó su contraseña?" (porque la función no existe, FUN-08); en pantallas ≤900px las columnas apilan bien |
| Dashboards | KPIs y tablas legibles; modal de detalle funcional | **Barra lateral de navegación completamente vacía** (el bloque `sidebar_nav` no se rellena en ninguna plantilla) — verificado en vivo: el `<nav>` no tiene enlaces; no hay forma de volver al inicio salvo el logo (que tampoco enlaza en dashboards) |
| Móvil | Breakpoints existen en CSS (900/640/600) | Al ocultarse la barra lateral con `translateX(-100%)` **desaparecen también el botón de cerrar sesión y toda la navegación**, sin menú hamburguesa alternativo; las tablas de datos no tienen scroll horizontal contenedor |
| Formularios | Validaciones y errores visibles, estilo consistente | El acta se anuncia "Descargar acta (PDF/imprimir)" pero es HTML en pestaña nueva (F-17); en el formulario de reserva el tipo de servicio y la subespecialidad no guardan relación visible (FUN-10) |
| Mensajes de error | Los `messages` de Django se muestran con alertas propias y auto-cierre | Bajo `DEBUG=1` cualquier 500 (como SEG-01) muestra traceback completo al usuario final — nada pulido para público |
| Consistencia visual | Misma hoja de estilos en todo el producto; badges de área/estado coherentes | Franjas/estados "mixto" caen al branch `{% else %}` y se pintan como **civil** (plantillas con if binario); favicon ausente (404 `/favicon.ico`) |
| Prototipo raíz | (no forma parte del producto) | 10+ pantallas HTML de diseño con módulos inexistentes que pueden leerse como "funcionalidad implementada" ante un público no técnico (ARQ-16) |

## 5. Veredicto

**El proyecto es un MVP real y demostrable, a un commit de distancia de no serlo.** La corrección de SEG-01 (una línea de import), la regeneración de datos de demo (franjas futuras, citas colgadas del cliente sembrado, un estudiante con perfil de tutor) y asegurar las variables de entorno (DEBUG/SECRET_KEY) son suficientes para una demostración estable. Todo lo demás puede planificarse con calma según `PLAN_CORRECCIONES.md`.
