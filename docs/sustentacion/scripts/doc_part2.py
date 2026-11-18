"""Capítulos 4–6 del documento maestro."""


def build(k):
    # ------------------------------------------------------------------ 4
    k.h1("4. Requisitos, actores y reglas de negocio")

    k.h2("4.1 Actores y alcance por rol")
    k.p("El sistema define cinco roles. El rol no es una preferencia de interfaz: determina "
        "qué rutas se pueden abrir, qué objetos se pueden consultar y qué acciones se pueden "
        "ejecutar. La tabla siguiente resume el alcance; la matriz detallada de seguridad se "
        "presenta en el capítulo 8.")
    k.table("Actores, portal y alcance",
            ["Actor", "Portal", "Alcance principal", "Restricción clave"],
            [["Cliente / Empresa", "`/panel/cliente/`", "Solicitar, seguir, comentar, aprobar o pedir ajustes, cancelar", "Solo sus propias solicitudes; debe pertenecer a una empresa"],
             ["Estudiante", "`/panel/estudiante/`", "Consultar casos de apoyo y registrar bitácora", "Solo casos asignados; tutor debe cumplir umbrales académicos"],
             ["Docente", "`/panel/docente/`", "Gestionar caso, publicar entregable, generar acta", "Solo casos asignados; área compatible"],
             ["Coordinador", "`/panel/coordinador/`", "Bandeja del área, asignar docente y tutor, seguimiento y CSV", "Área forzada en servidor; no ve la otra área"],
             ["Director", "`/panel/director/`", "Panel ejecutivo, trazabilidad global, indicadores y CSV", "Lectura global; no asigna ni ejecuta casos"]],
            widths=[0.7, 0.8, 1.35, 1.15])
    k.figure("02_casos_uso.png",
             "Casos de uso por actor. Cada panel muestra las acciones que el servidor autoriza; "
             "UC-13 es compartido por coordinador (por área) y director (global).", 16.2)

    k.h2("4.2 Requisitos funcionales")
    k.table("Requisitos funcionales y su implementación",
            ["ID", "Requisito", "Implementación principal"],
            [["RF-01", "Registro público de clientes con empresa", "`accounts.views.register_cliente`, `Empresa`, `CustomUser`"],
             ["RF-02", "Login con portal esperado y rechazo de rol incorrecto", "`RoleLoginForm`, `accounts.views.login_view`"],
             ["RF-03", "Landing institucional con acceso a portales", "`portal.views.landing`"],
             ["RF-04", "Agenda de franjas por área, con cupos y vigencia", "`FranjaHoraria`, API `/agenda/api/eventos/`"],
             ["RF-05", "Reserva atómica de una franja", "`scheduling.views.reservar_cita_api`"],
             ["RF-06", "Consulta y seguimiento de solicitudes propias", "`cliente_mis_solicitudes`, `cliente_seguimiento`"],
             ["RF-07", "Cancelación de la solicitud por el cliente", "`puede_cancelar_cliente`, `cambio_estado`"],
             ["RF-08", "Comentarios e interacciones cliente–equipo", "`CitaInteraccion`, `registrar_interaccion`"],
             ["RF-09", "Entrega de resultados y decisión del cliente", "`publicar_entrega`, `registrar_decision_cliente`"],
             ["RF-10", "Asignación de docente y tutor por coordinador", "`coordinador_asignar`, `asignar_cita`"],
             ["RF-11", "Gestión del caso y acta de cierre por docente", "`docente_caso_detalle`, `docente_generar_acta`"],
             ["RF-12", "Bitácora de apoyo del estudiante", "`estudiante_caso_nota`, `NotaBitacora`"],
             ["RF-13", "Panel ejecutivo, trazabilidad e indicadores CSV", "`director_dashboard`, `trazabilidad`, `trazabilidad_csv`"],
             ["RF-14", "Descarga autorizada de adjuntos", "`cita_adjunto`"],
             ["RF-15", "Perfil propio y notificaciones internas", "`perfil_propio`, `cliente_notificaciones`"]],
            widths=[0.45, 1.55, 1.6])

    k.h2("4.3 Requisitos no funcionales")
    k.table("Requisitos no funcionales priorizados",
            ["ID", "Atributo", "Requisito", "Evidencia"],
            [["RNF-01", "Seguridad", "Toda ruta privada exige autenticación y rol; el alcance por área y propietario se fuerza en servidor", "Matriz 5×5, pruebas IDOR, 404/403"],
             ["RNF-02", "Trazabilidad", "Cada mutación relevante deja un evento inmutable en la misma transacción", "`CitaEvento`, pruebas de transacción fallida"],
             ["RNF-03", "Eficiencia", "Las vistas principales responden en decenas de milisegundos en local y sin consultas N+1 evidentes", "Métricas fase 0: 2,8–28,1 ms"],
             ["RNF-04", "Usabilidad", "Cinco paneles consistentes, responsive 390–1440 px, estados vacíos honestos", "Revisión en navegador y capturas"],
             ["RNF-05", "Mantenibilidad", "Tres apps con límites, servicios explícitos y suite automatizada", "107 pruebas, 18 clases"],
             ["RNF-06", "Portabilidad", "SQLite en local y PostgreSQL por `DATABASE_URL`, sin cambiar el código", "`config/settings.py`, pruebas"],
             ["RNF-07", "Integridad", "Reserva y cambios de estado atómicos; sin cupos negativos ni dobles reservas", "`transaction.atomic`, `select_for_update`, constraint"],
             ["RNF-08", "Compatibilidad", "Navegadores modernos de escritorio y móvil", "HTML/CSS estándar; FullCalendar por CDN"],
             ["RNF-09", "Operabilidad", "Arranque con un comando, seed idempotente y pruebas en base aislada", "`runserver`, `seed_demo`, `manage.py test`"],
             ["RNF-10", "Privacidad", "Notas internas invisibles al cliente; CSV sin correos personales", "`para_cliente`, `interacciones_visibles`, `csv_rows`"]],
            widths=[0.5, 0.75, 1.55, 1.05])

    k.h2("4.4 Reglas de negocio")
    k.p("Las reglas siguientes no son validaciones de formulario: son invariantes del dominio. "
        "Cuando una regla se puede expresar en la base de datos, se expresa ahí; cuando depende "
        "del contexto, se valida en el modelo o en el servicio. La tabla indica dónde vive cada "
        "una para que no haya duda sobre quién la hace cumplir.")
    k.table("Reglas de negocio e implementación",
            ["ID", "Regla", "Dónde vive"],
            [["BR-01", "Solo un usuario con rol Cliente puede reservar una cita", "`CitaAsesoria.clean()`"],
             ["BR-02", "La franja debe estar activa, ser futura y tener cupo disponible", "`FranjaHoraria.esta_disponible`, `clean()`"],
             ["BR-03", "Un cliente no puede tener dos reservas activas en la misma franja", "`UniqueConstraint` parcial en la base"],
             ["BR-04", "Solo se permiten las transiciones de la tabla formal", "`CitaAsesoria.TRANSICIONES`, `transicion_legal()`"],
             ["BR-05", "Una consultoría especializada exige docente antes de salir de `solicitada`", "`clean()` y `asignar_cita`"],
             ["BR-06", "Docente y tutor deben pertenecer al área de la franja o ser `mixto`", "`CitaAsesoria.clean()`"],
             ["BR-07", "Un tutor debe cumplir semestre, créditos y promedio mínimos", "`PerfilEstudiante.cumple_requisitos_tutor()`"],
             ["BR-08", "El cliente solo cancela en `solicitada` o `asignada`", "`puede_cancelar_cliente()`"],
             ["BR-09", "Aprobar un entregable no finaliza el caso; un ajuste puede reabrir `finalizada`", "`registrar_decision_cliente`"],
             ["BR-10", "Una nota interna nunca es visible al cliente", "`CitaInteraccion.save()`, `interacciones_visibles`"],
             ["BR-11", "El coordinador solo opera sobre su área", "`area_helpers`, `parse_filtros(area_forzada=...)`"],
             ["BR-12", "Cada transición real produce exactamente un evento de historial", "`cambio_estado`, servicios de trazabilidad"]],
            widths=[0.5, 1.6, 1.25])

    k.h2("4.5 Casos de uso principales")
    k.table("Casos de uso y actor primario",
            ["ID", "Caso de uso", "Actor primario", "Resultado"],
            [["UC-01", "Registrarse como cliente", "Visitante", "Cuenta y empresa creadas"],
             ["UC-02", "Iniciar sesión por portal", "Todos", "Sesión con rol validado"],
             ["UC-03", "Consultar agenda", "Cliente", "Franjas disponibles por área"],
             ["UC-04", "Reservar cita", "Cliente", "Solicitud en estado `solicitada`"],
             ["UC-05", "Seguir solicitud", "Cliente", "Línea de tiempo e historial"],
             ["UC-06", "Comentar o responder", "Cliente / equipo", "Interacción registrada"],
             ["UC-07", "Aprobar o pedir ajustes", "Cliente", "Decisión sobre entregable"],
             ["UC-08", "Cancelar solicitud", "Cliente", "Estado `cancelada` con evento"],
             ["UC-09", "Asignar responsable", "Coordinador", "Estado `asignada`"],
             ["UC-10", "Gestionar caso", "Docente", "Estado `en_proceso` o `finalizada`"],
             ["UC-11", "Publicar entregable", "Docente", "Entrega visible al cliente"],
             ["UC-12", "Registrar bitácora", "Estudiante", "Nota de apoyo"],
             ["UC-13", "Consultar trazabilidad e indicadores", "Coordinador / Director", "KPIs y CSV"],
             ["UC-14", "Administrar registros", "Director staff", "CRUD administrativo auditado"]],
            widths=[0.45, 1.25, 0.95, 1.25])

    k.h2("4.6 Priorización y decisiones de alcance")
    k.p("La priorización se hizo por riesgo operativo, no por atractivo visual. Primero se "
        "resolvió lo que podía producir pérdida de confianza: identidad, cupos, estados y "
        "historial. Después se agregó lo que mejora la experiencia: comentarios, entregables, "
        "notificaciones y perfil. Lo que quedó fuera se documentó como trabajo futuro y no se "
        "insinuó como si existiera. Esa frontera es importante: un sistema académico puede "
        "estar incompleto, pero no puede mentir sobre lo que hace.")

    # ------------------------------------------------------------------ 5
    k.h1("5. Arquitectura del sistema")

    k.h2("5.1 Estilo arquitectónico y principios")
    k.p("CITI es un **monolito modular** construido sobre Django con patrón MVT (Model–View–"
        "Template) y una capa explícita de servicios de dominio. Un solo proceso, una sola "
        "base de datos y un solo despliegue, pero con fronteras internas claras: identidad en "
        "`accounts`, agenda y evidencia en `scheduling`, presentación y decisión en `portal`. "
        "La modularidad no se mide por el número de servicios desplegados, sino por la "
        "dirección de las dependencias y por la posibilidad de extraer un módulo sin reescribir "
        "el dominio.")
    k.p("Los principios que gobiernan el diseño son cuatro. Primero, **el servidor manda**: "
        "ninguna regla de acceso o de estado se delega al JavaScript. Segundo, **una sola "
        "verdad**: el estado vive en `CitaAsesoria`, la evidencia en `CitaEvento` y la "
        "conversación en `CitaInteraccion`; no se duplican banderas derivadas. Tercero, "
        "**transacción o nada**: estado, marcas temporales y evento se escriben juntos. Cuarto, "
        "**explicititud sobre magia**: servicios llamados desde las vistas en lugar de señales "
        "globales que disparan efectos difíciles de rastrear.")

    k.h2("5.2 Contexto del sistema (C4)")
    k.p("El diagrama de contexto muestra la frontera: qué actores usan el sistema y qué "
        "sistemas externos participan. CITI no es un componente aislado del mundo: conversa "
        "con el navegador por HTTP, con la base de datos por el ORM, con el sistema de archivos "
        "para los adjuntos y con GitHub para el control de versiones. FullCalendar se carga "
        "por CDN en la agenda; esa dependencia se declara porque es un punto de fallo externo.")
    k.figure("01_contexto_c4.png",
             "Contexto C4 del CITI. Los actores entran por HTTP; la frontera del sistema es "
             "Django y sus almacenes (base de datos y media).", 16.2)

    k.h2("5.3 Componentes")
    k.p("La descomposición por componentes separa responsabilidades de negocio de detalles de "
        "presentación. `accounts` contiene la identidad y las reglas académicas; `scheduling` "
        "contiene la agenda, la máquina de estados y la evidencia; `portal` contiene las vistas, "
        "formularios, indicadores y plantillas. Los servicios compartidos evitan que una regla "
        "se replique en tres vistas distintas.")
    k.figure("03_componentes.png",
             "Componentes internos y dependencias. Las flechas muestran quién llama a quién; "
             "el dominio no depende de las plantillas.", 16.2)
    k.table("Responsabilidades por app",
            ["App", "Responsabilidad", "Artefactos principales", "No debe hacer"],
            [["`accounts`", "Identidad, roles, empresa y perfil académico", "`CustomUser`, `Empresa`, `PerfilEstudiante`, `signals.py`", "Gestionar citas o indicadores"],
             ["`scheduling`", "Franjas, citas, estados, eventos e interacciones", "`FranjaHoraria`, `CitaAsesoria`, `CitaEvento`, `CitaInteraccion`, `trazabilidad.py`", "Renderizar portales o decidir permisos de vista"],
             ["`portal`", "Presentación por rol, formularios, métricas y CSV", "`views.py`, `forms.py`, `indicadores.py`, `templates/`", "Definir reglas de negocio o duplicar transiciones"],
             ["`config`", "Configuración, rutas raíz, WSGI y entorno", "`settings.py`, `urls.py`, `wsgi.py`", "Contener lógica de negocio"]],
            widths=[0.55, 1.15, 1.35, 0.95])

    k.h2("5.4 Capas y reglas de dependencia")
    k.p("La arquitectura se organiza en cuatro capas lógicas. La capa de presentación incluye "
        "navegador, URLconf, vistas y templates. La capa de aplicación contiene middleware, "
        "autenticación, decoradores y servicios de dominio. La capa de dominio contiene los "
        "modelos, las reglas académicas y la máquina de estados. La capa de infraestructura "
        "contiene el ORM, la base de datos, el almacenamiento de archivos y la carga de "
        "variables de entorno.")
    k.figure("04_capas.png",
             "Recorrido horizontal de una petición: URL → middleware/auth → vista → servicio → "
             "modelo → ORM → base de datos → template. Las reglas críticas no viven en el template.", 16.4)
    k.p("La regla de dependencia es unidireccional: presentación → aplicación → dominio → "
        "infraestructura. Una vista puede llamar a un servicio y a un modelo; un modelo no "
        "conoce la vista; un template no consulta la base de datos. Esta disciplina permite "
        "probar el dominio sin levantar el servidor y explicar el sistema sin mezclar capas.")
    k.table("Capa, artefactos y prohibiciones",
            ["Capa", "Artefactos", "Prohibición"],
            [["Presentación", "URLconf, vistas FBV, templates, formularios, CSS/JS", "No decide permisos ni transiciones"],
             ["Aplicación", "Middleware, auth, `role_required`, `trazabilidad.py`, `indicadores.py`", "No renderiza HTML ni arma SQL"],
             ["Dominio", "Modelos, propiedades, `clean()`, `TRANSICIONES`, reglas académicas", "No conoce request ni sesión"],
             ["Infraestructura", "ORM, SQLite/PostgreSQL, `MEDIA_ROOT`, `python-dotenv`", "No contiene reglas de negocio"]],
            widths=[0.7, 1.65, 1.1])

    k.h2("5.5 Ciclo de vida de una petición")
    k.p("Una petición típica recorre ocho pasos. El navegador envía HTTP; el URLconf resuelve "
        "la ruta; el middleware aplica seguridad, sesión y CSRF; el decorador verifica el rol; "
        "la vista construye el contexto y llama al servicio; el servicio aplica la regla y "
        "persiste; el ORM traduce a SQL; el template renderiza la respuesta. Si el servicio "
        "cambia un estado, la transacción incluye la marca temporal y el evento. Si algo falla, "
        "no queda rastro de éxito.")
    k.table("Pasos del recorrido y responsable",
            ["Paso", "Responsable", "Resultado"],
            [["1. HTTP", "Navegador", "Solicitud con sesión y CSRF"],
             ["2. Ruta", "`config/urls.py`, `portal/urls.py`", "Vista identificada"],
             ["3. Seguridad", "Middleware + `role_required`", "Usuario autenticado y autorizado"],
             ["4. Vista", "Función de `portal/views.py`", "Contexto y decisión de flujo"],
             ["5. Servicio", "`trazabilidad.py`, `indicadores.py`", "Regla de dominio aplicada"],
             ["6. Persistencia", "Modelo + ORM", "Estado y evento en una transacción"],
             ["7. Render", "Template", "HTML con datos del alcance"],
             ["8. Respuesta", "Navegador", "Interfaz actualizada"]],
            widths=[0.65, 1.3, 1.4])

    k.h2("5.6 Vistas, formularios y plantillas")
    k.p("Las vistas son funciones (FBV), no clases genéricas. Esa decisión prioriza lectura y "
        "control explícito del flujo sobre la reutilización automática. Hay una vista de detalle "
        "que despacha por rol (`cita_detalle_interactivo`) y renderiza el partial correspondiente; "
        "las demás vistas responden a un portal concreto. Los formularios son `ModelForm` con "
        "validación adicional; las plantillas se organizan en `base.html`, `dashboard_base.html` "
        "y partials por rol. El resultado son 31 plantillas y 14 archivos estáticos, con una "
        "jerarquía que evita duplicar la barra lateral y los estilos de cada portal.")
    k.callout("Decisión de presentación",
              "No se usó una SPA ni DRF. El JSON se reserva para dos endpoints: el calendario y "
              "la reserva. El resto son formularios HTML con CSRF, lo que reduce el estado en el "
              "cliente y mantiene la autorización en el servidor. El costo es una interacción "
              "menos rica; el beneficio es una superficie más pequeña y auditable.", "teal")

    k.h2("5.7 Servicios de dominio")
    k.p("Los servicios son funciones explícitas, no señales. `trazabilidad.py` concentra "
        "`registrar_evento`, `cambio_estado`, `asignar_cita`, `nota_asignacion`, "
        "`auditar_guardado_form`, `registrar_interaccion`, `publicar_entrega`, "
        "`registrar_decision_cliente` e `interacciones_visibles`. `indicadores.py` concentra el "
        "parseo de filtros, los KPI, las métricas de interacción, los promedios, las series y "
        "el CSV. Esa separación permite probar las reglas sin pasar por la interfaz y evita que "
        "una vista o un admin ejecuten una transición por su cuenta.")

    k.h2("5.8 Alternativas descartadas")
    k.table("Alternativas evaluadas y motivo de descarte",
            ["Alternativa", "Ventaja teórica", "Motivo de descarte en CITI"],
            [["Microservicios", "Despliegue independiente por dominio", "Dos personas, diez semanas y necesidad de consistencia transaccional; el costo operativo supera el beneficio"],
             ["SPA + DRF", "Interactividad y separación frontend/backend", "Duplicaría autorización y estado en el cliente; el producto es principalmente formularios"],
             ["Serverless", "Escalado automático y costo por uso", "Complejidad de estado, transacciones y adjuntos; la demo local perdería reproducibilidad"],
             ["Base NoSQL", "Flexibilidad de esquema", "El dominio es relacional y requiere restricciones e integridad referencial"],
             ["Monolito sin módulos", "Menor esfuerzo inicial", "Mezclaría identidad, agenda y presentación; difícil de probar y evolucionar"]],
            widths=[0.75, 1.0, 1.7])

    k.h2("5.9 Atributos de calidad conducidos por la arquitectura")
    k.bullets([
        "**Seguridad:** autenticación por rol, autorización por objeto y área, CSRF, adjuntos servidos por vista autorizada.",
        "**Trazabilidad:** evento append-only por mutación, dentro de la misma transacción; actor congelado en `actor_label`.",
        "**Mantenibilidad:** tres apps, servicios explícitos, 107 pruebas y documentación de decisiones.",
        "**Eficiencia y operabilidad:** consultas acotadas con `select_related`, agregaciones ORM, un comando de arranque y seed idempotente.",
    ])

    # ------------------------------------------------------------------ 6
    k.h1("6. Modelo de dominio y datos")

    k.h2("6.1 Modelo conceptual")
    k.p("El dominio se organiza alrededor de una cita de asesoría. Una empresa agrupa clientes; "
        "un cliente crea una cita sobre una franja horaria; la cita acumula notas de bitácora, "
        "eventos de historial e interacciones con el equipo. Alrededor de esa columna vertebral "
        "aparecen los responsables (docente y estudiante tutor), el perfil académico que habilita "
        "al tutor y las decisiones del cliente sobre los entregables. No hay una entidad "
        "“Solicitud” separada de la cita: la cita es la solicitud y su ciclo de vida es el "
        "estado.")
    k.figure("08_er_real.png",
             "Modelo entidad–relación real. Ocho entidades implementadas; el detalle de campos "
             "y restricciones proviene de accounts/models.py y scheduling/models.py.", 15.8)

    k.h2("6.2 Entidades")
    k.table("Entidades del dominio",
            ["Entidad", "Propósito", "Campos clave"],
            [["`Empresa`", "Organización a la que pertenece un cliente", "`razon_social`, `nit`, `sector`"],
             ["`CustomUser`", "Usuario con email único y rol", "`email`, `role`, `area`, `empresa`, `student_type`"],
             ["`PerfilEstudiante`", "Filtro académico para habilitar tutores", "`semestre`, `creditos_aprobados`, `promedio_general`, `autorizado_como_tutor`"],
             ["`FranjaHoraria`", "Ventana de disponibilidad por área y cupo", "`inicio`, `fin`, `area`, `capacidad`, `activa`"],
             ["`CitaAsesoria`", "Solicitud y su ciclo de vida", "`franja`, `cliente`, `estado`, `docente_asignado`, `estudiante_apoyo`, `asignada_en`, `cerrada_en`"],
             ["`NotaBitacora`", "Registro de apoyo del estudiante", "`cita`, `autor`, `texto`, `creada_en`"],
             ["`CitaEvento`", "Historial append-only de la cita", "`tipo`, `actor_label`, `estado_anterior`, `estado_nuevo`, `metadata`, `fecha`"],
             ["`CitaInteraccion`", "Comentarios, entregas y decisiones", "`tipo`, `rol_autor`, `texto`, `datos_extra`, `para_cliente`"]],
            widths=[0.8, 1.3, 1.5])

    k.h2("6.3 Relaciones y cardinalidades")
    k.table("Relaciones principales",
            ["Relación", "Cardinalidad", "Regla de integridad"],
            [["Empresa–Cliente", "1:N", "Un cliente debe tener empresa (validado en `CustomUser.clean()`)"],
             ["Usuario–PerfilEstudiante", "1:1", "Solo para rol Estudiante; el perfil habilita el tipo tutor"],
             ["Franja–Cita", "1:N", "La franja define área y cupo; `on_delete=CASCADE`"],
             ["Cliente–Cita", "1:N", "Solo clientes; `limit_choices_to` y `clean()`"],
             ["Cita–NotaBitacora", "1:N", "Notas ordenadas por fecha descendente"],
             ["Cita–CitaEvento", "1:N", "Historial ordenado por fecha e id; sin edición desde el portal"],
             ["Cita–CitaInteraccion", "1:N", "Comentarios, entregas y decisiones; visibilidad por tipo"]],
            widths=[0.95, 0.55, 1.8])

    k.h2("6.4 Invariantes y restricciones")
    k.p("Las invariantes son las condiciones que deben cumplirse siempre, incluso si alguien "
        "intenta saltarse la interfaz. Se implementan en tres niveles: validación del modelo "
        "(`clean`/`full_clean`), restricciones de base de datos y servicios transaccionales. "
        "La combinación es deliberada: la base protege la integridad; el modelo explica la "
        "regla; el servicio garantiza que el cambio y su evidencia ocurran juntos.")
    k.table("Invariantes del dominio",
            ["Invariante", "Nivel", "Implementación"],
            [["Un cliente no reserva dos veces la misma franja activa", "Base de datos", "`UniqueConstraint` parcial `unique_cita_activa_por_cliente_franja`"],
             ["La franja termina después de empezar y no se crea en el pasado", "Modelo", "`FranjaHoraria.clean()`"],
             ["El cupo disponible nunca es negativo", "Modelo", "`cupos_disponibles = max(0, capacidad - ocupados)`"],
             ["Un docente pertenece al área o es mixto", "Modelo", "`CitaAsesoria.clean()`"],
             ["Un tutor cumple los umbrales académicos", "Modelo + señal", "`PerfilEstudiante.save()`, `post_save`"],
             ["Una consultoría especializada tiene docente antes de avanzar", "Modelo + servicio", "`clean()` y `asignar_cita`"],
             ["Solo se aplican transiciones legales", "Dominio", "`TRANSICIONES` y `transicion_legal()`"],
             ["Una nota interna no es visible al cliente", "Modelo + consulta", "`CitaInteraccion.save()`, `interacciones_visibles`"]],
            widths=[1.25, 0.65, 1.55])
    k.callout("Por qué hay una restricción parcial",
              "La unicidad no es “una cita por franja y cliente para siempre”, porque un cliente "
              "puede volver a reservar si canceló. La condición `estado in (solicitada, asignada, "
              "en_proceso)` permite el historial y bloquea el doble cupo activo. Es una regla de "
              "negocio expresada en la base, no un parche de vista.", "green")

    k.h2("6.5 Máquina de estados")
    k.p("El estado de una cita solo puede avanzar por las aristas definidas. La tabla formal "
        "incluye una única arista hacia atrás: `finalizada → en_proceso`, habilitada únicamente "
        "cuando el cliente solicita ajustes sobre un entregable. No existe un retroceso manual "
        "del equipo. Esa restricción evita dos problemas frecuentes: reabrir un caso por "
        "conveniencia y perder la fecha real de cierre.")
    k.figure("07_estados.png",
             "Máquina de estados de CitaAsesoria. Las transiciones se validan en el dominio y "
             "se registran como eventos con estado anterior y nuevo.", 14.2)
    k.table("Tabla formal de transiciones",
            ["Estado actual", "Estados permitidos", "Observación"],
            [["`solicitada`", "`asignada`, `cancelada`", "El cliente puede cancelar antes de que haya responsable"],
             ["`asignada`", "`en_proceso`, `finalizada`, `cancelada`, `asignada`", "Reasignación permitida; el cierre directo existe para casos resueltos en la asignación"],
             ["`en_proceso`", "`finalizada`, `cancelada`", "Cierre operativo"],
             ["`finalizada`", "`en_proceso`", "Única reapertura: ajuste solicitado por el cliente"],
             ["`cancelada`", "—", "Estado terminal"]],
            widths=[0.75, 1.35, 1.4])

    k.h2("6.6 Índices y rendimiento de datos")
    k.p("Los índices responden a las consultas reales: agenda por rango de fechas, historial por "
        "cita y fecha, interacciones por cita y tipo, y eventos por fecha. No se indexa “por si "
        "acaso”: cada índice tiene una consulta que lo justifica. Las vistas usan "
        "`select_related` para cliente, empresa, franja y responsables, y agregaciones ORM para "
        "los tableros. El detalle de consultas por vista se presenta en el capítulo 9.")
    k.table("Índices declarados",
            ["Modelo", "Índice", "Consulta que lo usa"],
            [["`FranjaHoraria`", "`(inicio, fin)`", "Agenda y disponibilidad"],
             ["`CitaEvento`", "`(cita, fecha)` y `fecha`", "Historial y actividad reciente"],
             ["`CitaInteraccion`", "`(cita, tipo)`", "Entregas, decisiones y métricas"],
             ["`CitaAsesoria`", "Constraint parcial + FK indexadas", "Reserva activa y filtros por estado/área"]],
            widths=[0.9, 1.1, 1.4])

    k.h2("6.7 Ciclo de vida del dato")
    k.p("Una cita nace en `solicitada`, recibe responsable en `asignada`, se ejecuta en "
        "`en_proceso` y termina en `finalizada` o `cancelada`. El historial no se borra: se "
        "conserva como evidencia. Las notas de bitácora y las interacciones se agregan, no se "
        "sobrescriben. Los adjuntos se guardan en `media/documentos_citas/<año>/<mes>/` y se "
        "sirven por una vista autorizada. Esa política permite responder qué pasó sin depender "
        "de la memoria de los participantes y sin exponer archivos por URL directa.")
