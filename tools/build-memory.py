"""Build Memory's flat illustration and five erasing planes (never crop the CG).

Run: python tools/build-memory.py [--mapset PATH]
Textures are kept in assets/memory-v2 and installed into the beatmap's sb folder.
"""
from pathlib import Path
import argparse
import shutil
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "memory-v2"
W, H, SS = 640, 403, 3
FRAMES, STEP = 72, 35


def illustration():
    im = Image.new("RGB", (W * SS, H * SS), "#b8c5bf")
    d = ImageDraw.Draw(im)

    def ellipse(box, color):
        d.ellipse([round(v * SS) for v in box], fill=color)

    def rounded_shape(points, radius, color):
        # Round each turn with a quadratic curve; preserve the previous mass/proportion.
        vertices = np.array(points, dtype=float)
        path = []
        for i, corner in enumerate(vertices):
            previous, following = vertices[i - 1], vertices[(i + 1) % len(vertices)]
            incoming, outgoing = previous - corner, following - corner
            a_len, b_len = np.linalg.norm(incoming), np.linalg.norm(outgoing)
            trim = min(radius, a_len * 0.35, b_len * 0.35)
            a, b = corner + incoming * trim / a_len, corner + outgoing * trim / b_len
            for t in np.linspace(0, 1, 13):
                point = (1 - t) ** 2 * a + 2 * (1 - t) * t * corner + t ** 2 * b
                path.append(tuple(np.round(point * SS).astype(int)))
        d.polygon(path, fill=color)

    # Return to the simple filled house, with softer masses and no linework.
    # Woodland and light use large off-canvas ellipses, independent of reveal seams.
    ellipse((-210, -190, 470, 345), "#d8dfc7")
    ellipse((-112, -125, 112, 133), "#92a5a0")
    ellipse((476, -105, 826, 322), "#92a5a0")
    # One broad, shallow arc replaces the angular ground horizon.
    ellipse((-370, 286, 1010, 1080), "#a8af96")
    # Same wall, shed, roof and eave arrangement as the simple version.
    rounded_shape([(533, 218), (600, 243), (600, 322), (533, 333)], 14, "#a59980")
    # Slight overlap beneath the roof prevents a pale gap after rounding its peak.
    rounded_shape([(121, 148), (421, 6), (534, 153), (534, 333), (121, 333)], 18, "#b3a789")
    rounded_shape([(47, 171), (422, 2), (589, 205), (574, 202), (421, 18), (63, 178)], 7, "#858674")
    rounded_shape([(202, 111), (523, 108), (539, 126), (205, 128)], 8, "#d0c2a3")
    d.rounded_rectangle([357 * SS, 138 * SS, 444 * SS, 333 * SS],
                        radius=12 * SS, fill="#8c846e")
    return im.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    art = illustration()
    art.save(OUT / "abstract.png")
    pixels = np.array(art)
    yy, xx = np.mgrid[:H, :W]
    diagonal = xx - 0.34 * yy
    # Five unequal large planes. Each erases in place with a different sweep.
    edges = [-150, 65, 203, 293, 461, 641]
    timings = [(550, 700), (760, 890), (1090, 570), (1330, 880), (1620, 850)]
    directions = [yy, xx + 0.55 * yy, yy, H - yy, xx + 0.55 * yy]
    masks = [(diagonal >= edges[i]) & (diagonal < edges[i + 1]) for i in range(5)]
    ranges = [(float(v[m].min()) - 3, float(v[m].max()) + 3)
              for v, m in zip(directions, masks)]
    areas = []
    for frame in range(FRAMES):
        alpha = np.zeros((H, W), dtype=np.float32)
        for mask, coord, (lo, hi), (start, duration) in zip(masks, directions, ranges, timings):
            u = np.clip((frame * STEP - start) / duration, 0, 1)
            eased = u * u * (3 - 2 * u)
            edge = lo + (hi - lo) * eased
            a = np.clip((coord - edge) / 2.0, 0, 1)
            alpha[mask] = a[mask]
        output = pixels.copy()
        output[:, :, 3] = np.round(alpha * 255).astype(np.uint8)
        Image.fromarray(output).save(OUT / f"reveal-{frame:02d}.png", optimize=True)
        areas.append(float(alpha.mean()))
    assert all(a >= b for a, b in zip(areas, areas[1:])), "Reveal must be monotonic"
    assert areas[0] == 1.0 and areas[-1] == 0.0
    # The final page has two broad fields, only introduced during the camera move.
    wedge = Image.new("RGBA", (854, 480))
    ImageDraw.Draw(wedge).polygon([(411, 480), (411, 368), (854, 227), (854, 480)], fill="#c7d1d0")
    wedge.save(OUT / "page-field.png")
    print(f"Built {FRAMES} overlay frames; opaque coverage {areas[0]:.0%} -> {areas[-1]:.0%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapset", type=Path, default=Path(r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"))
    args = parser.parse_args()
    build()
    target = args.mapset / "sb" / "memory-v2"
    target.mkdir(parents=True, exist_ok=True)
    for source in OUT.glob("*.png"):
        shutil.copyfile(source, target / source.name)
    cg = args.mapset / "sb" / "secret-base.png"
    if not cg.exists():
        shutil.copyfile(ROOT / "graphics" / "mapset" / "sb" / "secret-base.png", cg)
    pixel = args.mapset / "sb" / "px.png"
    if not pixel.exists():
        shutil.copyfile(ROOT / "graphics" / "mapset" / "sb" / "px.png", pixel)
    print(f"Installed Memory textures: {target}")
