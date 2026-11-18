"""Referencias y anexos del documento maestro."""


def build(k):
    # ------------------------------------------------------------- refs
    k.h1("Referencias")
    refs = [
        "Bass, L., Clements, P. y Kazman, R. (2021). *Software Architecture in Practice* (4.ª ed.). Addison-Wesley.",
        "Brown, S. (2018). *The C4 Model for Visualising Software Architecture*. Leanpub.",
        "Django Software Foundation. (2026). *Django 5.2 Documentation*. https://docs.djangoproject.com/",
        "Fowler, M. (2002). *Patterns of Enterprise Application Architecture*. Addison-Wesley.",
        "Gamma, E., Helm, R., Johnson, R. y Vlissides, J. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley.",
        "International Organization for Standardization. (2011). *ISO/IEC 25010:2011. Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models*.",
        "PlantUML. (2024). *PlantUML Language Reference Guide*. https://plantuml.com/",
        "Pressman, R. y Maxim, B. (2020). *Software Engineering: A Practitioner's Approach* (9.ª ed.). McGraw-Hill.",
        "Sommerville, I. (2016). *Software Engineering* (10.ª ed.). Pearson.",
        "Universidad Cooperativa de Colombia. (2026). *Guía de sustentación · Arquitectura y Modelamiento de Software*. Presentacion final/.",
    ]
    for ref in refs:
        k.p(ref, align="left", space_after=4)

    # ------------------------------------------------------------- A
    k.h1("Anexo A. Catálogo de rutas y APIs")
    k.p("El sistema expone 26 rutas: 20 del portal, 3 de cuentas, 2 de la agenda y 1 del admin. "
        "Todas las rutas privadas exigen sesión; las que además tienen rol se protegen con "
        "`role_required`. La tabla siguiente es el contrato de navegación del sistema.")
    k.table("Rutas implementadas",
            ["Método", "Ruta", "Vista", "Acceso"],
            [["GET", "`/`", "`landing`", "Público"],
             ["GET/POST", "`/cuenta/login/`", "`login_view`", "Público"],
             ["GET/POST", "`/cuenta/registro/`", "`register_cliente`", "Público"],
             ["POST", "`/cuenta/logout/`", "`logout_view`", "Autenticado"],
             ["GET", "`/panel/director/`", "`director_dashboard`", "Director"],
             ["GET", "`/panel/trazabilidad/`", "`trazabilidad`", "Director / Coordinador"],
             ["GET", "`/panel/trazabilidad/exportar.csv`", "`trazabilidad_csv`", "Director / Coordinador"],
             ["GET", "`/panel/coordinador/`", "`coordinador_dashboard`", "Coordinador"],
             ["GET/POST", "`/panel/coordinador/asignar/<id>/`", "`coordinador_asignar`", "Coordinador"],
             ["GET", "`/panel/docente/`", "`docente_dashboard`", "Docente"],
             ["GET/POST", "`/panel/docente/caso/<id>/`", "`docente_caso_detalle`", "Docente"],
             ["GET", "`/panel/docente/caso/<id>/acta/`", "`docente_generar_acta`", "Docente"],
             ["GET", "`/panel/estudiante/`", "`estudiante_dashboard`", "Estudiante"],
             ["POST", "`/panel/estudiante/caso/<id>/nota/`", "`estudiante_caso_nota`", "Estudiante"],
             ["GET", "`/panel/cliente/`", "`cliente_dashboard`", "Cliente"],
             ["GET", "`/panel/cliente/mis-solicitudes/`", "`cliente_mis_solicitudes`", "Cliente"],
             ["GET/POST", "`/panel/cliente/solicitud/<id>/seguimiento/`", "`cliente_seguimiento`", "Cliente"],
             ["GET", "`/panel/cliente/notificaciones/`", "`cliente_notificaciones`", "Cliente"],
             ["GET/POST", "`/panel/cliente/feedback/<id>/`", "`cliente_feedback`", "Cliente"],
             ["GET/POST", "`/panel/perfil/`", "`perfil_propio`", "Autenticado"],
             ["GET", "`/panel/seguimiento/`", "`staff_seguimiento`", "Docente / Coordinador / Director"],
             ["GET", "`/panel/cita/<id>/adjunto/`", "`cita_adjunto`", "Autenticado con alcance"],
             ["GET/POST", "`/panel/cita/<id>/detalle/`", "`cita_detalle_interactivo`", "Autenticado con alcance"],
             ["GET", "`/agenda/api/eventos/`", "`calendario_eventos_api`", "Autenticado"],
             ["POST", "`/agenda/api/reservar/`", "`reservar_cita_api`", "Cliente"],
             ["GET", "`/admin/`", "Admin Django", "Staff"]],
            widths=[0.55, 1.75, 1.2, 0.9])

    # ------------------------------------------------------------- B
    k.h1("Anexo B. Matriz de trazabilidad requisito → código → prueba")
    k.p("La matriz permite verificar que ningún requisito crítico quedó sin implementación o "
        "sin prueba. Las rutas y los nombres de prueba corresponden al repositorio; cuando una "
        "regla se cubre en varias clases, se indica la más representativa.")
    k.table("Trazabilidad de requisitos",
            ["Requisito", "Implementación", "Prueba"],
            [["RF-01 Registro de clientes", "`accounts/views.py`, `CustomUser.clean()`", "`RegistroValidacionTests`"],
             ["RF-02 Login por portal", "`RoleLoginForm`, `login_view`", "`RoleAccessMatrixTests`"],
             ["RF-03 Landing", "`portal.views.landing`", "`NavegacionRegresionF4Tests`"],
             ["RF-04 Agenda", "`FranjaHoraria`, `calendario_eventos_api`", "`ReservasApiTests`"],
             ["RF-05 Reserva atómica", "`reservar_cita_api`", "`ReservasApiTests`"],
             ["RF-06 Seguimiento cliente", "`cliente_mis_solicitudes`, `cliente_seguimiento`", "`SeguimientoClienteTests`"],
             ["RF-07 Cancelación", "`puede_cancelar_cliente`, `cambio_estado`", "`CancelacionI4AdjuntoI3Tests`"],
             ["RF-08 Comentarios", "`CitaInteraccion`, `registrar_interaccion`", "`InteraccionComentariosTests`"],
             ["RF-09 Entregables", "`publicar_entrega`, `registrar_decision_cliente`", "`AprobacionesEntregablesTests`"],
             ["RF-10 Asignación", "`coordinador_asignar`, `asignar_cita`", "`ModalidadesServicioTests`"],
             ["RF-11 Gestión y acta", "`docente_caso_detalle`, `docente_generar_acta`", "`EndToEndDemoTests`"],
             ["RF-12 Bitácora", "`estudiante_caso_nota`, `NotaBitacora`", "`EndToEndDemoTests`"],
             ["RF-13 Indicadores", "`indicadores.py`, `trazabilidad_csv`", "`IndicadoresTests`"],
             ["RF-14 Adjuntos", "`cita_adjunto`", "`CancelacionI4AdjuntoI3Tests`"],
             ["RF-15 Perfil", "`perfil_propio`", "`NavegacionRegresionF4Tests`"],
             ["RNF-02 Trazabilidad", "`CitaEvento`, `cambio_estado`", "`TrazabilidadEventosTests`"],
             ["RNF-05 Mantenibilidad", "3 apps + servicios", "107 pruebas / 18 clases"],
             ["RNF-07 Integridad", "`transaction.atomic`, constraint", "`ReservasApiTests`"]],
            widths=[1.0, 1.45, 1.0])

    # ------------------------------------------------------------- C
    k.h1("Anexo C. Uso de herramientas CASE e IA y su validación")
    k.p("La sustentación exige declarar con qué instrumentos se produjo el análisis y la "
        "documentación. Este anexo responde tres preguntas: qué se usó, para qué se usó y cómo "
        "se validó. La regla de oro fue que ninguna herramienta, humana o automática, se "
        "considerara fuente de verdad por sí sola. La fuente de verdad fue el código en "
        "`backend/` y la suite de pruebas.")

    k.h2("C.1 Herramientas CASE y de composición")
    k.table("Herramientas, productos y validación",
            ["Herramienta", "Producto", "Validación aplicada"],
            [["PlantUML 1.2024.8", "Diagramas de contexto, casos de uso, componentes, capas, secuencias, estados, ER y despliegue", "Renderizado con límite ampliado; revisión visual de cada PNG; fuentes `.puml` versionadas"],
             ["Scripts Python", "`gen_diagrams.py`, `gen_use_cases.py`, `build_deck.py`, `build_guion.py`, `build_doc.py`", "Ejecución reproducible; revisión de salida y dimensiones"],
             ["Pillow", "Composición de paneles de casos de uso y recorte de capturas", "Verificación de tamaño y legibilidad"],
             ["python-pptx", "Presentación de 13 + 3 diapositivas", "Exportación a PDF y revisión de las 16 diapositivas"],
             ["python-docx", "Documento maestro y guion", "Apertura en Word, actualización de índices y exportación a PDF"],
             ["Playwright", "Capturas y recorridos E2E de la demo", "Comparación con el flujo real y revisión de pantallas"],
             ["Word / PowerPoint (COM)", "Exportación fiel a PDF", "Verificación de paginación y diapositivas"],
             ["Git / GitHub", "Control de versiones y respaldo", "Historial de commits y revisión de cambios"]],
            widths=[1.0, 1.55, 1.55])

    k.h2("C.2 Uso de inteligencia artificial")
    k.p("La IA se usó como asistente de redacción y revisión, no como autoridad técnica. Sus "
        "usos concretos fueron: proponer estructura de capítulos y diapositivas; mejorar la "
        "claridad de párrafos; detectar inconsistencias entre el texto y las tablas; sugerir "
        "layouts para los diagramas; y revisar que las cifras citadas coincidieran con la "
        "evidencia. No se usó para inventar datos, para generar lógica de negocio ni para "
        "afirmar capacidades no implementadas.")
    k.table("Usos y controles de la IA",
            ["Uso", "Riesgo", "Control aplicado"],
            [["Redacción y estilo", "Texto fluido pero inexacto", "Contraste con código, pruebas y mediciones"],
             ["Estructura de documentos", "Secciones genéricas o repetidas", "Revisión de pertinencia y eliminación de relleno"],
             ["Diagramas", "Cajas o relaciones inventadas", "Regeneración desde modelos y revisión visual"],
             ["Cifras y métricas", "Valores plausibles pero falsos", "Uso exclusivo de `fase0_metrics.txt` y `fase0_test.txt`"],
             ["Código", "Cambios no revisados", "Ninguna lógica se aceptó sin revisión y suite en verde"]],
            widths=[1.1, 1.2, 1.6])

    k.h2("C.3 Protocolo de validación")
    k.numbered([
        "**Contraste con el código:** cada afirmación sobre modelos, rutas, estados o reglas se verificó en `backend/`.",
        "**Ejecución:** los comandos de `check`, migraciones y pruebas se corrieron en el venv del curso; la salida se guardó como evidencia.",
        "**Revisión visual:** los diagramas y las diapositivas se exportaron y se inspeccionaron uno por uno; se corrigieron desbordes y espacios vacíos.",
        "**Coherencia:** el guion, la presentación y el documento se contrastaron entre sí para que las cifras y los mensajes coincidieran.",
        "**Declaración de límites:** cuando no había evidencia, se escribió “no disponible” o “no implementado”, nunca una estimación presentada como hecho.",
    ])

    k.h2("C.4 Limitaciones del enfoque")
    k.p("El uso de IA acelera la producción de texto, pero también puede introducir errores "
        "difíciles de detectar: una cifra que suena razonable, una relación que no existe o una "
        "promesa de escala sin respaldo. El control humano fue obligatorio y quedó documentado "
        "en este anexo. La herramienta no reemplazó la lectura del código ni la ejecución de las "
        "pruebas; esas dos actividades son la garantía final de que el documento describe el "
        "sistema real.")

    # ------------------------------------------------------------- D
    k.h1("Anexo D. Evidencias de ejecución")
    k.p("Las evidencias se conservan en `docs/sustentacion/evidencias/`. Se ejecutaron el 18 de "
        "noviembre de 2026 en el entorno local del proyecto, con el venv de la raíz y la base "
        "SQLite de desarrollo. La suite crea una base de pruebas aislada; el archivo "
        "`db.sqlite3` no se modifica.")
    k.code("""> ..\\venv\\Scripts\\python.exe manage.py check
System check identified no issues (0 silenced).

> ..\\venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run
No changes detected

> ..\\venv\\Scripts\\python.exe manage.py test
Found 107 test(s).
System check identified no issues (0 silenced).
...........................................................................
----------------------------------------------------------------------
Ran 107 tests in 67.524s

OK
Destroying test database for alias 'default'...""")
    k.table("Resumen de evidencias",
            ["Archivo", "Contenido", "Resultado"],
            [["`fase0_check.txt`", "Salida de `manage.py check`", "0 issues"],
             ["`fase0_makemigrations.txt`", "Verificación de migraciones", "Sin cambios"],
             ["`fase0_test.txt`", "Suite completa", "107/107 OK en 67,524 s"],
             ["`fase0_metrics.txt`", "Mediciones de rutas y consultas", "2,8–28,1 ms"],
             ["`demo_cliente.png`", "Captura del seguimiento del cliente", "Flujo visible"],
             ["`demo_docente.png`", "Captura de la entrega publicada", "Flujo visible"],
             ["`demo_director.png`", "Captura de trazabilidad e indicadores", "Flujo visible"]],
            widths=[1.2, 1.7, 1.0])
    k.callout("Reproducibilidad",
              "Los comandos deben ejecutarse desde `backend/` con `..\\venv\\Scripts\\python.exe`. "
              "Ejecutar `python backend/manage.py test` desde la raíz falla por la colisión con el "
              "stub `portal/` de la raíz; no es un defecto del sistema, es una condición del "
              "repositorio que quedó documentada.", "amber")

    # ------------------------------------------------------------- E
    k.h1("Anexo E. Glosario")
    terms = [
        ("ADR", "Architecture Decision Record: registro de una decisión de arquitectura con contexto, alternativas y consecuencias."),
        ("Append-only", "Registro al que solo se agregan entradas; no se edita ni se borra desde el portal."),
        ("Cita de asesoría", "Solicitud concreta sobre una franja, con cliente, estado, responsables y evidencia."),
        ("Cupo", "Número de citas activas que una franja puede admitir."),
        ("Franja horaria", "Ventana de disponibilidad con área, inicio, fin y capacidad."),
        ("IDOR", "Insecure Direct Object Reference: acceso a un objeto ajeno manipulando su identificador."),
        ("MVT", "Model–View–Template: patrón de Django que separa datos, lógica de presentación y plantilla."),
        ("Monolito modular", "Un solo despliegue con fronteras internas explícitas entre módulos."),
        ("ORM", "Object–Relational Mapping: traducción entre objetos y tablas relacionales."),
        ("RBAC", "Role-Based Access Control: control de acceso basado en roles."),
        ("RF / RNF", "Requisito funcional / requisito no funcional."),
        ("Seed", "Conjunto de datos de demostración reproducible e idempotente."),
        ("Servicio de dominio", "Función que aplica una regla de negocio y coordina persistencia y evidencia."),
        ("Trazabilidad", "Capacidad de reconstruir qué pasó, quién lo hizo y cuándo."),
        ("Transición", "Cambio de estado permitido por la tabla formal del dominio."),
        ("UML", "Unified Modeling Language: lenguaje de modelado visual."),
        ("WSGI", "Web Server Gateway Interface: contrato entre servidor web y aplicación Python."),
    ]
    for term, definition in terms:
        k.lead(term + ".", definition, size=10)

    k.p("")
    k.p("— Fin del documento —", align="center", italic=True)
