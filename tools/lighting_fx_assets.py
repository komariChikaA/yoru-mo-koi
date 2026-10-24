"""Deterministic neutral-alpha textures for LightingFx; no external image inputs."""
from pathlib import Path
import argparse
import shutil
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def save_alpha(path, alpha):
    rgba = np.full((*alpha.shape, 4), 255, np.uint8)
    rgba[..., 3] = np.round(np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(rgba).save(path)


def strip(width, height, half_max, strength=1, end_feather=0):
    x = np.arange(width) + .5 - width / 2
    cross = .5 + .5 * np.cos(np.pi * np.clip(x / (2 * half_max), -1, 1))
    alpha = np.broadcast_to(cross * strength, (height, width)).copy()
    if end_feather:
        edge = np.minimum(np.arange(height) + .5, height - np.arange(height) - .5)
        feather = .5 - .5 * np.cos(np.pi * np.minimum(edge / end_feather, 1))
        alpha *= feather[:, None]
    return alpha


def spot(width, height):
    y, x = np.mgrid[:height, :width]
    radius = np.sqrt(((x + .5 - width / 2) / (width / 2))**2 +
                     ((y + .5 - height / 2) / (height / 2))**2)
    return .5 + .5 * np.cos(np.pi * np.minimum(radius, 1))


def tube_beam(width, height):
    # Top-centre is the lamp aperture/pivot. A broad shaft spreads gently
    # toward the page; soft sides and a finite tail keep it graphic, not foggy.
    y, x = np.mgrid[:height, :width]
    travel = (y + .5) / height
    half_width = 58 + (width / 2 - 58) * np.minimum(travel / .78, 1)
    cross = .5 + .5 * np.cos(np.pi * np.minimum(np.abs(x + .5 - width/2) / half_width, 1))
    head = .5 - .5 * np.cos(np.pi * np.minimum((y + .5) / 80, 1))
    tail = .5 - .5 * np.cos(np.pi * np.minimum((height - y - .5) / 240, 1))
    return cross * head * tail


def build(mapset=None):
    out = ROOT / 'assets/lighting-fx'
    out.mkdir(parents=True, exist_ok=True)
    textures = {
        'light_sweep_wide.png': strip(512, 1536, 128),
        'light_sweep_narrow.png': strip(192, 1536, 48),
        'soft_glow_round.png': spot(512, 512),
        'soft_glow_big.png': spot(1024, 768),
        'paper_shine.png': strip(512, 1024, 128, strength=.65, end_feather=96),
        # Both axes are feathered. LineGlow scales this patch to pixel dimensions.
        'line_shine.png': strip(64, 256, 16, end_feather=128).T,
        'light_tube_beam.png': tube_beam(768, 1152),
    }
    for name, alpha in textures.items():
        save_alpha(out / name, alpha)
    if mapset is not None:
        target = mapset / 'sb/lighting-fx'
        target.mkdir(parents=True, exist_ok=True)
        for name in textures:
            shutil.copy2(out / name, target / name)
    print(f'Built {len(textures)} neutral LightingFx textures' + (' and installed to mapset' if mapset else ''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path)
    build(parser.parse_args().mapset)
