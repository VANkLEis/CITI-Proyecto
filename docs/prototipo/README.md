# Prototipo estático · archivo histórico

Esta carpeta conserva la maqueta Hi-Fi que se usó antes de la implementación
Django. Se movió desde la raíz (`app/`, `assets/`, `dashboards/`, `plantillas/`
y los `*.html` sueltos) para que el repositorio tenga una sola aplicación MVT en
`backend/`.

**No es la plataforma real y no participa del runtime ni de la imagen Docker.**
El prototipo usa JavaScript vanilla y `localStorage`; las reglas de negocio,
permisos y datos viven únicamente en Django.

## Cómo abrirlo

- `visualizacion.html`: recorrido completo de las pantallas.
- `login.html`: login simulado del prototipo.
- `prototipo-flujos.html`: mapa de flujos.
- `design-system.html` y `manual-identidad.html`: identidad visual.

Los enlaces relativos funcionan porque `app/`, `assets/`, `dashboards/` y
`plantillas/` se conservaron dentro de esta misma carpeta.
