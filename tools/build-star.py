# Concave four-point star for the post-Movie transition.
# Tips are sharp. Each edge is one smooth inward cubic Bezier.
import math
import os

from PIL import Image, ImageDraw

MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
OUT = os.path.join(MAPSET, "sb")
PREVIEW = r"../..\_preview"


def bezier(p0, p1, p2, p3, steps):
    pts = []
    for i in range(steps):
        t = i / steps
        u = 1.0 - t
        x = u ** 3 * p0[0] + 3 * u ** 2 * t * p1[0] + 3 * u * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u ** 2 * t * p1[1] + 3 * u * t ** 2 * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def star_points(cx, cy, r_out, r_in, steps=48):
    pts = []
    for i in range(4):
        a0 = -math.pi / 2 + i * math.pi / 2
        a1 = a0 + math.pi / 2
        p0 = (cx + r_out * math.cos(a0), cy + r_out * math.sin(a0))
        p3 = (cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        c1 = a0 + math.radians(28)
        c2 = a1 - math.radians(28)
        p1 = (cx + r_in * math.cos(c1), cy + r_in * math.sin(c1))
        p2 = (cx + r_in * math.cos(c2), cy + r_in * math.sin(c2))
        pts.extend(bezier(p0, p1, p2, p3, steps))
    return pts


def min_radius(pts, cx, cy):
    return min(math.hypot(x - cx, y - cy) for x, y in pts)


def draw_star(size, r_out, r_in, ss=4):
    big = size * ss
    cx = cy = big / 2
    pts = star_points(cx, cy, r_out * ss, r_in * ss)
    im = Image.new("L", (big, big), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return im.resize((size, size), Image.Resampling.LANCZOS), min_radius(pts, cx, cy) / ss


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)

    filled_size = 768
    filled, filled_min = draw_star(filled_size, 360, 132)
    star = Image.new("RGBA", (filled_size, filled_size), (0, 0, 0, 0))
    star.putalpha(filled)
    # white RGB where visible
    px = star.load()
    for y in range(filled_size):
        for x in range(filled_size):
            a = px[x, y][3]
            if a:
                px[x, y] = (255, 255, 255, a)
    star.save(os.path.join(OUT, "star-concave.png"))

    win_size = 1280
    hole, hole_min = draw_star(win_size, 210, 78)
    window = Image.new("RGBA", (win_size, win_size), (255, 255, 255, 255))
    wpx = window.load()
    hpx = hole.load()
    for y in range(win_size):
        for x in range(win_size):
            a = hpx[x, y]
            if a:
                # hole: previous white alpha is reduced by the star coverage
                wpx[x, y] = (255, 255, 255, 255 - a)
    window.save(os.path.join(OUT, "star-open.png"))

    corner = 510.0
    print(f"filled {filled_size} minR {filled_min:.2f} coverScale {corner / filled_min:.3f}")
    print(f"window {win_size} holeMin {hole_min:.2f}")
    print(f"window startScale {corner / (win_size / 2):.3f} endScale {corner / hole_min:.3f}")

    preview = Image.new("RGBA", (768, 768), (40, 170, 168, 255))
    preview.alpha_composite(star)
    preview.convert("RGB").save(os.path.join(PREVIEW, "star-concave.png"), quality=92)


if __name__ == "__main__":
    main()
