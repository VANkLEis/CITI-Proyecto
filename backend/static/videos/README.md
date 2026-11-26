# Videos de la zona pública

Los 3 MP4 están incluidos en `backend/static/videos/` y se generaron con
`tools/generate_ken_burns.py` a partir de los pósters reales. Son contenido
reemplazable: si se eliminan o fallan, el navegador muestra el `poster` y la
`<img>` de respaldo de `templates/portal/partials/media_video.html`.

## Archivos

| Archivo | Uso | Póster |
|---|---|---|
| `hero-citi.mp4` | Hero de la portada | `images/landing/hero-citi-poster.jpg` |
| `progreso-ingenieria.mp4` | Sección "Cómo funciona" | `images/landing/progreso-ingenieria-poster.jpg` |
| `resultados-impacto.mp4` | Banda del portafolio | `images/landing/resultados-impacto-poster.jpg` |

## Especificaciones

- Contenedor MP4 / H.264, sin audio (`-an`), `faststart`.
- 8–10 s en loop continuo; el zoom vuelve al punto inicial para evitar saltos.
- Hero: 1920×1080, objetivo < 6 MB. Secciones: 1600×900, objetivo < 4 MB.
- Sin texto quemado: el copy vive en la plantilla, no en el video.

## Regeneración

```powershell
py -m venv tools/.venv
tools\.venv\Scripts\python.exe -m pip install -r tools\requirements-video.txt
tools\.venv\Scripts\python.exe tools\generate_ken_burns.py
```

`imageio-ffmpeg` incluye el binario ffmpeg; no se instala ffmpeg en la imagen
Docker. Después de regenerar, reconstruir el contenedor para que
`collectstatic` copie los archivos.

## Reglas de implementación

- El `<video>` siempre lleva `autoplay muted loop playsinline
  preload="metadata"` y un `poster` que **sí existe**.
- La `<img>` de respaldo queda debajo: si el video falla, se ve la imagen.
- `prefers-reduced-motion: reduce` oculta el video (CSS en `public.css`) y
  `public.js` pausa la reproducción.
- No agregar audio ni subtítulos: son videos decorativos (`aria-hidden`).
