# Herramientas de contenido público

Estas herramientas no forman parte del runtime de Django ni se copian a la
imagen Docker. Generan los assets que después se versionan en
`backend/static/`.

## Vendor local (offline)

FullCalendar 6.1.15 y Open Sans están vendorizados para que Docker no llame a
CDNs:

- `backend/static/vendor/fullcalendar/6.1.15/index.global.min.js` + `LICENSE.md`.
- `backend/static/fonts/open-sans/open-sans-latin-var.woff2` + `OFL.txt`.
- `backend/static/css/fonts.css` declara el `@font-face` local.

No hay archivo CSS de FullCalendar 6: el paquete inyecta sus estilos desde el
JS. El `<link>` antiguo a `index.global.min.css` era un 404 y se retiró.

## Imágenes

```powershell
..\venv\Scripts\python.exe tools\fetch_public_images.py --force
```

- Lee `tools/public_images.json` (fuente exacta, licencia y autor).
- Valida HTTP 200, MIME de imagen y dimensiones mínimas.
- Recorta a 1600×1000 (tarjetas) o 1920×1080/1600×900 (pósters).
- Escribe `tools/public_images.lock.json` y `docs/demo/CREDITOS_IMAGENES.md`.
- No usa búsquedas en vivo: la descarga es reproducible.

## Videos Ken Burns

```powershell
py -m venv tools/.venv
tools\.venv\Scripts\python.exe -m pip install -r tools\requirements-video.txt
tools\.venv\Scripts\python.exe tools\generate_ken_burns.py
```

- Usa el ffmpeg incluido en `imageio-ffmpeg`; no requiere ffmpeg del sistema.
- Genera `hero-citi.mp4`, `progreso-ingenieria.mp4` y
  `resultados-impacto.mp4` desde los pósters.
- H.264, `yuv420p`, sin audio, `faststart`, 8–10 s y loop suave.
- Los MP4 se commitean; Docker solo los sirve desde `static/`.
