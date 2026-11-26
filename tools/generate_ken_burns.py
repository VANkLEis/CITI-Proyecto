"""Genera los MP4 decorativos de la portada con efecto Ken Burns.

Requiere Pillow e imageio-ffmpeg (este último incluye un binario ffmpeg).
Los MP4 se generan una vez y se commitean; Docker no necesita ffmpeg.

Uso:
    python tools/generate_ken_burns.py
"""

import math
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / 'backend' / 'static' / 'images' / 'landing'
VIDEOS = ROOT / 'backend' / 'static' / 'videos'

JOBS = (
    {
        'poster': 'hero-citi-poster.jpg',
        'output': 'hero-citi.mp4',
        'size': (1920, 1080),
        'duration': 10,
        'crf': 25,
        'max_mb': 6,
    },
    {
        'poster': 'progreso-ingenieria-poster.jpg',
        'output': 'progreso-ingenieria.mp4',
        'size': (1600, 900),
        'duration': 8,
        'max_mb': 4,
    },
    {
        'poster': 'resultados-impacto-poster.jpg',
        'output': 'resultados-impacto.mp4',
        'size': (1600, 900),
        'duration': 8,
        'max_mb': 4,
    },
)

FPS = 30


def ken_burns_frames(image, size, duration):
    """Genera frames RGB con zoom/pan que vuelve al punto inicial."""
    width, height = size
    base = ImageOps.fit(image.convert('RGB'), size, method=Image.Resampling.LANCZOS)
    total = max(2, int(duration * FPS))
    for index in range(total):
        p = index / (total - 1)
        zoom = 1.0 + 0.08 * math.sin(math.pi * p)
        crop_w = max(2, int(width / zoom))
        crop_h = max(2, int(height / zoom))
        cx = (0.5 + 0.02 * math.sin(2 * math.pi * p)) * width
        cy = (0.5 + 0.01 * math.sin(2 * math.pi * p + math.pi / 2)) * height
        left = min(max(0, int(cx - crop_w / 2)), width - crop_w)
        top = min(max(0, int(cy - crop_h / 2)), height - crop_h)
        frame = base.crop((left, top, left + crop_w, top + crop_h))
        yield frame.resize(size, Image.Resampling.LANCZOS)


def render(job):
    poster = IMAGES / job['poster']
    output = VIDEOS / job['output']
    if not poster.exists():
        raise FileNotFoundError(poster)
    VIDEOS.mkdir(parents=True, exist_ok=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    width, height = job['size']
    command = [
        ffmpeg, '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}', '-pix_fmt', 'rgb24',
        '-r', str(FPS), '-i', '-',
        '-an', '-c:v', 'libx264', '-preset', 'medium',
        '-crf', str(job.get('crf', 23)),
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        str(output),
    ]
    print(f"+ {job['output']} ({width}x{height}, {job['duration']}s)")
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE)
    image = Image.open(poster)
    try:
        for frame in ken_burns_frames(image, job['size'], job['duration']):
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
        stderr = process.stderr.read().decode('utf-8', errors='replace')
        code = process.wait()
    if code != 0:
        raise RuntimeError(f'ffmpeg falló ({code}): {stderr}')

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f'  {size_mb:.1f} MB')
    if size_mb > job['max_mb']:
        raise RuntimeError(
            f"{job['output']} supera {job['max_mb']} MB ({size_mb:.1f} MB)")


def main():
    for job in JOBS:
        render(job)
    print('Videos generados en', VIDEOS)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise
