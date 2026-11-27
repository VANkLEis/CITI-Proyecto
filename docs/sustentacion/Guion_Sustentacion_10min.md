# Guion de sustentación · CITI UCC

**Curso:** Arquitectura y Modelamiento de Software  
**Entrega:** Sustentación final · Noviembre de 2026  
**Expositores:** Santiago Cubillos Arana y Juan José Tique  
**Duración:** 9:00 de voz + 0:30 de transiciones = **9:30 en reloj** (colchón de 0:30 hasta el límite de 10:00)  
**Reparto:** Santiago 5:05 · Juan José 3:55  
**Soporte:** [`CITI_Sustentacion_Final.pptx`](../presentacion/CITI_Sustentacion_Final.pptx) (13 diapositivas + R1-R3 de respaldo)

---

## 1. Reglas de escena

- Una idea por diapositiva. No se lee la pantalla: se explica la decisión.
- Santiago abre, modela y decide. Juan José mide, escala, despliega y demuestra.
- La demo dura 1:05 y tiene respaldo en video y capturas. Nunca se improvisa en vivo.
- Si el tiempo se acorta: recortar primero la diapositiva 3 (evolución) y luego la 7 (drivers). Nunca la demo ni el cierre.
- Si se abre una pregunta durante la exposición, se responde en una frase y se ofrece profundizar al final.
- Frases prohibidas: “esto es solo un prototipo”, “después lo mejoramos”, “no alcanzamos”. Se reemplazan por límites declarados: “está fuera del alcance de esta entrega y aquí está la ruta”.

---

## 2. Cronograma maestro

| # | Diapositiva | Quién | Voz | Inicio–fin | Transición |
|---|---|---|---|---|---|
| 1 | Portada | Santiago | 0:20 | 0:00–0:20 | 0:05 → 0:25 |
| 2 | Problema y contexto | Santiago | 0:45 | 0:25–1:10 | — |
| 3 | Evolución S1–S16 | Santiago | 0:30 | 1:10–1:40 | 0:05 → 1:45 |
| 4 | Casos de uso | Santiago | 0:40 | 1:45–2:25 | — |
| 5 | Componentes | Santiago | 0:45 | 2:25–3:10 | — |
| 6 | Arquitectura por capas | Santiago | 0:45 | 3:10–3:55 | — |
| 7 | Drivers | Santiago | 0:40 | 3:55–4:35 | — |
| 8 | ADRs | Santiago | 0:40 | 4:35–5:15 | 0:05 → 5:20 |
| 9 | ISO/IEC 25010 | Juan José | 0:45 | 5:20–6:05 | — |
| 10 | Escalabilidad | Juan José | 0:45 | 6:05–6:50 | 0:05 → 6:55 |
| 11 | Despliegue | Juan José | 0:45 | 6:55–7:40 | 0:05 → 7:45 |
| 12 | Demo | Juan José | 1:05 | 7:45–8:50 | 0:05 → 8:55 |
| 13 | Cierre | Juan José | 0:35 | 8:55–9:30 | Fin 9:30 |

**Voces:** Santiago 305 s (5:05) · Juan José 235 s (3:55) · Total 540 s (9:00)  
**Transiciones:** 6 × 5 s = 30 s · **Reloj final:** 9:30

---

## 3. Guion palabra por palabra

### Diapositiva 1 · Portada — Santiago · 0:20

> Buenos días. Somos Santiago Cubillos y Juan José Tique. Presentamos CITI, el Consultorio de Ingeniería, Tecnología e Innovación de la UCC: la arquitectura y el modelado de un sistema que lleva una solicitud desde el primer contacto hasta el acta de cierre, con responsables y evidencia en cada paso.

**Cue:** mirar al jurado, no a la pantalla. Dejar 2 s de silencio antes de avanzar.

**Transición (5 s):** “Para entender por qué esta arquitectura es así, primero hay que entender el problema”.

---

### Diapositiva 2 · Problema y contexto — Santiago · 0:45

> El CITI conecta empresas, instituciones y ciudadanía con el conocimiento de dos programas: Sistemas y Civil. Hoy esa relación vive en correos, hojas de cálculo y memoria. El problema no es la falta de pantallas: es la falta de confianza. Sin un responsable visible, sin reglas académicas explícitas y sin historial, nadie puede responder quién atendió, qué se prometió y cómo terminó. Por eso el sistema se diseñó alrededor de tres ideas: acceso por rol, trazabilidad de cada cambio y un cierre verificable. No es un CRM genérico; es un consultorio universitario con reglas propias.

**Cue:** señalar los cinco roles y las dos áreas. No enumerar las 14 especialidades todavía.

---

### Diapositiva 3 · Evolución — Santiago · 0:30

> El proyecto evolucionó en tres tramos. S1 a S5 fue modelado: actores, casos de uso, clases y una primera arquitectura. S6 a S10 llevó ese modelo a Django, corrigió bloqueantes y llegó a 42 pruebas. S11 a S16 agregó trazabilidad, interacción con el cliente y 107 pruebas. Las capturas oscuras de la izquierda son evidencia del modelado inicial; no son el modelo vigente. El modelo final se regeneró desde el código.

**Cue:** decir “no son el modelo vigente” mirando al jurado; es la frase que evita una objeción.

**Transición (5 s):** “Si el modelo cambió, la pregunta es qué puede hacer hoy cada actor”.

---

### Diapositiva 4 · Casos de uso — Santiago · 0:40

> Cinco roles, un mismo flujo de valor. El cliente solicita, sigue, comenta y aprueba. El estudiante registra bitácora y apoya casos. El docente gestiona, entrega y cierra. El coordinador revisa su bandeja, asigna docente y tutor, y hace seguimiento de su área. El director mide, filtra y decide. El caso compartido es UC-13: coordinador por área, director global. La regla es simple: el alcance lo fuerza el servidor, nunca el frontend.

**Cue:** recorrer la fila de tarjetas de izquierda a derecha y detenerse en la franja de estados.

---

### Diapositiva 5 · Componentes — Santiago · 0:45

> Tres apps con límites claros. accounts responde quién entra y qué requisitos académicos cumple. scheduling responde qué se agenda, en qué estado va y qué evidencia deja. portal responde cómo se presenta cada rol y qué puede decidir. Debajo, cuatro servicios de dominio: trazabilidad, indicadores, el catálogo real de subespecialidades y el decorador de roles. No usamos DRF: el JSON existe solo para el calendario y la reserva. El admin es una herramienta administrativa, no el dashboard del director.

**Cue:** “catálogo real” es intencional: existe en `scheduling/subespecialidades.py`, no en un portafolio inexistente.

---

### Diapositiva 6 · Arquitectura por capas — Santiago · 0:45

> La petición recorre capas explícitas: URL, autenticación y rol, vista, servicio, ORM, base de datos y template. Las capas no son carpetas: son una regla de dependencia. Un template no decide permisos y una vista no arma SQL a mano. Las reglas críticas —cupos, transiciones, visibilidad— viven en modelos y servicios, y se prueban ahí. Por eso el sistema es un monolito modular: un solo despliegue, pero con fronteras que permiten extraer módulos después.

**Cue:** usar la columna derecha como “atajo mental”; no leer cada caja.

---

### Diapositiva 7 · Drivers — Santiago · 0:40

> Tres drivers cambiaron el diseño. Primero, seguridad y acceso por rol: cinco roles, área forzada, login con portal esperado, pruebas de IDOR y CSRF. Segundo, trazabilidad transaccional: cada mutación relevante pasa por un servicio explícito y deja un evento; si la operación falla, no queda evento de éxito. Tercero, mantenibilidad: tres apps, 107 pruebas y documentación por fase. La restricción real era dura: dos personas, diez semanas, sin presupuesto de infraestructura.

**Cue:** la última frase justifica todo lo que viene; bajarla de velocidad.

---

### Diapositiva 8 · ADRs — Santiago · 0:40

> Documentamos diez ADRs. Los cuatro que explican el conjunto: monolito modular frente a microservicios, porque la consistencia transaccional pesaba más que la independencia de despliegue; templates con JSON mínimo frente a SPA con DRF, para reducir superficie y estado en el cliente; SQLite en desarrollo y PostgreSQL en producción; y servicios de dominio explícitos frente a señales globales, para evitar eventos duplicados o efectos ocultos. La decisión no es que Django sea mejor: es que el contexto no justificaba el costo operativo de microservicios.

**Transición / handoff (5 s):** “Juan José les cuenta cómo medimos la calidad y cómo escala”.

---

### Diapositiva 9 · ISO/IEC 25010 — Juan José · 0:45

> Gracias, Santiago. Medimos cuatro atributos de ISO 25010. Eficiencia de desempeño con mediciones reales en local: la landing en 2,8 milisegundos y cero consultas; el dashboard del cliente en 14,8 y nueve consultas; trazabilidad en 28,1 y 32; la reserva en 15,6. Seguridad con la matriz de cinco roles, IDOR, CSRF y adjuntos autorizados. Mantenibilidad con tres apps, 107 pruebas y migraciones al día. Usabilidad con cinco paneles, responsive y estados vacíos honestos. Declaramos el límite: no hay prueba de carga ni cobertura formal; los tiempos son locales y la muestra es pequeña.

**Cue:** “medimos lo que podemos defender” es la tesis; no inflar los números.

---

### Diapositiva 10 · Escalabilidad — Juan José · 0:45

> Si mañana se multiplican usuarios, el primer cuello no es Django: es SQLite con un solo escritor. Después, WSGI síncrono, media local y la ausencia de caché y colas. La ruta es por fases. Fase uno: PostgreSQL, PgBouncer, Gunicorn y Nginx. Fase dos: Redis para caché y sesiones, tareas asíncronas y S3 o CDN para archivos. Fase tres: réplicas de lectura, servicios extraídos y observabilidad. No escalamos antes de medir. El límite modular permite extraer identidad, notificaciones o reportes sin reescribir el dominio.

**Transición (5 s):** “Esa ruta se concreta en el despliegue”.

---

### Diapositiva 11 · Despliegue — Juan José · 0:45

> El despliegue mantiene el mismo código y cambia la infraestructura. En local: runserver, SQLite, media local, seed idempotente y 107 pruebas en base aislada. En producción: GitHub, Nginx con HTTPS y proxy, Gunicorn o uWSGI con workers, Django 5 por WSGI y PostgreSQL por DATABASE_URL. El endurecimiento se activa con DJANGO_ENV=produccion: secreto obligatorio, ALLOWED_HOSTS obligatorio, HSTS, cookies seguras y redirección SSL. Límite actual: no hay Docker, Procfile ni CI/CD; el despliegue es manual y las dependencias no están pinneadas. Está documentado como trabajo futuro.

**Transición (5 s):** “Y esto no se queda en el diagrama: se opera”.

---

### Diapositiva 12 · Demo — Juan José · 1:05

> Ahora la arquitectura se demuestra operándola.

**Runbook exacto (ensayar con cronómetro):**

1. **0:00–0:15 · Cliente.** Entrar como `cliente@empresatolima.co` / `CITIPass2026*`. Abrir “Mis solicitudes” y la solicitud 17. Señalar la línea de tiempo y el entregable pendiente.
2. **0:15–0:30 · Interacción.** Escribir un comentario breve (“Revisado con el equipo; solicito ajuste en el alcance”). Guardar. Mostrar que aparece en el historial como interacción y como evento.
3. **0:30–0:45 · Docente.** Cambiar a `docente@citi.ucc.edu.co`. Abrir el caso 17. Mostrar ficha, entrega publicada e historial. Decir: “publicar una entrega no finaliza el caso; aprobar tampoco”.
4. **0:45–1:05 · Director.** Cambiar a `director@citi.ucc.edu.co`. Abrir Trazabilidad, filtrar 90 días, señalar los KPI y exportar el CSV.

> Cada clic corresponde a una vista, un servicio y una tabla o evento. Si falla la red, tenemos video y capturas.

**Cue:** no leer la pantalla; narrar qué capa se está viendo. Tener el video abierto en otra pestaña.

**Transición (5 s):** “Con eso, cierro”.

---

### Diapositiva 13 · Cierre — Juan José · 0:35

> Cierro con tres números: 107 pruebas, 8 modelos, 5 estados formales. Y con límites declarados: el flujo mixto, las observaciones de seguridad en revisión, la ausencia de CI/CD y de pruebas de carga, la media local y FullCalendar por CDN. La arquitectura es adecuada para el contexto y tiene una ruta clara de evolución. No defiendan un diagrama: defiendan las decisiones que lo hicieron posible. Gracias.

**Cue:** bajar el ritmo, mirar al jurado y quedarse quieto 3 s. No cerrar con “¿preguntas?”; esperar.

---

## 4. Banco de preguntas y respuestas

**1. ¿Por qué no microservicios?**  
Porque el requisito dominante era la consistencia transaccional entre cita, evento e interacción, y el equipo era de dos personas. Un monolito modular da una sola transacción y un solo despliegue; las fronteras por app permiten extraer servicios cuando el volumen lo justifique.

**2. ¿Por qué no DRF ni una SPA?**  
El 90 % del producto es formularios y vistas por rol. Una SPA habría duplicado reglas de autorización en el cliente y agregado estado, build y superficie de ataque. El JSON se limita al calendario y a la reserva.

**3. ¿Cómo evitan eventos duplicados?**  
Las escrituras pasan por funciones explícitas de `scheduling/trazabilidad.py`, no por señales globales. Cada flujo llama una sola función dentro de `transaction.atomic()`. Además, `nota_asignacion` verifica si el usuario ya revisó la solicitud antes de crear el evento.

**4. ¿Qué pasa si falla la operación?**  
La transacción revierte completa: no queda cambio de estado, ni interacción, ni evento de éxito. Esa es la razón de que el evento se escriba en la misma transacción y no en un proceso posterior.

**5. ¿Cómo evitan IDOR?**  
Cada vista filtra por propietario o por área antes de responder; el coordinador tiene `area_forzada` en el servidor. Los tests devuelven 404 o 403, no “acceso denegado” con datos. El detalle despacha por rol y el adjunto se sirve por una vista autorizada, no por `MEDIA_URL`.

**6. ¿Cómo se calculan los indicadores?**  
Están documentados en `portal/indicadores.py`: recibidas por `creada_en`, finalizadas por estado, tasa de finalización sobre recibidas (incluye canceladas), tiempos promedio solo con marcas reales y “No disponible” cuando no hay muestra. El CSV usa el mismo criterio.

**7. ¿Por qué SQLite y cómo escala?**  
SQLite es suficiente para la demo y elimina infraestructura. Para producción se cambia a PostgreSQL con `DATABASE_URL`; el código ya soporta ambos. El cuello real es el escritor único, y por eso la fase uno incluye PostgreSQL y PgBouncer.

**8. ¿Aprobar un entregable no debería cerrar el caso?**  
No. Aprobar es una decisión sobre el entregable; cerrar es una decisión administrativa distinta, con acta y resumen. Separarlas evita cierres accidentales y permite reabrir solo de `finalizada` a `en_proceso` cuando el cliente pide ajustes.

**9. ¿Cómo se controla que un estudiante sea tutor?**  
La regla vive en el modelo: mínimo 8.º semestre, 130 créditos y promedio 4.0, configurables por variables de entorno. `PerfilEstudiante.save()` y la señal `post_save` promueven o degradan el tipo; no se asigna a mano. La asignación vuelve a validar el perfil.

**10. ¿Qué falta para producción?**  
CI/CD, dependencias pinneadas, PostgreSQL administrado, almacenamiento externo para adjuntos, backups, observabilidad, pruebas de carga y revisión de los hallazgos de seguridad declarados. La arquitectura ya tiene los puntos de extensión; no está vendida como producción terminada.

**11. ¿Qué fue lo más difícil?**  
La frontera entre estado, interacción y evento. Un comentario no es un cambio de estado, pero sí deja evidencia; una aprobación no cierra, pero puede reabrir. Esa separación obligó a una tabla formal de transiciones y a servicios explícitos, y es lo que más pruebas acumuló.

**12. ¿Usaron IA? ¿Cómo la validaron?**  
Sí, como apoyo para redactar, revisar consistencia y proponer diagramas. La fuente de verdad fue el código: cada afirmación se contrastó con modelos, vistas y pruebas, y los diagramas se regeneraron con PlantUML desde las fuentes versionadas. Ningún cambio de lógica se aceptó sin revisión y sin que la suite de 107 pruebas siguiera en verde.

---

## 5. Checklist previo (T-10 minutos)

- [ ] Servidor Django corriendo con `..\venv\Scripts\python.exe manage.py runserver` desde `backend/`.
- [ ] `seed_demo` ejecutado y solicitud 17 disponible con entregable pendiente.
- [ ] Tres sesiones listas: cliente, docente, director (ventanas separadas o perfiles del navegador).
- [ ] Video de respaldo de 2 min abierto y silenciado.
- [ ] PDF de la presentación en el escritorio y en el correo.
- [ ] Cronómetro visible para Juan José; aviso a los 7:45 para iniciar demo.
- [ ] Zoom del navegador al 100 %; notificaciones y correo cerrados.
- [ ] Probar proyector: 16:9, sin recorte de la barra inferior.

## 6. Plan de contingencia

| Falla | Respuesta |
|---|---|
| No abre el servidor | Cambiar al video de respaldo y narrar sobre las capturas de la diapositiva 12. |
| No hay internet | FullCalendar por CDN puede fallar; usar el video. El resto del sitio es local. |
| Se cae la demo a mitad | “La demo ya quedó registrada; sigo con el cierre” y pasar a la diapositiva 13. |
| Pregunta hostil | “Es un límite declarado; está en la diapositiva de cierre y en el documento, sección de trabajo futuro”. |
| Se acaba el tiempo en la diapositiva 8 | Saltar a la 9 y entregar el turno; la demo y el cierre son intocables. |

---

## 7. Frases de anclaje (memorizar)

- “No es un CRM genérico; es un consultorio universitario con reglas propias”.
- “Las capas no son carpetas: son una regla de dependencia”.
- “Si la operación falla, no queda evento de éxito”.
- “El alcance lo fuerza el servidor, no el frontend”.
- “Medimos lo que podemos defender”.
- “No escalamos antes de medir”.
- “Aprobar un entregable no cierra el caso”.
- “No defiendan un diagrama; defiendan las decisiones”.
