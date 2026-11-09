# PLAN DE CORRECCIONES — CITI

Plan priorizado derivado de la auditoría (Fase 01). Orden de ejecución: BLOQUEANTES → IMPORTANTES → FUTUROS.

## Estado global (09/11/2026 — Fases 02, 03 y 04 ejecutadas)

| Bloque | Estado |
|---|---|
| B-1 SEG-01 | ✅ Corregido + matriz 5×5 verde + verificado en navegador real |
| B-2 datos demo | ✅ `seed_demo` coherente (director, tutores por umbrales, franjas futuras, todos los estados, reserva en vivo probada) |
| B-3 config | ✅ Entornos desarrollo/producción, secreto obligatorio en prod, `.env.example`, `VARIABLES_ENTORNO.md` |
| B-4 autoseed | ✅ Explícito, idempotente, bloqueado en producción; sin side-effects de GET |
| B-5/6 pruebas | ✅ 105 pruebas OK (42 Fase 02 + 19 Fase 03 + 44 Fase 04; ninguna reducida) |
| I-1 carrera | ✅ Cerrado en Fase 03 (atomic + `select_for_update` en la reserva) |
| I-2 estados | ✅ **Cerrado en Fase 04**: tabla formal `CitaAsesoria.TRANSICIONES` aplicada en servicio y vistas (página y modal); `finalizada→en_proceso` solo como reapertura por ajuste del cliente; 3 pruebas |
| I-3 uploads | ✅ **Cerrado en Fase 04**: vista autorizada `portal:cita_adjunto` (dueña/docente/tutor/coordinador de área/director; demás = 403); todos los enlaces de descarga del sitio pasan por ella |
| I-4 cancelación portal | ✅ **Cerrado en Fase 04**: POST autenticado con confirmación doble (JS + campo `confirmar=si`), solo en solicitada/asignada, evento `cancelada` con actor; rechazada en en_proceso/finalizada (probado) |
| I-5 MIXTO | ⏳ **Pendiente** (Fase 04 no lo declaró resuelto): sigue sin flujo operativo; sin franjas mixtas en BD; aviso honesto en la UI |
| I-6 tipo_servicio | ✅ **Cerrado en Fase 04**: consultoría `especializada` exige docente (`CitaAsesoria.clean()` + `asignar_cita`, con mensaje propio); ficha `ctx_*` de reserva solo aplica a consultoría; denegación demostrada en vivo |
| I-7 seguridad | 🔶 SEG-13 ✅, SEG-15 ✅ en reserva, SEG-18 ✅ (descarga de adjunto autenticada, Fase 04); SEG-14/21/22/23 abiertos |
| I-8 KPI arbitrario | ✅ Eliminado del dashboard estudiante (ahora casos asignados/cerrados/valoración media reales) |
| I-9 requirements/CI | ⏳ Pendiente |
| I-10 docs | 🔶 Guías nuevas completas; ERD antiguo aún pendiente de reescribir |
| F-* | ✅ Parciales: menú hamburguesa, navegación lateral real en los 5 paneles (con rutas verificadas), branding admin, CSV, portal de seguimiento + interacción/aprobación (Fase 04), organigrama retirado de la UI. Pendientes: recuperaciones, acta PDF, módulos de taller/convenio |

---

## 🔴 BLOQUEANTES — antes de cualquier demo/presentación

| # | Hallazgo | Corrección mínima | Esfuerzo |
|---|---|---|---|
| B-1 | SEG-01 (500 al cruzar rol) | Añadir `from django.shortcuts import redirect` en `backend/portal/decorators.py`. Añadir la prueba de la matriz rol×URL (P0-1 de la matriz de pruebas). | 15 min |
| B-2 | FUN-12 (calendario vacío, sin reserva demo) | Regenerar datos: crear franjas futuras reales (o depurar las 9 vencidas: `activa=False`); asignar las citas existentes al cliente sembrado o sembrar citas coherentes; subir el perfil de un estudiante demo a tutor (8°/130/4.0) vía admin; documentar el guion de cuentas a usar. Ideal: comando `seed_demo` completo (usuarios + franjas futuras + citas). | 1–2 h |
| B-3 | SEG-03 (defaults inseguros) | Arrancar la demo con `DJANGO_DEBUG` explícito y sin publicar el puerto; preparar un `.env`-checklist de despliegue (DEBUG=0, SECRET_KEY propio, ALLOWED_HOSTS). | 30 min |
| B-4 | SEG-02 (cuentas públicas auto-sembradas) | Decisión explícita: (a) demo 100 % local → documentar el riesgo y basta; (b) el sistema se expone en red → quitar `ensure_demo_users()` de `landing`/`login_view` y dejar solo el management command. Si hay jueces externos con el repo, asumir (b). | 30 min |
| B-5 | Demo sin cuenta Director sembrada | Añadir director al seed (con `is_staff` si se va a mostrar admin) o documentar su creación; hoy existe solo un usuario personal (`is_staff=1`) que no es reproducible en clon limpio. | 15 min |
| B-6 | Criterio mínimo de pruebas | Implementar las 5 pruebas P0 (`MATRIZ_DE_PRUEBAS.md` §4): matriz de roles, reserva, máquina de estados, IDOR, registro. Protegen exactamente lo que la auditoría encontró roto. | 3–4 h |

## 🟠 IMPORTANTES — inmediatamente después de la demo (o antes si el tiempo lo permite)

| # | Hallazgo | Corrección | Esfuerzo |
|---|---|---|---|
| I-1 | FUN-05 (overbooking por carrera) | Envolvizar `reservar_cita_api` en `transaction.atomic()` + `FranjaHoraria.objects.select_for_update().get(pk=...)` antes de `esta_disponible`; re-verificar constraint de mismo-cliente. Prueba de dos hilos. | 2 h |
| I-2 | FUN-06 (estados sin transiciones) | Centralizar la máquina de estados (dict de transiciones válidas + validación en form/view); quitar `estado` y `estudiante_apoyo` del `DocenteCasoForm`; registrar historia de cambios (tabla `CitaEstadoLog` o append de `NotaBitacora`). | 3–4 h |
| I-3 | SEG-04 (uploads/media) | Validar tipo/tamaño en servidor, renombrar con UUID, vista de descarga `login_required` + filtro por rol/propiedad con `FileResponse(as_attachment=True)`; eliminar enlaces directos a `MEDIA_URL` de las plantillas. | 3–4 h |
| I-4 | FUN-07 (cancelación) | Endpoint POST cliente (antes de "en proceso") y coordinador; regla: cancelada libera cupo (ya lo hace: `ocupan_cupo()` la excluye) + motivo. | 2–3 h |
| I-5 | FUN-09/F-26 (MIXTO) | Decidir semántica: o catálogo mixto de subespecialidades + bandeja de ambos coordinadores (filtro `franja__area__in=[area,'mixto']` en helper y asignación), o quitar 'mixto' de las opciones visibles del admin hasta implementarlo. | 2 h |
| I-6 | FUN-10 (tipo_servicio decorativo) | Usar el tipo en la asignación (orientación→exigir tutor; especializada→exigir docente) y habilitar cierre por tutor en orientación; o eliminar el selector hasta tener el flujo. | 3 h |
| I-7 | SEG-13/14/15/21/22 | `validate_password` en registro; mensaje de login neutro; errores genéricos en API + log; `require_POST` en logout; `textContent` en `showAlert`. | 2–3 h |
| I-8 | FUN-11 (KPI inventado) | Retular el KPI ("casos×2 h estimado") o calcular horas de sesión reales; no mostrar fórmulas ocultas como métricas oficiales. | 30 min |
| I-9 | PRB (0 tests, CI) | Ajustar `requirements.txt` con versiones fijadas; añadir job de CI (check + makemigrations --check + test). | 1–2 h |
| I-10 | ARQ-16/17 (docs) | Reescribir `docs/erd-mermaid.md` con los modelos reales (o renombrarlo "esquema planeado"); README con instalación, env vars, y semilla; marcar `app/`, `dashboards/`, `plantillas/` como prototipo obsoleto; eliminar apps stub raíz o dejar constancia en el repo. | 2–3 h |

## 🟡 FUTUROS — no bloquean la demo; v2 del producto

| # | Hallazgo | Mejora |
|---|---|---|
| F-1 | FUN-08 | Recuperación de contraseña por correo (configuración `EMAIL_*`, token firmado) — requiere infraestructura de correo UCC. |
| F-2 | FUN-28 / F-25 | UI de coordinación de agenda: crear/editar franjas por coordinador/director con calendario (hoy solo admin). |
| F-3 | FUN-13 | Agenda semanal del coordinador/director (consumir la API de eventos con rol no-cliente y agregar métricas de ocupación). |
| F-4 | F-17 | Acta en PDF real (WeasyPrint o similar) + opción de envío al cliente y marca de agua de borrador. |
| F-5 | UX (§4 de `AUDITORIA_GENERAL.md`) | Menú móvil real (hamburguesa) para dashboards; navegación lateral funcional hoy vacía (`sidebar_nav`); enlace de logout visible en móvil; badging correcto para área mixta (los `{% if %}` binarios muestran "civil" en franjas mixtas). |
| F-6 | ARQ (DRY) | Extraer servicios (`assign_cita`, `change_state`, `reserve`) reutilizados por vista de página y modal, eliminando las 4 copias de lógica. |
| F-7 | Seguridad | django-allauth/axes, CSP (`django-csp`), HSTS, audit log, rate-limit API, backup de media. |
| F-8 | Funcional | Módulos del prototipo que el producto prometía (talleres, convenios, informes con firma) — solo si hay pedido real; hoy el ERD planeado vive en docs sin código. |

---

## Orden recomendado de una sola sentada (si el tiempo apremia)

1. B-1 (15 min) + B-3/B-4/B-5 (1 h) + B-2 (2 h) → **demo estable y segura**.
2. B-6 (4 h) → red de seguridad para no regresser mientras se arregla el resto.
3. I-1, I-2, I-3 (9 h) → los tres riesgos de producción restantes.
4. El resto de IMPORTANTES según tiempo disponible; FUTUROS a planificación de v2.

## Criterio de salida del plan

- Demo completa: cliente reserva en franja futura → coordinador asigna (docente + tutor) → docente cierra → acta → cliente califica, **sin pantallas de error** y sin tocar el admin durante la presentación.
- `manage.py test` > 0 pruebas y todas verdes; matriz rol×URL sin 500; reserva concurrente sin sobreasignación en prueba de dos hilos.
