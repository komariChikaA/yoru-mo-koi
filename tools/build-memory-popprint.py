"""Build a shared soft pastel surface, following the game's bright photo OP."""
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/memory-popprint'
MAP = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ/sb/memory-popprint')
OUT.mkdir(parents=True, exist_ok=True)
MAP.mkdir(parents=True, exist_ok=True)


def save(image, name):
    image.save(OUT / name)
    shutil.copyfile(OUT / name, MAP / name)
    print(f'{name}: {image.width}x{image.height} RGBA')


def surface(width, world_left):
    y, x = np.mgrid[:480, :width]
    world_x = x + world_left
    v = y / 479
    base = np.array((255., 251., 245.))[None, None, :] * (1-v[..., None])
    base += np.array((253., 246., 231.))[None, None, :] * v[..., None]
    # Two broad, feathered washes share world coordinates across the page seam.
    # They are the material itself, never additional panels or moving stickers.
    peach = np.exp(-((y-90)/190.)**2) * (.5+.5*np.cos(2*np.pi*(world_x-100)/1280.)) * .80
    mint = np.exp(-((y-290)/220.)**2) * (.5+.5*np.cos(2*np.pi*(world_x-650)/1280.)) * .65
    rgb = base * (1-peach[..., None]) + np.array((253., 225., 228.)) * peach[..., None]
    rgb = rgb * (1-mint[..., None]) + np.array((225., 243., 242.)) * mint[..., None]
    # Subpixel ordered dither prevents banding without a paper-noise overlay.
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
    dither = (bayer[y % 4, x % 4] + .5) / 16 - .5
    pixels = np.empty((480, width, 4), dtype=np.uint8)
    pixels[:, :, :3] = np.uint8(np.clip(np.rint(rgb + dither[..., None]), 0, 255))
    pixels[:, :, 3] = 255
    return pixels


save(Image.fromarray(surface(854, -107)), 'page-ground.png')
pixels = surface(2600, 640)
pixels[:, :, 3] = np.uint8(np.minimum(np.arange(2600) / 107, 1)[None, :] * 255)
save(Image.fromarray(pixels), 'ground.png')


def band(width, height):
    pixels = np.empty((height, width, 4), dtype=np.uint8)
    pixels[:, :, :3] = (249, 227, 172)
    pixels[:, :, 3] = 255
    edge = max(1, height // 40)
    pixels[:edge, :, 3] = np.uint8(np.linspace(90, 255, edge))[:, None]
    pixels[-edge:, :, 3] = np.uint8(np.linspace(255, 90, edge))[:, None]
    return pixels


save(Image.fromarray(band(1760, 160)), 'front-strip.png')
pixels = band(2400, 80)
pixels[:, :, 3] = np.uint8(pixels[:, :, 3] * np.minimum(np.arange(2400) / 120, 1)[None, :])
save(Image.fromarray(pixels), 'ribbon.png')
print(f'Installed to {MAP}')
