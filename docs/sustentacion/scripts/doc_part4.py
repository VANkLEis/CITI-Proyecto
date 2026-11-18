"""Capítulos 10–13 del documento maestro."""


def build(k):
    # ----------------------------------------------------------------- 10
    k.h1("10. Decisiones de arquitectura (ADR)")

    k.h2("10.1 Resumen de decisiones")
    k.p("Las decisiones se documentaron con el formato de Architecture Decision Record: "
        "contexto, alternativas, decisión, consecuencias y evidencia. No se registran todas las "
        "decisiones de código, solo aquellas que cambian la estructura, el costo operativo o la "
        "capacidad de evolución. El resumen siguiente permite ubicar la decisión y su impacto "
        "antes de leer el detalle.")
    k.table("Catálogo de ADR",
            ["ADR", "Decisión", "Alternativa principal", "Consecuencia dominante"],
            [["ADR-01", "Monolito modular Django", "Microservicios", "Consistencia transaccional y menor costo operativo"],
             ["ADR-02", "MVT + JSON mínimo", "SPA + DRF", "Menos estado y superficie en el cliente"],
             ["ADR-03", "SQLite dev / PostgreSQL prod", "Una sola base", "Demo simple; producción con concurrencia real"],
             ["ADR-04", "Servicios explícitos", "Señales globales", "Eventos sin duplicados ni efectos ocultos"],
             ["ADR-05", "`CitaEvento` append-only", "Log de texto", "Evidencia consultable y auditable"],
             ["ADR-06", "Login con portal esperado", "Login genérico", "Mejor experiencia; revela el portal (SEG-14)"],
             ["ADR-07", "Regla académica en el modelo", "Validación manual", "El tutor no se asigna por conveniencia"],
             ["ADR-08", "Interacción separada del estado", "Todo en `estado`", "Aprobar no cierra; el historial no se mezcla"],
             ["ADR-09", "Adjuntos por vista autorizada", "`MEDIA_URL` directa", "No hay descargas por URL adivinada"],
             ["ADR-10", "Configuración por entorno", "Settings hardcodeados", "Producción exige secretos y HTTPS"]],
            widths=[0.55, 1.2, 1.0, 1.55])

    adrs = [
        ("ADR-01 · Monolito modular en lugar de microservicios",
         "El CITI maneja una transacción que abarca cita, evento, marca temporal e interacción. "
         "El equipo es de dos personas, el plazo de diez semanas y no hay presupuesto de "
         "infraestructura. La independencia de despliegue no es un requisito del negocio; la "
         "consistencia sí.",
         "Microservicios por dominio, SOA con bus de servicios, monolito sin módulos.",
         "Un solo proyecto Django con tres apps y fronteras explícitas. Los servicios de dominio "
         "concentran las reglas y las apps se pueden extraer cuando el volumen lo justifique.",
         "Un despliegue y una transacción; menor independencia y un solo punto de fallo. La "
         "modularidad se demuestra por dependencias, no por número de procesos.",
         "`config/settings.py`, `accounts/`, `scheduling/`, `portal/`; 107 pruebas en un solo comando."),
        ("ADR-02 · Templates Django con JSON mínimo en lugar de SPA + DRF",
         "El producto es intensivo en formularios, tablas y flujos por rol. Una SPA habría "
         "duplicado la autorización en el cliente, agregado un build y ampliado la superficie "
         "de ataque. Solo el calendario y la reserva necesitan JSON.",
         "SPA con React/Vue y DRF; Django + HTMX; templates con JavaScript vanilla.",
         "Templates server-side, formularios con CSRF y dos endpoints JSON: "
         "`/agenda/api/eventos/` y `/agenda/api/reservar/`.",
         "Menos interactividad rica y más recargas; a cambio, menos estado, menos dependencias y "
         "una autorización concentrada en el servidor.",
         "`portal/templates/`, `scheduling/views.py`; pruebas de API y de navegación."),
        ("ADR-03 · SQLite en desarrollo y PostgreSQL en producción",
         "La demo debe arrancar en un portátil sin instalar un motor adicional. La producción "
         "necesita concurrencia de escritores, backups y administración.",
         "SQLite en ambos entornos; PostgreSQL en ambos; MySQL.",
         "SQLite por defecto y PostgreSQL cuando `DATABASE_URL` empieza por `postgres`. El "
         "código no cambia; solo la configuración.",
         "Dos comportamientos posibles si no se prueba en PostgreSQL. La ruta de escalamiento "
         "incluye PgBouncer y pruebas de carga contra el motor real.",
         "`config/settings.py`, `requirements.txt` (`psycopg2-binary`), evidencia de migraciones."),
        ("ADR-04 · Servicios de dominio explícitos en lugar de señales globales",
         "Las señales de Django son cómodas, pero dispersan efectos: un `save()` puede disparar "
         "eventos sin que la vista lo sepa. Eso dificulta auditar y probar.",
         "Señales `post_save`/`pre_save`; middleware; servicios llamados desde vistas.",
         "Funciones explícitas en `scheduling/trazabilidad.py`, invocadas dentro de "
         "`transaction.atomic()` por vistas, API y admin.",
         "Más líneas de llamada y disciplina del equipo; a cambio, el flujo es legible, no hay "
         "eventos duplicados y una transacción fallida no deja evidencia.",
         "`trazabilidad.py`, pruebas `TrazabilidadEventosTests`."),
        ("ADR-05 · CitaEvento append-only como historial",
         "La operación necesita responder qué pasó, quién lo hizo y cuándo, incluso si el usuario "
         "se elimina o cambia de rol. Un campo `updated_at` no cuenta la historia.",
         "Log de texto; tabla de auditoría genérica; eventos en el modelo de cita.",
         "Tabla `CitaEvento` con tipo, actor, `actor_label`, estados, descripción, metadata y "
         "fecha; sin edición ni borrado desde el portal.",
         "Crecimiento lineal de la tabla y necesidad de índices; a cambio, evidencia inmutable y "
         "consultable por caso.",
         "`scheduling/models.py`, admin de solo lectura, pruebas de evento y transacción."),
        ("ADR-06 · Login consciente del portal",
         "Un usuario puede tener un rol, pero el jurado y los usuarios reales necesitan entrar por "
         "el portal correcto. Un login genérico redirige sin explicar y mezcla experiencias.",
         "Login único con redirección; selección de portal en el dashboard; login con rol esperado.",
         "El formulario envía `expected_role` y rechaza cuentas cuyo rol no coincide. "
         "`/cuenta/login/?rol=<role>` preselecciona el portal.",
         "Mejor claridad y menos errores de entrada; el mensaje revela el portal real de la "
         "cuenta, un riesgo residual declarado (SEG-14).",
         "`accounts/forms.py`, `accounts/views.py`, pruebas de matriz rol × portal."),
        ("ADR-07 · Regla académica del tutor en el modelo",
         "El tutor debe tener semestre, créditos y promedio mínimos. Si la regla vive en un "
         "formulario, se puede saltar por admin, seed o script.",
         "Validación solo en el formulario; validación en la vista; validación en el modelo y la señal.",
         "`PerfilEstudiante.cumple_requisitos_tutor()` y `save()` sincronizan "
         "`autorizado_como_tutor` y `student_type`; `CitaAsesoria.clean()` vuelve a validar.",
         "Guardar un perfil puede promover o degradar al estudiante; el seed debe usar "
         "`skip_validation` cuando corresponda. A cambio, no hay tutores por conveniencia.",
         "`accounts/models.py`, `accounts/signals.py`, pruebas de perfil y asignación."),
        ("ADR-08 · Interacción separada del estado",
         "Un comentario, una entrega y una aprobación no son lo mismo que un cambio de estado. "
         "Mezclarlos produce estados que dependen del último mensaje y cierres accidentales.",
         "Todo en `CitaAsesoria.estado`; un campo de texto libre; una tabla de interacciones.",
         "`CitaInteraccion` con tipo, autor, rol congelado y visibilidad; `CitaEvento` refleja "
         "cada interacción. Aprobar no finaliza; un ajuste puede reabrir.",
         "Dos tablas que deben mantenerse sincronizadas por servicio; a cambio, la conversación "
         "y el ciclo de vida se auditan por separado.",
         "`CitaInteraccion`, `registrar_interaccion`, `registrar_decision_cliente`, pruebas de "
         "aprobaciones y reapertura."),
        ("ADR-09 · Adjuntos servidos por vista autorizada",
         "Los adjuntos pueden contener información sensible. Servirlos por `MEDIA_URL` permite "
         "descargarlos a quien adivine o copie la URL, sin verificar rol ni alcance.",
         "`MEDIA_URL` directa; almacenamiento público; vista con control de acceso.",
         "`cita_adjunto` verifica sesión, rol y relación con la cita; el template usa esa ruta y "
         "no `archivo_adjunto.url`.",
         "Más código y una respuesta potencialmente más lenta; a cambio, no hay descargas por "
         "URL adivinada y se puede auditar el acceso.",
         "`portal/views.py` (`cita_adjunto`), pruebas `CancelacionI4AdjuntoI3Tests`."),
        ("ADR-10 · Configuración por entorno y endurecimiento en producción",
         "La demo local necesita HTTP y SQLite; producción necesita secretos, hosts permitidos y "
         "HTTPS. Un solo `settings.py` con valores fijos no puede cubrir ambos sin riesgo.",
         "Settings separados por archivo; variables de entorno; `django-environ`.",
         "`DJANGO_ENV`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` y "
         "`CITI_*`; en producción se exigen secreto y hosts, y se activan HSTS, cookies seguras, "
         "redirección SSL y `X_FRAME_OPTIONS=DENY`.",
         "La configuración es más compleja y un despliegue mal configurado falla al arrancar; a "
         "cambio, no hay valores inseguros por defecto en producción.",
         "`config/settings.py`, `.env.example`, `docs/demo/VARIABLES_ENTORNO.md`."),
    ]
    for title, context, alternatives, decision, consequences, evidence in adrs:
        k.h2(title)
        k.lead("Contexto.", context)
        k.lead("Alternativas.", alternatives)
        k.lead("Decisión.", decision)
        k.lead("Consecuencias.", consequences)
        k.lead("Evidencia.", evidence)

    # ----------------------------------------------------------------- 11
    k.h1("11. Implementación y despliegue")

    k.h2("11.1 Stack y versiones")
    k.table("Stack tecnológico",
            ["Componente", "Versión / elección", "Función"],
            [["Python", "3.x del entorno del curso", "Lenguaje y runtime"],
             ["Django", "5.2.18 (restricción `>=5.0,<6`)", "Framework web, ORM, admin, auth"],
             ["SQLite", "Incluido en Python", "Base local de desarrollo"],
             ["PostgreSQL", "`psycopg2-binary>=2.9`", "Base de producción por `DATABASE_URL`"],
             ["python-dotenv", "`>=1.0`", "Carga de `.env` sin sobrescribir el shell"],
             ["HTML/CSS/JS", "Plantillas Django + FullCalendar CDN", "Interfaz y agenda"],
             ["PlantUML", "1.2024.8", "Diagramas versionables"],
             ["python-pptx / python-docx", "1.0.2 / 1.2.0", "Entregables de sustentación"]],
            widths=[0.9, 1.3, 1.2])

    k.h2("11.2 Estructura del proyecto")
    k.code("""CITI-Proyecto/
├── backend/
│   ├── config/          settings.py, urls.py, wsgi.py, asgi.py
│   ├── accounts/        CustomUser, Empresa, PerfilEstudiante, login, seed
│   ├── scheduling/      FranjaHoraria, CitaAsesoria, CitaEvento, CitaInteraccion
│   ├── portal/          views.py, forms.py, indicadores.py, tests.py, templates
│   ├── templates/       base.html, dashboard_base.html, accounts/, portal/
│   ├── static/          CSS, JS, imágenes institucionales
│   ├── media/           documentos_citas/<año>/<mes>/
│   └── manage.py
├── docs/sustentacion/   diagramas/, fuentes/, evidencias/, scripts/
├── Presentacion final/  guía docente y capturas heredadas
├── requirements.txt
└── venv/                entorno del curso (Django 5.2.18)""")

    k.h2("11.3 Variables de entorno")
    k.table("Variables reconocidas",
            ["Variable", "Valor por defecto", "Efecto"],
            [["`DJANGO_ENV`", "`desarrollo`", "Activa el perfil de producción y sus validaciones"],
             ["`DJANGO_DEBUG`", "`1` en desarrollo, `0` en producción", "Modo de depuración; prohibido en producción"],
             ["`DJANGO_SECRET_KEY`", "Fallback solo en desarrollo", "Obligatorio en producción"],
             ["`DJANGO_ALLOWED_HOSTS`", "`127.0.0.1,localhost`", "Obligatorio en producción; lista separada por comas"],
             ["`DATABASE_URL`", "SQLite", "Si empieza por `postgres`, cambia el motor"],
             ["`CITI_DEMO_PASSWORD`", "`CITIPass2026*`", "Contraseña de cuentas demo"],
             ["`CITI_MIN_SEMESTRE_TUTOR`", "`8`", "Umbral académico"],
             ["`CITI_MIN_CREDITOS_TUTOR`", "`130`", "Umbral académico"],
             ["`CITI_MIN_PROMEDIO_TUTOR`", "`4.0`", "Umbral académico"],
             ["`DJANGO_HSTS_SECONDS`", "`31536000`", "HSTS en producción"]],
            widths=[1.15, 1.1, 1.45])

    k.h2("11.4 Operación local")
    k.p("El arranque local está pensado para que un evaluador pueda reproducirlo sin leer diez "
        "páginas. Se usa el venv de la raíz, se ejecutan las migraciones, se carga el seed y se "
        "levanta el servidor. El seed es idempotente y se niega a correr en producción. Las "
        "pruebas usan una base aislada y no tocan `db.sqlite3`.")
    k.code("""cd backend
..\\venv\\Scripts\\python.exe manage.py migrate
..\\venv\\Scripts\\python.exe manage.py seed_demo
..\\venv\\Scripts\\python.exe manage.py runserver
# En otra terminal:
..\\venv\\Scripts\\python.exe manage.py test""")
    k.p("Cuentas demo: `director@citi.ucc.edu.co`, `coordinador@citi.ucc.edu.co`, "
        "`docente@citi.ucc.edu.co`, `estudiante@citi.ucc.edu.co` y "
        "`cliente@empresatolima.co`, con la contraseña `CITIPass2026*` (configurable). "
        "Los portales se preseleccionan con `?rol=<role>`.")

    k.h2("11.5 Topología de producción")
    k.p("La topología propuesta mantiene el mismo código y cambia la infraestructura: GitHub "
        "como origen, Nginx como terminador HTTPS y proxy, Gunicorn o uWSGI como servidor WSGI, "
        "Django 5 con `config.wsgi`, PostgreSQL por `DATABASE_URL` y un volumen o bucket para "
        "los adjuntos. No hay Docker, Procfile ni pipeline de CI/CD en esta entrega; esa "
        "ausencia se declara y se ubica en la ruta de trabajo futuro.")
    k.figure("09_despliegue.png",
             "Despliegue objetivo: GitHub → Nginx → Gunicorn/uWSGI → Django → PostgreSQL, con "
             "almacenamiento de media y configuración por entorno.", 16.2)

    k.h2("11.6 Endurecimiento en producción")
    k.p("Con `DJANGO_ENV=produccion`, el sistema exige `DJANGO_SECRET_KEY` y "
        "`DJANGO_ALLOWED_HOSTS`, prohíbe `DEBUG=1`, activa `SECURE_SSL_REDIRECT`, HSTS con "
        "subdominios, cookies `Secure`, `SECURE_CONTENT_TYPE_NOSNIFF`, "
        "`SECURE_REFERRER_POLICY=same-origin` y `X_FRAME_OPTIONS=DENY`. Si falta un secreto o "
        "un host, el arranque falla con `ImproperlyConfigured`; no hay un fallback silencioso "
        "que ponga la instalación en riesgo. Detrás de Nginx se debe habilitar "
        "`SECURE_PROXY_SSL_HEADER` (documentado y comentado en `settings.py`).")

    k.h2("11.7 Medios y almacenamiento")
    k.p("Los adjuntos se guardan en `media/documentos_citas/<año>/<mes>/`. En desarrollo, "
        "`runserver` sirve `/media/` solo con `DEBUG=1`; en producción esa ruta no debe "
        "exponerse. El acceso pasa por `cita_adjunto`, que verifica sesión, rol y relación con "
        "la cita. Para escalar, el siguiente paso es un almacenamiento de objetos (S3 o "
        "equivalente) con URLs firmadas y una política de retención.")

    k.h2("11.8 Brechas de despliegue")
    k.table("Brechas y trabajo futuro",
            ["Brecha", "Impacto", "Acción propuesta"],
            [["Sin Docker", "Diferencias entre máquinas", "`Dockerfile` + `docker-compose` con Postgres"],
             ["Sin CI/CD", "Regresiones manuales", "GitHub Actions: check, migraciones, tests"],
             ["Dependencias no pinneadas", "Build no reproducible", "`requirements.txt` con versiones exactas y `pip-tools`"],
             ["Sin backups", "Pérdida de evidencia", "Backups automáticos de Postgres y media"],
             ["Sin observabilidad", "Diagnóstico lento", "Logs estructurados, métricas y alertas"],
             ["Media local", "No escala ni persiste", "Bucket S3 con URLs firmadas"]],
            widths=[1.0, 1.15, 1.55])

    # ----------------------------------------------------------------- 12
    k.h1("12. Verificación y pruebas")

    k.h2("12.1 Estrategia")
    k.p("La suite se organizó por riesgo, no por archivo. Cada clase agrupa un conjunto de "
        "comportamientos que podrían fallar juntos: acceso por rol, reservas, estados, IDOR, "
        "registro, seed, trazabilidad, indicadores, seguimiento, interacciones, aprobaciones, "
        "modalidades, cancelación/adjuntos, reportes y navegación. Las pruebas usan el cliente "
        "de Django y una base de pruebas aislada; no dependen de datos manuales ni de un "
        "servidor externo. El resultado es reproducible con un comando.")

    k.h2("12.2 Clases de prueba")
    k.table("Clases de prueba y foco",
            ["Clase", "Foco"],
            [["`RoleAccessMatrixTests`", "Matriz de roles × portales y redirección al portal correcto"],
             ["`ReservasApiTests`", "Reserva, cupos, 409, constraint de doble reserva"],
             ["`StateMachineTests`", "Transiciones válidas e inválidas"],
             ["`IdorTests`", "Acceso directo a objetos ajenos (404/403)"],
             ["`RegistroValidacionTests`", "Registro de clientes, empresa y contraseña"],
             ["`SeedDemoTests`", "Idempotencia, bloqueo en producción y datos demo"],
             ["`RegresionesAuditTests`", "Bloqueantes de la auditoría de cierre"],
             ["`EndToEndDemoTests`", "Flujo completo de la demo"],
             ["`TrazabilidadEventosTests`", "Eventos, transacción fallida y marcas temporales"],
             ["`IndicadoresTests`", "KPI, filtros, área forzada y CSV"],
             ["`SeguimientoClienteTests`", "Mis solicitudes, seguimiento y cancelación"],
             ["`InteraccionComentariosTests`", "Comentarios, respuestas y notas internas"],
             ["`AprobacionesEntregablesTests`", "Entrega, aprobación, ajuste y reapertura"],
             ["`ModalidadesServicioTests`", "Orientación vs consultoría especializada"],
             ["`TransicionesFormalTests`", "Tabla formal de transiciones (I-2)"],
             ["`CancelacionI4AdjuntoI3Tests`", "Cancelación propia y descarga autorizada (I-3/I-4)"],
             ["`ReportesInteraccionTests`", "Métricas de aprobación y columna CSV"],
             ["`NavegacionRegresionF4Tests`", "Navegación y regresiones de la fase 4"]],
            widths=[1.35, 2.1])

    k.h2("12.3 Resultados de la ejecución")
    k.p("La ejecución de cierre se hizo desde `backend/` con el venv de la raíz. El resultado "
        "fue: `check` sin issues, `makemigrations --check` sin cambios, `seed_demo` idempotente "
        "y 107 pruebas en verde en 67,524 segundos. La base de desarrollo no se modificó porque "
        "Django crea y destruye una base de pruebas separada.")
    k.code("""System check identified no issues (0 silenced).
Found 107 test(s).
Ran 107 tests in 67.524s
OK""")

    k.h2("12.4 Cobertura por riesgo")
    k.table("Riesgo y evidencia de prueba",
            ["Riesgo", "Prueba representativa", "Resultado"],
            [["Un rol entra a un portal ajeno", "`test_matriz_rol_x_portal`", "Redirección/404"],
             ["Doble reserva o sobrecupo", "`ReservasApiTests`", "409 y constraint"],
             ["Transición ilegal", "`TransicionesFormalTests`", "`ValidationError`"],
             ["IDOR en detalle o adjunto", "`IdorTests`, `CancelacionI4AdjuntoI3Tests`", "404/403"],
             ["Evento sin transacción", "`TrazabilidadEventosTests`", "Revert completo"],
             ["Indicador con área manipulada", "`IndicadoresTests`", "Área forzada"],
             ["Nota interna visible al cliente", "`InteraccionComentariosTests`", "Filtro de visibilidad"],
             ["Aprobación que cierra el caso", "`AprobacionesEntregablesTests`", "Estado intacto"],
             ["Seed duplicado o en producción", "`SeedDemoTests`", "Idempotente / bloqueado"]],
            widths=[1.2, 1.45, 0.8])

    k.h2("12.5 Verificación manual y E2E")
    k.p("Además de la suite, se recorrieron los cinco portales en navegador con las cuentas demo. "
        "Se verificó el responsive en 390, 768 y 1440 px, los estados vacíos, la navegación "
        "entre partials, la descarga autorizada de un adjunto y la exportación CSV. Las capturas "
        "de la demo se conservan en `docs/sustentacion/evidencias/`. La verificación manual no "
        "reemplaza la suite; cubre lo que una prueba de unidad no ve: jerarquía visual, textos "
        "y comportamiento del navegador.")

    k.h2("12.6 Regresiones y auditoría")
    k.p("La auditoría de cierre encontró bloqueantes que se corrigieron y se convirtieron en "
        "pruebas: el seed ya no se ejecuta en cada GET; el login exige portal; los eventos no se "
        "duplican; la reapertura solo ocurre por ajuste; el adjunto no se sirve por URL directa; "
        "y la cancelación del cliente tiene confirmación. Cada corrección quedó cubierta por una "
        "prueba de regresión, de modo que el defecto no puede volver silenciosamente.")

    k.h2("12.7 Límites")
    k.p("No se calculó cobertura formal, no hay pruebas de carga, no se probó en PostgreSQL "
        "durante la ejecución de cierre y no hay pruebas de accesibilidad automatizadas. La "
        "suite cubre comportamiento de negocio, no rendimiento ni seguridad ofensiva. Esos "
        "límites se declaran y se ubican en el plan de mejora; no se presentan como virtudes.")

    # ----------------------------------------------------------------- 13
    k.h1("13. Conclusiones, límites y trabajo futuro")

    k.h2("13.1 Logros")
    k.p("El proyecto entrega un sistema funcional que cubre el ciclo completo de una solicitud: "
        "registro, reserva, asignación, ejecución, entrega, decisión y cierre. Los cinco roles "
        "tienen portales con alcance propio; el historial es consultable y append-only; los "
        "indicadores se calculan desde la base real; y la suite de 107 pruebas respalda las "
        "reglas críticas. La arquitectura es deliberadamente sobria: un solo despliegue, tres "
        "apps y servicios explícitos. Esa sobriedad es una decisión, no una limitación accidental.")

    k.h2("13.2 Decisiones que sostuvieron el resultado")
    k.bullets([
        "**Consistencia antes que independencia:** el monolito modular permitió una sola transacción para estado y evidencia.",
        "**Servidor antes que frontend:** la autorización y las transiciones no se delegan al navegador.",
        "**Evidencia antes que memoria:** `CitaEvento` y `CitaInteraccion` conservan qué pasó y quién lo hizo.",
        "**Explicititud antes que magia:** los servicios se llaman desde las vistas; no hay señales globales opacas.",
        "**Límites declarados:** el sistema no promete producción ni escala; documenta qué falta y cómo llegaría.",
    ])

    k.h2("13.3 Límites")
    k.table("Límites de la entrega",
            ["Ámbito", "Límite", "Consecuencia"],
            [["Funcional", "Flujo `mixto` y algunas observaciones de seguridad en revisión", "No se usa como caso principal de demo"],
             ["Infraestructura", "Sin Docker, CI/CD, backups ni observabilidad", "Despliegue manual y diagnóstico limitado"],
             ["Rendimiento", "Sin prueba de carga; métricas locales", "No se conoce el punto de saturación"],
             ["Datos", "SQLite en la demo; PostgreSQL no probado en carga", "Riesgo de diferencias de comportamiento"],
             ["Accesibilidad", "Sin auditoría WCAG completa", "Puede haber barreras para lectores de pantalla"],
             ["Seguridad", "Sin 2FA, rate limiting ni antivirus de adjuntos", "Riesgo residual declarado"]],
            widths=[0.8, 1.65, 1.25])

    k.h2("13.4 Ruta de evolución")
    k.table("Roadmap por fases",
            ["Fase", "Objetivo", "Acciones"],
            [["1. Producción", "Operar con seguridad y reproducibilidad", "PostgreSQL, Gunicorn, Nginx, CI/CD, dependencias pinneadas, backups, logs"],
             ["2. Escala", "Sostener más usuarios y archivos", "Redis, tareas asíncronas, S3/CDN, rate limiting, 2FA"],
             ["3. Evolución", "Extraer módulos y medir", "Réplicas de lectura, servicios de notificaciones/reportes, observabilidad, pruebas de carga"]],
            widths=[0.75, 1.25, 1.7])

    k.h2("13.5 Lecciones aprendidas")
    k.p("La lección más importante no fue técnica: fue aprender a distinguir entre lo que el "
        "sistema hace y lo que nos gustaría que hiciera. Esa distinción obligó a corregir el "
        "seed, a separar la aprobación del cierre, a documentar los hallazgos de seguridad y a "
        "declarar los límites de las mediciones. También mostró que la arquitectura se defiende "
        "con evidencia, no con diagramas: un diagrama sin prueba es una hipótesis; una prueba "
        "sin decisión es un detalle. El valor está en la cadena completa.")
    k.p("La segunda lección fue sobre el tamaño. Un equipo de dos personas no puede sostener "
        "microservicios, una SPA y un pipeline complejo al mismo tiempo. Elegir un monolito "
        "modular no fue conformismo: fue diseñar para el contexto. La modularidad quedó en las "
        "fronteras y en los servicios, que es donde se necesita para evolucionar.")
    k.callout("Cierre",
              "CITI es un sistema funcional, trazable y con límites honestos. La arquitectura "
              "es adecuada para el contexto y tiene una ruta clara de evolución. Lo que no está "
              "implementado se declara; lo que está, se demuestra.", "teal")
