"""Descarga, valida y optimiza las imágenes públicas del CITI.

Uso:
    python tools/fetch_public_images.py --force

Requiere Pillow. No ejecuta búsquedas en vivo: el manifiesto
`public_images.json` contiene la fuente exacta y su licencia. Así la descarga
es reproducible y el sitio no depende de URLs externas en runtime.
"""

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / 'backend' / 'static' / 'images' / 'landing'
MANIFEST = Path(__file__).with_name('public_images.json')
LOCKFILE = Path(__file__).with_name('public_images.lock.json')
CREDITS = ROOT / 'docs' / 'demo' / 'CREDITOS_IMAGENES.md'
UA = 'CITI-UCC-demo/1.0 (academic demo; contact: citi@ucc.edu.co)'

ALLOWED_LICENSES = {
    'CC0 1.0', 'Public domain', 'CC BY 2.0', 'CC BY 4.0',
    'CC BY-SA 2.0', 'CC BY-SA 3.0', 'CC BY-SA 4.0',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status} para {url}')
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            raise RuntimeError(f'Content-Type inesperado: {content_type}')
        return response.read()


def optimize(raw, target, poster=False):
    image = Image.open(io.BytesIO(raw))
    image.verify()
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert('RGB')
    if image.width < 900 or image.height < 600:
        raise RuntimeError(
            f'Imagen demasiado pequeña: {image.width}x{image.height}')
    centering = (0.5, 0.5) if poster else (0.5, 0.35)
    image = ImageOps.fit(
        image, tuple(target), method=Image.Resampling.LANCZOS,
        centering=centering)
    buffer = io.BytesIO()
    image.save(
        buffer, format='JPEG', quality=85 if poster else 82,
        optimize=True, progressive=True)
    return buffer.getvalue(), image.size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    entries = manifest['images']
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    CREDITS.parent.mkdir(parents=True, exist_ok=True)

    lock = {'images': []}
    seen_source_hashes = set()
    seen_output_hashes = set()

    for item in entries:
        filename = item['filename']
        output = STATIC_DIR / filename
        if output.exists() and not args.force:
            print(f'= {filename} (ya existe; use --force para regenerar)')
            continue
        if item['license'] not in ALLOWED_LICENSES:
            raise RuntimeError(f'Licencia no permitida para {filename}: {item["license"]}')

        print(f'+ {filename}')
        raw = fetch(item['download_url'])
        source_hash = sha256(raw)
        if source_hash in seen_source_hashes:
            raise RuntimeError(f'Fuente repetida para {filename}')
        seen_source_hashes.add(source_hash)

        poster = item['slot'].startswith('poster:')
        optimized, size = optimize(raw, item['target'], poster=poster)
        output_hash = sha256(optimized)
        if output_hash in seen_output_hashes:
            raise RuntimeError(f'Salida repetida para {filename}')
        seen_output_hashes.add(output_hash)
        output.write_bytes(optimized)

        entry = {
            **item,
            'output': f'images/landing/{filename}',
            'output_size': list(size),
            'source_sha256': source_hash,
            'output_sha256': output_hash,
        }
        lock['images'].append(entry)
        print(f'  {size[0]}x{size[1]} · {len(optimized) // 1024} KB')

    LOCKFILE.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# Créditos de imágenes públicas',
        '',
        'Las imágenes se descargaron una vez, se recortaron a la proporción de',
        'las tarjetas o pósters y se optimizaron como JPEG. No se cargan desde',
        'CDNs ni URLs externas en runtime. El manifiesto reproducible está en',
        '`tools/public_images.json` y el lockfile en `tools/public_images.lock.json`.',
        '',
        '| Archivo | Tema | Autor | Licencia | Fuente |',
        '|---|---|---|---|---|',
    ]
    for item in lock['images']:
        lines.append(
            f"| `{item['filename']}` | {item['theme']} | {item['author']} | "
            f"{item['license']} | [ver original](<{item['source_url']}>) |")
    lines += [
        '',
        '## Notas de licencia',
        '',
        '- CC0 y dominio público no exigen atribución, pero se acreditan por',
        '  transparencia académica.',
        '- CC BY exige atribución; se conserva autor, licencia y enlace.',
        '- CC BY-SA exige atribución y compartir igual; las versiones recortadas',
        '  de este repositorio se distribuyen bajo la misma licencia de la obra',
        '  original.',
        '- Las fotos se recortaron y redimensionaron; no se alteró su contenido.',
        '',
    ]
    CREDITS.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Listo: {len(lock["images"])} imágenes; créditos en {CREDITS}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise
