"""Capítulos 7–9 del documento maestro."""


def build(k):
    # ------------------------------------------------------------------ 7
    k.h1("7. Comportamiento, trazabilidad e interacción")

    k.h2("7.1 Flujo de reserva")
    k.p("La reserva es el punto de entrada operativo y el lugar donde la concurrencia se vuelve "
        "visible. El cliente elige una franja en el calendario; el navegador envía el id de la "
        "franja y los datos mínimos; la vista valida método, autenticación y rol; el servicio "
        "abre una transacción, bloquea la franja con `select_for_update`, verifica cupo y "
        "duplicados, crea la cita y registra el evento. Si dos clientes intentan el último cupo "
        "al mismo tiempo, solo uno obtiene 200; el otro recibe 409 con un mensaje comprensible.")
    k.figure("05_secuencia_reserva.png",
             "Secuencia real de reserva. El flujo tiene 19 pasos, usa transaction.atomic y "
             "select_for_update sobre la franja, y devuelve 200 o 409 según el resultado.", 15.6)

    k.h2("7.2 Concurrencia y consistencia")
    k.p("La API de reserva no confía en el estado que muestra el calendario. Vuelve a leer la "
        "franja dentro de la transacción y bloquea la fila antes de contar cupos. Esa doble "
        "verificación es necesaria porque entre el render y el clic pueden pasar segundos y "
        "otro cliente puede haber reservado. La restricción única parcial es la última red: "
        "aunque dos requests pasaran la validación lógica, la base rechaza la segunda reserva "
        "activa del mismo cliente en la misma franja.")
    k.table("Respuestas de la API de reserva",
            ["Situación", "HTTP", "Efecto"],
            [["Reserva exitosa", "200", "Cita `solicitada` + evento `creada`"],
             ["Sin cupo o franja no disponible", "409", "Sin cambios; mensaje de conflicto"],
             ["Datos inválidos o falta de sesión", "400 / 302", "Sin cambios; redirección o error de validación"],
             ["Error inesperado", "500", "La transacción revierte; no queda cita ni evento"]],
            widths=[1.2, 0.55, 1.45])

    k.h2("7.3 Registro append-only de eventos")
    k.p("`CitaEvento` es el historial auditable de la solicitud. No se edita ni se borra desde "
        "el portal; se crea únicamente a través de `scheduling/trazabilidad.py`. Cada evento "
        "guarda el tipo, el actor (`usuario` y `actor_label`), el estado anterior y nuevo, una "
        "descripción, metadatos JSON y la fecha. `actor_label` conserva el correo aunque el "
        "usuario se elimine después; esa decisión evita que el historial pierda sentido cuando "
        "cambia la planta de personal.")
    k.table("Tipos de evento y uso",
            ["Tipo", "Cuándo se registra"],
            [["`creada`", "El cliente reserva una cita"],
             ["`revisada`", "El coordinador abre la solicitud por primera vez"],
             ["`docente_asignado` / `tutor_asignado`", "Se asigna un responsable"],
             ["`asignada`", "La cita pasa a estado `asignada`"],
             ["`iniciada`", "La cita pasa a `en_proceso`"],
             ["`estado_cambiado`", "Cambio de estado desde gestión del caso"],
             ["`archivo_adjuntado`", "Se adjunta documentación base"],
             ["`finalizada` / `acta_registrada`", "Cierre operativo y acta"],
             ["`feedback`", "El cliente califica el cierre"],
             ["`cancelada`", "Cancelación por cliente o equipo"],
             ["`bitacora`", "Nota de apoyo del estudiante"],
             ["`interaccion`", "Comentario, observación o nota interna"],
             ["`entrega_publicada`", "Se publica un entregable"],
             ["`decision_cliente`", "Aprobación o solicitud de ajustes"]],
            widths=[1.2, 2.0])

    k.h2("7.4 Secuencia de trazabilidad")
    k.p("La secuencia de trazabilidad muestra el patrón que se repite en todo el sistema: la "
        "vista no escribe el evento por su cuenta; llama a un servicio; el servicio valida, "
        "cambia el estado, actualiza las marcas temporales y registra el evento dentro de la "
        "misma transacción. Si la validación falla, la excepción revierte el conjunto. Esa es "
        "la diferencia entre “registrar un log” y “garantizar evidencia”.")
    k.figure("06_secuencia_trazabilidad.png",
             "Secuencia de un cambio de estado auditado. El evento y el estado comparten "
             "transacción; una falla no deja evidencia de éxito.", 15.4)

    k.h2("7.5 Interacciones, entregables y decisiones")
    k.p("`CitaInteraccion` separa la conversación del estado. Un comentario no cambia el estado; "
        "una entrega no cierra el caso; una aprobación no finaliza la cita. Esa separación evita "
        "que la bandeja de estados se convierta en un chat y que el chat se convierta en la "
        "única fuente de verdad. Cada interacción tiene un tipo, un autor con rol congelado y "
        "una bandera `para_cliente`; las notas internas siempre son privadas.")
    k.table("Tipos de interacción",
            ["Tipo", "Autor permitido", "Visible al cliente", "Uso"],
            [["`general`", "Cliente", "Sí", "Comentario general del cliente"],
             ["`respuesta`", "Cliente", "Sí", "Respuesta a una observación"],
             ["`aprobacion`", "Cliente", "Sí", "Acepta el entregable"],
             ["`rechazo_ajuste`", "Cliente", "Sí", "Solicita correcciones"],
             ["`observacion`", "Equipo", "Sí", "Observación del profesional"],
             ["`ajuste`", "Equipo", "Sí", "Solicitud de ajuste al cliente"],
             ["`entrega_resultados`", "Equipo", "Sí", "Publica el entregable"],
             ["`nota_interna`", "Equipo", "No", "Nota técnica privada"]],
            widths=[1.0, 0.8, 0.6, 1.0])

    k.h2("7.6 Reglas de decisión y reapertura")
    k.p("El cliente solo puede decidir si hay una entrega pendiente. Aprobar registra una "
        "interacción y un evento, pero no toca el estado. Pedir ajustes registra la decisión y, "
        "si el caso estaba `finalizada`, lo devuelve a `en_proceso`: es la única arista de "
        "reapertura de la tabla. En cualquier otro estado activo, el estado se conserva. Esa "
        "regla evita dos extremos: cerrar automáticamente por una aprobación y reabrir por "
        "cualquier comentario.")
    k.callout("Decisión de diseño",
              "Aprobar un entregable no finaliza la cita. El cierre es una decisión "
              "administrativa distinta, con acta y resumen; la aprobación es una decisión sobre "
              "el entregable. Separarlas permite auditar ambas y evita cierres accidentales.", "green")

    k.h2("7.7 Caso narrado: la solicitud 17")
    k.p("La solicitud 17 del conjunto demo permite recorrer el sistema de punta a punta. El "
        "cliente la creó sobre una franja de Sistemas; el coordinador la revisó y asignó docente "
        "y tutora; el docente la pasó a `en_proceso` y publicó una entrega; el cliente comentó "
        "y pidió un ajuste. En el portal del cliente se ve la línea de tiempo, el entregable "
        "pendiente y el historial. En el portal del docente se ve la ficha, la entrega y los "
        "eventos. En el portal del director se ven los KPI, la evolución y el CSV. Es el mismo "
        "registro visto desde tres alcances distintos, no tres copias de la información.")

    # ------------------------------------------------------------------ 8
    k.h1("8. Seguridad y control de acceso")

    k.h2("8.1 Modelo de amenazas")
    k.p("El activo principal no es la base de datos: es la confianza en el historial. Un "
        "atacante podría intentar leer casos de otra área, modificar un estado sin dejar rastro, "
        "descargar un adjunto ajeno o suplantar un rol. El modelo de amenazas se organizó con "
        "STRIDE y se tradujo en controles verificables. La tabla siguiente resume las amenazas "
        "prioritarias y su mitigación.")
    k.table("Amenazas y controles",
            ["Amenaza", "Escenario", "Control"],
            [["Spoofing", "Entrar con un rol que no corresponde", "Login con `expected_role`, sesión y rechazo de portal incorrecto"],
             ["Tampering", "Cambiar un estado por URL o formulario", "Transiciones formales y servicios auditados"],
             ["Repudiation", "Negar una acción", "`CitaEvento` con actor y fecha; append-only"],
             ["Information disclosure", "Leer un caso o adjunto ajeno", "Filtros por propietario/área; vista autorizada de adjuntos"],
             ["Denial of service", "Saturar la reserva o el login", "Validación temprana; límite de prueba no implementado (declarado)"],
             ["Elevation of privilege", "Coordinador de un área operando en otra", "`area_forzada` en servidor; matriz de roles"]],
            widths=[0.9, 1.25, 1.65])

    k.h2("8.2 Autenticación")
    k.p("El usuario se autentica con email y contraseña. `CustomUser` extiende `AbstractBaseUser` "
        "y usa `email` como `USERNAME_FIELD`; el manager crea usuarios normales y superusuarios "
        "sin nombre de usuario. El login es consciente del rol: el formulario envía un "
        "`expected_role` oculto y rechaza la autenticación si el rol real no coincide, con el "
        "mensaje “Esta cuenta pertenece al portal …”. Las rutas `/cuenta/login/?rol=<role>` "
        "preseleccionan el portal. Esa decisión mejora la experiencia de aula, pero revela el "
        "portal real de una cuenta; se documenta como riesgo residual (SEG-14).")
    k.p("Las contraseñas se validan con los cuatro validadores de Django: similitud con datos "
        "personales, longitud mínima, contraseñas comunes y contraseñas numéricas. En producción "
        "se activan cookies seguras, `SECURE_SSL_REDIRECT`, HSTS, `X_FRAME_OPTIONS=DENY` y "
        "`SECURE_CONTENT_TYPE_NOSNIFF`. En desarrollo se mantiene HTTP local para no romper la "
        "demo, y esa diferencia se controla con `DJANGO_ENV`.")

    k.h2("8.3 Autorización por rol y por objeto")
    k.p("La autorización tiene dos capas. La primera es de ruta: `role_required` verifica que el "
        "usuario tenga uno de los roles permitidos. La segunda es de objeto: la vista filtra el "
        "queryset por propietario, área o asignación antes de responder. Un docente no puede "
        "abrir un caso que no le pertenece aunque conozca el id; un coordinador no puede ver la "
        "bandeja de la otra área; un cliente no puede leer una nota interna. Las pruebas de IDOR "
        "verifican que el sistema responda 404 o 403 sin filtrar datos.")
    k.table("Matriz de acceso por rol",
            ["Rol", "Landing / login", "Mis solicitudes", "Detalle del caso", "Asignar", "Trazabilidad", "Admin"],
            [["Cliente", "✓", "Solo propias", "Solo propias", "—", "—", "—"],
             ["Estudiante", "✓", "Casos de apoyo", "Solo asignados", "—", "—", "—"],
             ["Docente", "✓", "Casos asignados", "Solo asignados", "—", "—", "—"],
             ["Coordinador", "✓", "Bandeja del área", "Solo su área", "Sí, su área", "Solo su área", "—"],
             ["Director", "✓", "Global", "Global (lectura)", "—", "Global", "Si es staff"]],
            widths=[0.7, 0.75, 0.85, 0.9, 0.7, 0.8, 0.65], align_center=True)
    k.p("El coordinador tiene un `area_forzada` que se aplica en `parse_filtros` antes de "
        "cualquier consulta. Aunque manipule el parámetro `area` en la URL, el servidor conserva "
        "su área. El director no está limitado por área, pero su rol es de lectura ejecutiva: no "
        "asigna ni ejecuta casos. El admin de Django es una herramienta administrativa para "
        "staff, no el dashboard del director.")

    k.h2("8.4 Controles técnicos")
    k.bullets([
        "**CSRF:** todas las formas usan `{% csrf_token %}` y el middleware correspondiente; las APIs reciben el token en la sesión.",
        "**XSS:** las plantillas escapan por defecto; no se usa `|safe` sobre contenido de usuario.",
        "**Clickjacking:** `X_FRAME_OPTIONS=DENY` en producción.",
        "**Transporte:** redirección SSL, HSTS y cookies seguras cuando `DJANGO_ENV=produccion`.",
        "**Archivos:** los adjuntos se descargan por `cita_adjunto`, que verifica rol y alcance; no se enlaza `archivo_adjunto.url`.",
        "**Auditoría:** los eventos no se editan ni se borran desde el portal; el admin es de solo lectura para el historial.",
        "**Integridad:** `transaction.atomic` y `select_for_update` en reserva; constraint parcial para doble reserva.",
    ])

    k.h2("8.5 Seguridad del admin")
    k.p("El admin tiene dos rieles. Primero, `CitaAsesoria` no se puede eliminar para usuarios no "
        "superusuarios, porque borrar la cita borraría su historial. Segundo, los cambios de "
        "estado desde el admin se enrutan por `cambio_estado`, de modo que emiten evento y "
        "respetan la tabla de transiciones. El director demo es `is_staff` con permisos de "
        "dominio concedidos por el seed, no superusuario. Esa decisión reduce el poder de la "
        "cuenta de demostración y evita que un accidente borre evidencia.")

    k.h2("8.6 Hallazgos y límites declarados")
    k.p("La auditoría de cierre dejó hallazgos que se corrigieron (login por portal, seed "
        "explícito, eventos duplicados, reapertura, adjuntos) y otros que se declaran como "
        "límites: el login revela el portal real de una cuenta (SEG-14); no hay segundo factor; "
        "no hay límite de intentos ni rate limiting; las cuentas demo comparten contraseña y "
        "deben desactivarse fuera del aula; no hay antivirus sobre adjuntos; y la media local no "
        "está protegida por CDN ni por almacenamiento de objetos. Ninguno de esos límites se "
        "presenta como resuelto.")

    # ------------------------------------------------------------------ 9
    k.h1("9. Calidad y evaluación ISO/IEC 25010")

    k.h2("9.1 Modelo de calidad")
    k.p("ISO/IEC 25010 define ocho características de calidad: adecuación funcional, eficiencia "
        "de desempeño, compatibilidad, usabilidad, fiabilidad, seguridad, mantenibilidad y "
        "portabilidad. No todas se evaluaron con el mismo rigor. El proyecto priorizó cuatro "
        "por su relación con el problema: eficiencia de desempeño, seguridad, mantenibilidad y "
        "usabilidad. Las demás se documentan con evidencia indirecta y se marcan como no "
        "medidas formalmente.")
    k.table("Características ISO 25010 y evidencia",
            ["Característica", "Subcaracterísticas evaluadas", "Evidencia", "Estado"],
            [["Adecuación funcional", "Completitud, corrección", "107 pruebas, flujos E2E", "Medida"],
             ["Eficiencia", "Comportamiento temporal, uso de recursos", "Métricas de 6 rutas", "Medida"],
             ["Compatibilidad", "Coexistencia, interoperabilidad", "SQLite/PostgreSQL, navegadores", "Parcial"],
             ["Usabilidad", "Reconocibilidad, estética, accesibilidad", "5 paneles, responsive, estados vacíos", "Revisada"],
             ["Fiabilidad", "Madurez, disponibilidad, tolerancia a fallos", "Transacciones, 409, pruebas", "Parcial"],
             ["Seguridad", "Confidencialidad, integridad, autenticación", "Matriz, IDOR, CSRF, adjuntos", "Medida"],
             ["Mantenibilidad", "Modularidad, analizabilidad, modificabilidad", "3 apps, servicios, 107 pruebas", "Medida"],
             ["Portabilidad", "Adaptabilidad, instalación", "Venv, `.env`, `DATABASE_URL`", "Parcial"]],
            widths=[0.95, 1.25, 1.35, 0.55])

    k.h2("9.2 Método de medición")
    k.p("Las mediciones se tomaron en el entorno local de desarrollo, con la base demo y el "
        "servidor `runserver`, usando el cliente de pruebas de Django y `CaptureQueriesContext` "
        "para contar consultas. Se registraron mediana, mínimo y máximo de varias repeticiones. "
        "No se usó una herramienta de carga externa ni una base de datos de producción. Por "
        "tanto, los valores sirven para comparar rutas y detectar N+1, no para prometer "
        "capacidad. Esa distinción se explicita en cada tabla.")

    k.h2("9.3 Resultados de eficiencia")
    k.table("Métricas locales por ruta",
            ["Ruta", "HTTP", "Consultas", "Mediana (ms)", "Rango (ms)"],
            [["`/` (landing)", "200", "0", "2,8", "2,3–3,9"],
             ["`/panel/cliente/`", "200", "9", "14,8", "14,0–17,9"],
             ["`/panel/trazabilidad/`", "200", "32", "28,1", "25,9–32,9"],
             ["`/panel/director/`", "200", "22", "21,9", "20,3–24,5"],
             ["`/agenda/api/reservar/` (ok)", "200", "—", "15,6", "—"],
             ["`/agenda/api/reservar/` (conflicto)", "409", "5", "8,6", "—"]],
            widths=[1.55, 0.45, 0.65, 0.75, 0.7], align_center=True)
    k.p("La landing no consulta la base: solo renderiza la plantilla institucional. El dashboard "
        "del cliente usa nueve consultas, incluyendo relaciones con empresa, franja y "
        "responsables. Trazabilidad es la vista más costosa (32 consultas) porque agrega "
        "indicadores, series y tablas; aun así, se mantiene por debajo de 30 ms en la mediana. "
        "El conflicto de reserva es más rápido que la reserva exitosa porque no escribe.")

    k.h2("9.4 Seguridad")
    k.p("La seguridad se evaluó con la matriz de cinco roles y pruebas de acceso directo. Los "
        "casos cubren: cliente que intenta abrir un caso ajeno, docente que intenta abrir un "
        "caso no asignado, coordinador que intenta filtrar por el área contraria, usuario "
        "anónimo que intenta entrar a un panel y cliente que intenta descargar un adjunto de "
        "otra solicitud. El resultado esperado es 404 o 403, sin fuga de datos. También se "
        "verifican CSRF, validadores de contraseña y la separación de notas internas.")

    k.h2("9.5 Mantenibilidad")
    k.p("La mantenibilidad se apoya en tres decisiones: fronteras por app, servicios explícitos "
        "y una suite que actúa como red de seguridad. El código tiene 17 archivos Python en "
        "`accounts`, 15 en `scheduling` y 10 en `portal`, además de 31 plantillas. La suite tiene "
        "107 pruebas en 18 clases y se ejecuta en una base aislada en aproximadamente 67,5 s. "
        "No se calculó una métrica formal de cobertura; se declara como límite. La calidad se "
        "midió por comportamiento: cada regla crítica tiene al menos una prueba que la ejerce.")

    k.h2("9.6 Usabilidad")
    k.p("La usabilidad se revisó en navegador, no solo en código. Los cinco paneles comparten "
        "barra lateral, tipografía, colores y patrones de tabla. Se verificó el diseño en "
        "anchos de 390 a 1440 px, los estados vacíos muestran un mensaje útil en lugar de una "
        "tabla en blanco y las acciones destructivas piden confirmación. La demo se ensayó con "
        "las cuentas reales para detectar fricciones de navegación. No se aplicó una prueba "
        "formal con usuarios ni una auditoría WCAG completa; son límites declarados.")

    k.h2("9.7 Límites y plan de mejora")
    k.table("Límites de la evaluación y siguiente paso",
            ["Límite", "Riesgo", "Mejora propuesta"],
            [["Sin prueba de carga", "No se conoce el punto de saturación", "k6 o Locust contra PostgreSQL en un entorno staging"],
             ["Sin cobertura formal", "Puede haber rutas sin prueba", "`coverage.py` con umbral por app"],
             ["Tiempos locales", "No representan producción", "Medir con Gunicorn, Postgres y un CDN"],
             ["Muestra pequeña", "Los promedios no son concluyentes", "Seed con volumen sintético y series de 30 días"],
             ["Sin auditoría WCAG", "Barreras de accesibilidad", "Revisión con axe y prueba con lectores de pantalla"],
             ["Sin observabilidad", "Diagnóstico lento en producción", "Logs estructurados, métricas y trazas"]],
            widths=[1.0, 1.1, 1.55])
    k.callout("Lectura honesta",
              "El sistema es adecuado para el contexto académico y demuestra las decisiones "
              "arquitectónicas, pero no está certificado para producción. Los valores de "
              "rendimiento son locales, la muestra es pequeña y no hay prueba de carga. "
              "Declararlo no debilita la entrega: la hace verificable.", "amber")
