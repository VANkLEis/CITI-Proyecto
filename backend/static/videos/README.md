# Videos de la zona pública

Los MP4 son **contenido externo reemplazable**: el sitio funciona sin ellos.
Mientras no existan, el navegador muestra el `poster` (una imagen real de
`static/images/landing/`) y la `<img>` de respaldo de
`templates/portal/partials/media_video.html`.

## Archivos esperados

| Archivo | Uso | Poster de respaldo |
|---|---|---|
| `hero-citi.mp4` | Hero de la portada | `images/landing/hero-equipo.jpg` |
| `progreso-ingenieria.mp4` | Sección "Cómo funciona" | `images/landing/proceso-revision.jpg` |
| `resultados-impacto.mp4` | Banda del portafolio | `images/landing/reportes-manos.jpg` |

## Especificaciones

- Contenedor MP4 / H.264, sin audio (`-an`), `faststart`.
- 8–10 s en loop continuo; sin cortes bruscos en el empalme.
- Hero: 1920×1080, objetivo < 6 MB. Secciones: 1600×900, objetivo < 4 MB.
- Sin texto quemado: el copy vive en la plantilla, no en el video.

Comando de referencia (ffmpeg):

```bash
ffmpeg -i entrada.mp4 -an -vf "scale=1920:-2" -c:v libx264 -crf 23 \
  -pix_fmt yuv420p -movflags +faststart hero-citi.mp4
```

## Reglas de implementación

- El `<video>` siempre lleva `autoplay muted loop playsinline
  preload="metadata"` y un `poster` que **sí existe**.
- La `<img>` de respaldo queda debajo: si el video falla, se ve la imagen.
- `prefers-reduced-motion: reduce` oculta el video (CSS en `public.css`) y
  `public.js` pausa la reproducción.
- No agregar audio ni subtítulos: son videos decorativos (`aria-hidden`).
