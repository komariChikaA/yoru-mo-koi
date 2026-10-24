"""Deterministic viscous drop + damped shallow-water front for the Memory handoff.

All frames are neutral alpha masks, colored by the shared liquid/lining curve.
Tightly cropped textures carry world-space bounds in layout.txt.
"""
from pathlib import Path
import argparse
import shutil
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "memory-flow"
STEP = 20
POOL_AT, FULL_AT = 770, 1800
IMAGE_Y = 950.0
IMAGE_SCALE = 854 / 640
TOP = IMAGE_Y - 403 * IMAGE_SCALE / 2
BOTTOM = IMAGE_Y + 403 * IMAGE_SCALE / 2
COLOR = (255, 255, 255)
SEED_COLOR = (238, 221, 184)  # #EEDDB8, matching SecretBase's initial print stock.


def install_seed(mapset):
    # Recolor only the circled dot. Original title art, dimensions and alpha stay intact.
    source = Image.open(ROOT / 'graphics/mapset/sb/title/d12.png').convert('RGBA')
    seed = Image.new('RGBA', source.size, SEED_COLOR + (255,))
    seed.putalpha(source.getchannel('A'))
    OUT.mkdir(parents=True, exist_ok=True)
    asset = OUT / 'title-seed.png'
    seed.save(asset)
    target = mapset / 'sb/title/d12.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or asset.read_bytes() != target.read_bytes():
        shutil.copyfile(asset, target)


def clamp(t):
    return np.clip(t, 0, 1)


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


def ellipse(xx, yy, x, y, rx, ry):
    return (np.sqrt(((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2) - 1) * min(rx, ry)


def smooth_union(a, b, radius=8):
    h = clamp(0.5 + 0.5 * (b - a) / radius)
    return b * (1 - h) + a * h - radius * h * (1 - h)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    # World space: title at y=240, receiving photograph surface at y=950.
    yy, xx = np.mgrid[235:1225, -107:747].astype(float)
    # Damped shallow-water height/velocity on a coarse 1D grid; fixed substeps keep CFL < 1.
    gx = np.arange(-107, 751, 4, dtype=float)
    wave = np.zeros_like(gx)
    velocity = np.zeros_like(gx)
    velocity[:] = 240 * np.exp(-((gx - 566.24) / 53) ** 2)
    rows = []
    for time in range(0, FULL_AT, STEP):
        # Exact slower title-group scale when bloom starts at 14.7s; same 0.8 landing.
        title_u = clamp((14700 + time - 13156) / 1800)
        group = 1 - 0.2 * np.sin(title_u * np.pi / 2)
        seed_x = 320 + (627.8 - 320) * group
        seed_y = 240 + (295.4 - 240) * group
        if time <= 180:
            u = time / 180
            e = 1 - (1 - u) ** 3
            r = 11.4 * group / 0.8 + 17.6 * e
            field = ellipse(xx, yy, seed_x, seed_y + 5 * e, r, r * (1 + 0.12 * e))
        elif time < 440:
            u = (time - 180) / 260
            tip_y = seed_y + 35 + 108 * u * u
            field = ellipse(xx, yy, seed_x, seed_y, 29 - 18 * u, 29 - 13 * u)
            # Elliptical neck joins the source and bulb; it thins before detaching.
            field = smooth_union(field, ellipse(xx, yy, seed_x, (seed_y + tip_y) / 2,
                                                 19 * (1 - u) + 3, (tip_y - seed_y) / 2 + 5), 12)
            field = smooth_union(field, ellipse(xx, yy, seed_x, tip_y, 24, 31 + 12 * u), 13)
        elif time < 820:
            u = clamp((time - 440) / 360)
            tip_y = seed_y + 143 + (1158 - seed_y - 143) * u * u
            field = ellipse(xx, yy, seed_x - 8 * u, tip_y, 23 + 7 * u ** 6, 43 - 10 * u ** 6)
            # Two coherent tail drops mark the pinched neck; no random spray.
            if time < 740:
                field = smooth_union(field, ellipse(xx, yy, seed_x + 2, tip_y - 64, 8, 17), 5)
                field = smooth_union(field, ellipse(xx, yy, seed_x + 3, tip_y - 112, 4.8, 8), 4)
            if time < 520:
                remain = 1 - (time - 440) / 80
                field = smooth_union(field, ellipse(xx, yy, seed_x, seed_y, 10 * remain + 0.3, 13 * remain + 0.3), 3)
        else:
            field = np.full_like(xx, 10000)

        if time >= POOL_AT:
            p = (time - POOL_AT) / (FULL_AT - POOL_AT)
            for _ in range(10):
                padded = np.pad(wave, 1, mode="edge")
                laplace = (padded[:-2] - 2 * wave + padded[2:]) / 16
                velocity += (480 ** 2 * laplace - 7 * velocity) * 0.002
                wave += velocity * 0.002
            ripple = np.interp(xx[0], gx, wave) * (1 - p) ** 2
            # A longer, eased rise: avoid the old OutCubic front flooding the screen
            # almost immediately. Width leads gently while height takes the full span.
            spread = 24 + 940 * np.sin(p * np.pi / 2)
            rise = 0.5 - 0.5 * np.cos(p * np.pi)
            height = 52 + (BOTTOM - TOP - 52 + 6) * rise
            curvature = 100 * (1 - p) ** 2 * ((xx[0] - 558) / spread) ** 2
            surface = np.maximum(TOP, BOTTOM - height + curvature + ripple)
            pool = np.maximum(surface[None, :] - yy, np.abs(xx - 558) - spread)
            pool = np.maximum(pool, yy - BOTTOM)
            pool = np.maximum(pool, TOP - yy)
            field = smooth_union(field, pool, 12)

        alpha = np.round(clamp(0.5 - field / 1.3) * 255).astype(np.uint8)
        rgba = np.empty((*alpha.shape, 4), dtype=np.uint8)
        rgba[:, :, :3] = COLOR
        rgba[:, :, 3] = alpha
        im = Image.fromarray(rgba)
        box = im.getbbox()
        assert box is not None
        im = im.crop(box)
        name = f"flow-{time // STEP:02d}.png"
        im.save(OUT / name, optimize=True)
        cx = -107 + (box[0] + box[2]) / 2
        cy = 235 + (box[1] + box[3]) / 2
        rows.append(f"{name} {time} {cx:.3f} {cy:.3f}")

    (OUT / "layout.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    # A solid circle and a soft, finite bloom halo. Both are plain procedural alpha masks.
    y, x = np.mgrid[:192, :192]
    radius = np.hypot(x - 95.5, y - 95.5) / 95
    for name, alpha in [("halo.png", np.exp(-radius ** 2 * 5) * clamp((1 - radius) * 8)),
                        ("circle.png", clamp((1 - radius) * 96))]:
        im = Image.new("RGBA", (192, 192), "white")
        im.putalpha(Image.fromarray(np.round(alpha * 255).astype(np.uint8)))
        im.save(OUT / name)
    print(f"Built {len(rows)} cropped viscous-liquid frames; shallow-water CFL=0.24")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapset", type=Path, default=Path(r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"))
    args = parser.parse_args()
    build()
    target = args.mapset / "sb" / "memory-flow"
    target.mkdir(parents=True, exist_ok=True)
    for source in OUT.iterdir():
        if source.is_file():
            shutil.copyfile(source, target / source.name)
    # The handoff reuses the real title's glyphs, dots and layout. Preserve installed art.
    title = args.mapset / "sb" / "title"
    title.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "graphics" / "mapset" / "sb" / "title").iterdir():
        destination = title / source.name
        if source.is_file() and not destination.exists():
            shutil.copyfile(source, destination)
    install_seed(args.mapset)
    print(f"Installed liquid textures into {target}")
