"""Capítulos 1–3 del documento maestro."""


def build(k):
    # ------------------------------------------------------------------ 1
    k.h1("1. Introducción")
    k.p("Este documento describe la arquitectura del Sistema CITI, el Consultorio de "
        "Ingeniería, Tecnología e Innovación de la Universidad Cooperativa de Colombia, "
        "sede Ibagué – El Espinal. No es un manual de usuario ni una presentación "
        "comercial: es la memoria técnica que explica cómo está construido el sistema, "
        "por qué se tomaron ciertas decisiones, qué evidencia las respalda y qué límites "
        "permanecen abiertos. Su propósito es que un evaluador, un docente o un futuro "
        "desarrollador pueda reconstruir el razonamiento sin depender de la memoria del "
        "equipo.")

    k.h2("1.1 Propósito y alcance del documento")
    k.p("El documento cubre el sistema implementado en el directorio `backend/`: modelos, "
        "vistas, servicios, rutas, configuración, pruebas y despliegue. Incluye los "
        "diagramas definitivos regenerados desde el código, el catálogo de decisiones de "
        "arquitectura (ADR), la evaluación de calidad con ISO/IEC 25010 y la evidencia de "
        "la suite de 107 pruebas automatizadas. No cubre la operación comercial del "
        "consultorio, la facturación, la gestión contractual con empresas ni una "
        "aplicación móvil nativa, porque esas capacidades no forman parte del alcance "
        "implementado.")
    k.p("El documento se apoya en el código como fuente primaria. Cuando una afirmación "
        "depende de una medición, se indica el archivo de evidencia; cuando depende de una "
        "regla de negocio, se indica el modelo o servicio que la implementa; cuando es una "
        "decisión, se indica el ADR correspondiente. Esa disciplina evita dos errores "
        "frecuentes en trabajos de arquitectura: describir un sistema ideal que no existe "
        "y presentar como certeza lo que apenas es una intención.")

    k.h2("1.2 Contexto institucional")
    k.p("El CITI articula tres mundos que normalmente hablan idiomas distintos: la "
        "academia, la empresa y el territorio. La Universidad aporta estudiantes, docentes "
        "y laboratorios; las empresas e instituciones aportan problemas reales; el "
        "territorio aporta necesidades de innovación y transferencia de conocimiento. El "
        "sistema debe hacer visible esa articulación sin convertirla en un directorio de "
        "contactos. Cada solicitud tiene un responsable, un estado, un historial y un "
        "resultado verificable.")
    k.p("El consultorio atiende dos áreas de conocimiento: Ingeniería de Sistemas e "
        "Ingeniería Civil. El catálogo real contiene catorce subespecialidades: cuatro de "
        "Sistemas (bases de datos, desarrollo web, redes y ciberseguridad) y diez de Civil "
        "(concretos, suelos y geotecnia, pavimentos, topografía y SIG, estructuras, "
        "hidráulica, tránsito y transporte, vías, interventoría y planos). El catálogo vive "
        "en `scheduling/subespecialidades.py`; no se alimenta de un archivo de portafolio "
        "externo, porque ese archivo no existe en el repositorio.")
    k.p("Los actores del sistema son cinco: cliente o empresa, estudiante, docente, "
        "coordinador de área y director del CITI. Cada uno tiene un portal, un alcance y un "
        "conjunto de acciones permitidas. La arquitectura no trata esos roles como etiquetas "
        "cosméticas: los convierte en restricciones de servidor. Un coordinador de Sistemas "
        "no puede ver la bandeja de Civil; un docente no puede abrir un caso que no le fue "
        "asignado; un cliente no puede leer una nota interna. Esa es la diferencia entre un "
        "sistema con roles y un sistema con seguridad.")

    k.h2("1.3 Audiencia y convenciones")
    k.p("El documento está dirigido al jurado de la asignatura Arquitectura y Modelamiento "
        "de Software, a los docentes del programa y a quienes deban mantener el sistema "
        "después de la entrega. Se usan las siguientes convenciones:")
    k.bullets([
        "**RF** y **RNF** identifican requisitos funcionales y no funcionales; **BR** identifica reglas de negocio; **ADR** identifica decisiones de arquitectura.",
        "Las figuras y tablas se numeran de forma consecutiva y se referencian en el texto por ese número, no por el nombre del archivo.",
        "El código y las rutas se escriben en `fuente monoespaciada`; los nombres de archivo conservan su ruta relativa al repositorio.",
        "Las afirmaciones de rendimiento provienen de una medición local registrada en `docs/sustentacion/evidencias/fase0_metrics.txt`; no son estimaciones.",
        "Los límites se declaran de forma explícita. Cuando no hay evidencia, se dice “no disponible” en lugar de inferir un valor.",
    ])

    k.h2("1.4 Fuente de verdad y documentación heredada")
    k.p("La fuente de verdad son `backend/accounts/models.py`, `backend/scheduling/models.py`, "
        "`backend/portal/views.py`, `backend/portal/indicadores.py`, "
        "`backend/scheduling/trazabilidad.py` y `backend/portal/tests.py`. Los diagramas se "
        "regeneraron desde esos archivos con PlantUML y las fuentes `.puml` quedaron "
        "versionadas en `docs/sustentacion/fuentes/`.", align="left")
    k.callout("Advertencia sobre documentos heredados",
              "`docs/erd-mermaid.md` describe un esquema planeado (Solicitud, Informe, Firma) "
              "que no coincide con los modelos implementados. El prototipo estático de la raíz "
              "(`app/`, `dashboards/`, `plantillas/`) tampoco representa el sistema Django. "
              "Ninguno de esos artefactos se usa como fuente de verdad en este documento. "
              "El catálogo real de servicios está en `scheduling/subespecialidades.py`; el "
              "archivo `portafolio.py` no existe en el repositorio.", "amber")

    # ------------------------------------------------------------------ 2
    k.h1("2. Problema, objetivos y alcance")

    k.h2("2.1 Situación actual")
    k.p("Antes del sistema, una solicitud al CITI podía nacer en una llamada, un correo o una "
        "conversación de pasillo. A partir de ahí comenzaba una cadena de reenvíos: el "
        "coordinador preguntaba quién podía atender, el docente confirmaba disponibilidad, el "
        "estudiante se enteraba por un tercero y el cliente quedaba sin saber en qué iba su "
        "caso. La información existía, pero estaba dispersa en bandejas personales y hojas de "
        "cálculo. Nadie podía responder con precisión cuatro preguntas básicas: quién es el "
        "responsable, en qué estado está la solicitud, qué se prometió y cómo terminó.")
    k.p("Esa dispersión produce tres síntomas medibles en la operación: solicitudes "
        "duplicadas porque no hay un registro único; citas que se cruzan porque la "
        "disponibilidad no se reserva de forma atómica; y cierres sin evidencia porque el "
        "acta y las observaciones viven en documentos sueltos. El problema no se resuelve "
        "agregando una pantalla bonita al final de la cadena. Se resuelve modelando el ciclo "
        "de vida completo y poniendo las reglas en el servidor.")

    k.h2("2.2 Problema central")
    k.p("El CITI necesita una plataforma que haga **confiable** la relación entre la "
        "Universidad y sus usuarios: que garantice identidad y alcance por rol, que aplique "
        "reglas académicas y operativas de forma consistente, y que deje evidencia "
        "verificable de cada decisión. La confianza no es un atributo decorativo; es el "
        "requisito que explica la arquitectura. De él se derivan la autenticación por rol, "
        "la tabla formal de transiciones, el registro append-only de eventos y la separación "
        "entre estado, interacción y decisión.")

    k.h2("2.3 Objetivo general")
    k.p("Diseñar e implementar una arquitectura modular para el CITI que permita gestionar "
        "solicitudes de asesoría y consultoría desde su creación hasta su cierre, con control "
        "de acceso por rol, trazabilidad transaccional y evidencia verificable, en un contexto "
        "de equipo pequeño y recursos limitados.")

    k.h2("2.4 Objetivos específicos")
    k.numbered([
        "Modelar el dominio del consultorio con entidades, relaciones, estados y reglas que reflejen la operación real de las áreas de Sistemas y Civil.",
        "Implementar un monolito modular en Django que separe presentación, aplicación, dominio e infraestructura, sin duplicar reglas en las plantillas.",
        "Garantizar el acceso por rol y por área, incluyendo la protección de objetos contra referencias directas no autorizadas (IDOR).",
        "Registrar cada mutación relevante en un historial append-only, dentro de la misma transacción que cambia el estado.",
        "Calcular indicadores de gestión y exportarlos a CSV con el mismo criterio con el que se muestran en pantalla.",
        "Verificar el comportamiento con una suite automatizada y documentar las decisiones, los límites y la ruta de evolución.",
    ])

    k.h2("2.5 Alcance implementado y exclusiones")
    k.table("Alcance del sistema CITI en la entrega final",
            ["Incluido", "Excluido (declarado)"],
            [["Landing institucional y login por rol", "Portal público de noticias o blog"],
             ["Registro público de clientes con empresa", "Facturación, pagos o pasarela"],
             ["Agenda por franjas, cupos y reserva atómica", "Sincronización con Google Calendar"],
             ["Asignación de docente y tutor por coordinación", "Asignación automática por algoritmo"],
             ["Máquina de estados formal y trazabilidad append-only", "Flujo BPMN configurable por el usuario"],
             ["Seguimiento, comentarios, entregables y aprobaciones", "Firma electrónica certificada"],
             ["Dashboard ejecutivo, indicadores y CSV", "Business intelligence externo"],
             ["Adjuntos con descarga autorizada", "Antivirus o DLP sobre archivos"],
             ["Panel de perfil y notificaciones internas", "Notificaciones push o correo transaccional"],
             ["Documentación, diagramas y 107 pruebas", "Aplicación móvil nativa"]],
            widths=[1.15, 1.0])

    k.h2("2.6 Restricciones y supuestos")
    k.table("Restricciones del proyecto",
            ["Restricción", "Consecuencia arquitectónica"],
            [["Equipo de dos personas", "Se prioriza un solo despliegue y código explícito sobre infraestructura distribuida."],
             ["Diez semanas de trabajo académico", "Se congelan funcionalidades y se protege la demo; la deuda se documenta."],
             ["Sin presupuesto de infraestructura", "SQLite en local, media local y servicios gratuitos; PostgreSQL queda listo por configuración."],
             ["Django 5.x como stack del curso", "Monolito MVT, ORM y admin; sin DRF ni SPA."],
             ["Demo reproducible en Windows", "Venv raíz, `runserver`, `seed_demo` idempotente y pruebas en base aislada."],
             ["Evaluación con jurado", "Se privilegia la evidencia verificable sobre las promesas de escala."]],
            widths=[0.8, 1.5])
    k.p("Supuestos: el CITI opera en una sola sede; los clientes son personas jurídicas o "
        "naturales vinculadas a una empresa; la asignación de responsable es una decisión "
        "humana del coordinador; y la disponibilidad se publica por franjas, no por "
        "calendario individual de cada docente.")

    k.h2("2.7 Criterios de éxito")
    k.p("La entrega se considera exitosa si un evaluador puede recorrer los cinco portales, "
        "comprobar que cada rol ve solo lo que le corresponde, seguir una solicitud desde "
        "`solicitada` hasta `finalizada`, ver el historial de eventos y exportar los "
        "indicadores. Además, la suite debe pasar completa en una base aislada, el sistema "
        "debe arrancar con un comando y la documentación debe permitir reconstruir las "
        "decisiones sin acceso a los autores. Los criterios cuantitativos son: 107 pruebas "
        "en verde, cero errores de `check`, cero migraciones pendientes y una demo de menos "
        "de dos minutos que cubra cliente, docente y director.")

    # ------------------------------------------------------------------ 3
    k.h1("3. Metodología y proceso de arquitectura")

    k.h2("3.1 Enfoque")
    k.p("El proyecto se trabajó con un proceso iterativo e incremental, centrado en "
        "arquitectura y guiado por evidencia. Cada iteración produjo tres cosas: una porción "
        "del sistema funcionando, un artefacto de documentación y una prueba que la respalda. "
        "No se dibujó primero un modelo perfecto para después implementarlo; se modeló, se "
        "implementó, se auditó y se corrigió. Esa dinámica explica por qué el modelo final "
        "difiere del modelado inicial y por qué esa diferencia se muestra con honestidad en "
        "la sustentación.")
    k.p("El proceso combinó ideas de arquitectura centrada en atributos de calidad (Bass, "
        "Clements y Kazman) con la práctica de documentar decisiones mediante ADR. La "
        "pregunta rectora no fue “¿qué patrón nos gusta?”, sino “¿qué decisión nos permite "
        "sostener seguridad, trazabilidad y mantenibilidad con dos personas y diez semanas?”. "
        "Las alternativas se evaluaron por su costo operativo, no por su popularidad.")

    k.h2("3.2 Fases del proyecto")
    k.table("Fases S1–S16 y productos verificables",
            ["Fase", "Objetivo", "Productos", "Criterio de salida"],
            [["S1–S5", "Modelado inicial", "Actores, casos de uso, clases, ERD y arquitectura propuesta", "Modelo comprensible y validado en clase"],
             ["S6–S10", "Implementación base", "Django MVT, login, agenda, reservas, seed y 42 pruebas", "Flujo principal funcionando"],
             ["S11–S13", "Trazabilidad", "CitaEvento, servicios, dashboard ejecutivo e indicadores", "Historial y métricas consistentes"],
             ["S14–S16", "Interacción y cierre", "CitaInteraccion, entregables, aprobaciones, adjuntos y 107 pruebas", "Flujo completo por rol y evidencia E2E"]],
            widths=[0.55, 0.9, 1.5, 1.05])
    k.p("Las fases no fueron un cronograma rígido. La auditoría de cierre detectó bloqueantes "
        "que obligaron a reabrir decisiones: el seed que se ejecutaba solo, el login que no "
        "distinguía portal, los eventos duplicados y la reapertura de casos. Corregirlos no "
        "fue un retroceso; fue la parte más valiosa del proceso, porque cada corrección quedó "
        "acompañada de una prueba de regresión.")

    k.h2("3.3 Artefactos")
    k.bullets([
        "**Código:** tres apps Django (`accounts`, `scheduling`, `portal`) y un proyecto de configuración (`config`).",
        "**Diagramas:** contexto C4, casos de uso por actor, componentes, capas, dos secuencias, estados, ER y despliegue, con fuentes PlantUML versionadas.",
        "**Decisiones:** diez ADR con contexto, alternativas, decisión, consecuencias y evidencia.",
        "**Pruebas:** 107 pruebas en 18 clases, organizadas por riesgo y por flujo.",
        "**Evidencia:** salidas de `check`, `makemigrations`, `test`, métricas de consultas y capturas de la demo.",
        "**Documentación:** este documento, el guion de sustentación y la presentación de 13 diapositivas más respaldo.",
    ])

    k.h2("3.4 Herramientas")
    k.table("Herramientas utilizadas y función",
            ["Herramienta", "Uso", "Validación"],
            [["Django 5.2", "Framework web, ORM, admin, autenticación", "`manage.py check` y 107 pruebas"],
             ["SQLite / PostgreSQL", "Persistencia local y configuración de producción", "Migraciones y pruebas en base aislada"],
             ["PlantUML 1.2024.8", "Diagramas UML y C4 desde texto", "Fuentes `.puml` versionadas y revisión visual"],
             ["Python 3 + Pillow", "Composición de paneles y recorte de imágenes", "Revisión de dimensiones y legibilidad"],
             ["python-pptx / python-docx", "Generación de presentación y documento", "Exportación a PDF y revisión de diapositivas"],
             ["Playwright", "Recorridos E2E y capturas de la demo", "Evidencia visual de los flujos"],
             ["Git / GitHub", "Control de versiones y respaldo", "Historial de commits"],
             ["Word / PowerPoint (COM)", "Exportación fiel a PDF", "Verificación de páginas y diapositivas"]],
            widths=[0.75, 1.25, 1.0])

    k.h2("3.5 Puertas de calidad")
    k.p("Cada cierre de iteración exigió cuatro verificaciones. Primero, `manage.py check` sin "
        "errores. Segundo, `makemigrations --check --dry-run` sin cambios pendientes. Tercero, "
        "la suite completa en verde sobre una base de pruebas aislada. Cuarto, una revisión "
        "manual en navegador de los flujos afectados, incluyendo responsive y estados vacíos. "
        "Si una puerta fallaba, no se avanzaba. Esa disciplina es la razón por la que la "
        "entrega puede afirmar 107 pruebas y cero migraciones pendientes sin matices.")
    k.code("""cd backend
..\\venv\\Scripts\\python.exe manage.py check
..\\venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run
..\\venv\\Scripts\\python.exe manage.py test
..\\venv\\Scripts\\python.exe manage.py seed_demo""")

    k.h2("3.6 Trazabilidad metodológica")
    k.p("Cada requisito relevante se puede seguir en tres saltos: una regla o vista que lo "
        "implementa, una prueba que lo verifica y una evidencia que lo demuestra. Por ejemplo, "
        "la regla “un cliente no puede reservar dos veces la misma franja” se implementa en la "
        "restricción `unique_cita_activa_por_cliente_franja`, se verifica en "
        "`ReservasApiTests` y se evidencia con la respuesta 409 de la API. Esa cadena evita "
        "que la documentación se convierta en una lista de buenas intenciones.")

    k.h2("3.7 Documentación heredada y decisiones de honestidad")
    k.p("El repositorio conserva artefactos de etapas anteriores: un ERD planeado en Mermaid, "
        "un prototipo estático y capturas del modelado inicial. Se conservan por valor "
        "histórico, no porque sean normativos. La regla de trabajo fue simple: si un artefacto "
        "no coincide con el código, se corrige o se marca como heredado; nunca se presenta "
        "como vigente. Esa decisión explica el anexo sobre herramientas CASE e IA: la "
        "trazabilidad incluye los instrumentos de producción documental.")
