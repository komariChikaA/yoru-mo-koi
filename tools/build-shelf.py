# Long circular shelf. Geometry stays put; only the drawn face changes.
import math
import os

import numpy as np
from PIL import Image, ImageDraw

MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
OUT = os.path.join(MAPSET, "sb", "arc-shelf.png")
DASH = os.path.join(MAPSET, "sb", "orbit-dash.png")
PREVIEW = r"../..\_preview\shelf-comp.png"

# Crest stays at design y=400, which the storyboard pins to screen y=386.
# A wider radius carries the same crest out to the 16:9 corners.
CREST_Y = 400.0
R_OUT = 2400.0 / 1.5
# The inner edge has to stay off the lower-left corner while the shelf tilts in from 30°.
R_IN = R_OUT - 460.0
PIVOT_X = 320.0
PIVOT_Y = CREST_Y + R_OUT
HALF = math.radians(96.0)
TH0 = -math.pi / 2 - HALF
TH1 = -math.pi / 2 + HALF
# Output is 1 screen pixel per image pixel. Drawn larger, then reduced, so the arc stays smooth.
OUT_SCALE = 1.5
SS = 4.5
SPRITE_SCALE = 1.0


def pt(r, a):
    return (PIVOT_X + r * math.cos(a), PIVOT_Y + r * math.sin(a))


def window():
    xs, ys = [], []
    for i in range(81):
        a = TH0 + (TH1 - TH0) * i / 80
        for r in (R_IN - 10, R_OUT + 12):
            x, y = pt(r, a)
            xs.append(x)
            ys.append(y)
    pad = 22
    left, top = min(xs) - pad, min(ys) - pad
    right, bottom = max(xs) + pad, max(ys) + pad
    return left, top, right, bottom


LEFT, TOP, RIGHT, BOTTOM = window()


def sp(x, y):
    return ((x - LEFT) * SS, (y - TOP) * SS)


def band(r_out, r_in, a0, a1, n=480):
    outer, inner = [], []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        outer.append(sp(*pt(r_out, a)))
    for i in range(n + 1):
        a = a1 - (a1 - a0) * i / n
        inner.append(sp(*pt(r_in, a)))
    return outer + inner


def shade(color, delta):
    return tuple(max(0, min(255, channel + delta)) for channel in color) + (255,)


def book(draw, theta, r_top, height, thick, color, mark):
    r_bot = r_top - height
    da_o = (thick * 0.5) / r_top
    da_i = (thick * 0.5) / max(40.0, r_bot)

    def quad(r0, r1, f):
        return [
            sp(*pt(r0, theta - da_o * f)),
            sp(*pt(r0, theta + da_o * f)),
            sp(*pt(r1, theta + da_i * f)),
            sp(*pt(r1, theta - da_i * f)),
        ]

    draw.polygon(quad(r_top, r_bot, 1.0), fill=color + (255,))
    page = min(2.6, height * 0.16)
    draw.polygon(quad(r_top, r_top - page, 0.98), fill=(246, 242, 234, 255))
    line = max(1.7, thick * 0.16)
    frac = line / thick
    if mark == 0:
        draw.polygon(
            [
                sp(*pt(r_top - page - 1.0, theta - da_o * frac)),
                sp(*pt(r_top - page - 1.0, theta + da_o * frac)),
                sp(*pt(r_bot + height * 0.18, theta + da_i * frac)),
                sp(*pt(r_bot + height * 0.18, theta - da_i * frac)),
            ],
            fill=shade(color, -34),
        )
    else:
        draw.polygon(
            quad(r_top - page - 1.2, r_top - page - 1.2 - max(3.2, height * 0.22), 0.46),
            fill=shade(color, 30),
        )


def shelf_body(out_w, out_h):
    """Annulus coverage from the circle itself, so the rim is not a polygon staircase."""
    xs = ((np.arange(out_w) + 0.5) / OUT_SCALE + LEFT).astype(np.float32)
    ys = ((np.arange(out_h) + 0.5) / OUT_SCALE + TOP).astype(np.float32)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    r = np.hypot(xx - PIVOT_X, yy - PIVOT_Y)
    ang = np.arctan2(yy - PIVOT_Y, xx - PIVOT_X)
    delta = (ang + np.pi / 2 + np.pi) % (2 * np.pi) - np.pi
    inside = np.minimum(R_OUT - r, r - R_IN)
    inside = np.minimum(inside, (HALF - np.abs(delta)) * np.maximum(r, 1.0))
    # Wider than one pixel so a shallow arc, and the later rotation, does not step.
    alpha = np.clip(0.5 + inside * OUT_SCALE / 1.35, 0.0, 1.0)

    wood = np.array([208, 178, 146], np.float32)
    recess = np.array([196, 164, 132], np.float32)
    lip = np.array([226, 202, 174], np.float32)
    edge = np.array([238, 226, 210], np.float32)
    hair = np.array([156, 128, 102], np.float32)
    rgb = np.broadcast_to(wood, (out_h, out_w, 3)).copy()
    rgb[(r < R_OUT - 33.6) & (r > R_OUT - 52.2)] = recess
    rgb[(r < R_OUT - 5.2) & (r > R_OUT - 27.4)] = recess
    rgb[(r < R_OUT - 28.0) & (r > R_OUT - 32.2)] = lip
    rgb[(r < R_OUT - 28.0) & (r > R_OUT - 29.1)] = edge
    rgb[r > R_OUT - 5.4] = edge
    rgb[r > R_OUT - 4.2] = lip
    rgb[r > R_OUT - 1.5] = hair
    rgb[r < R_IN + 3.2] = lip
    rgb[r < R_IN + 1.6] = hair

    paint_books(rgb, r, ang)
    img = np.zeros((out_h, out_w, 4), np.uint8)
    img[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    img[..., 3] = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def blend(cols, cov, color):
    sel = cov > 0.004
    if not np.any(sel):
        return
    w = cov[sel][:, None]
    src = np.asarray(color, np.float32)
    if src.ndim == 1:
        src = src.reshape(1, 3)
    else:
        src = src[sel]
    cols[sel] = cols[sel] * (1.0 - w) + src * w


def paint_books(rgb, r, ang):
    colors = [
        (126, 168, 198),
        (214, 164, 176),
        (228, 206, 138),
        (168, 156, 198),
        (236, 228, 214),
        (132, 176, 168),
        (176, 196, 214),
        (206, 170, 154),
    ]
    phrase = [
        (18, 10, 0, 0),
        (22, 14, 1, 1),
        (15, 8, 2, 0),
        (20, 16, 3, 0),
        (17, 11, 4, 1),
        (14, 7, 5, 0),
        (24, 13, 6, 0),
        (19, 9, 7, 1),
    ]
    flat = rgb.reshape(-1, 3)

    def row(r_bottom, phase, height_scale):
        recs = []
        theta = TH0 + 0.035
        i = 0
        while theta < TH1 - 0.035:
            height, thick, color_i, mark = phrase[(i + phase) % len(phrase)]
            height *= height_scale
            r_top = r_bottom + height
            r_bot = r_bottom
            center = theta + (thick * 0.5) / r_top
            recs.append((
                r_bot, r_top,
                (thick * 0.5) / max(40.0, r_bot),
                (thick * 0.5) / r_top,
                center, colors[color_i], mark, height, thick,
            ))
            theta += (thick + 1.15) / ((r_top + r_bot) * 0.5)
            i += 1
        r0 = np.array([x[0] for x in recs], np.float32)
        r1 = np.array([x[1] for x in recs], np.float32)
        da0 = np.array([x[2] for x in recs], np.float32)
        da1 = np.array([x[3] for x in recs], np.float32)
        centers = np.array([x[4] for x in recs], np.float32)
        color = np.array([x[5] for x in recs], np.float32)
        mark = np.array([x[6] for x in recs], np.int32)
        height_a = np.array([x[7] for x in recs], np.float32)
        thick_a = np.array([x[8] for x in recs], np.float32)

        band = (r > r_bottom - 1.6) & (r < float(r1.max()) + 1.6)
        idx = np.flatnonzero(band.ravel())
        rr = r.ravel()[idx]
        aa = ang.ravel()[idx]
        j = np.clip(np.searchsorted(centers, aa), 1, len(centers) - 1)
        left = j - 1
        use = np.where(np.abs(aa - centers[left]) <= np.abs(aa - centers[j]), left, j)
        rb, rt = r0[use], r1[use]
        span = np.maximum(rt - rb, 1e-3)
        t = np.clip((rr - rb) / span, 0.0, 1.0)
        half = da0[use] + (da1[use] - da0[use]) * t
        dang = np.abs(aa - centers[use])
        dist = np.minimum(np.minimum(rt - rr, rr - rb), (half - dang) * rr)
        cov = np.clip(0.5 + dist * OUT_SCALE / 1.35, 0.0, 1.0).astype(np.float32)
        cols = flat[idx]
        blend(cols, cov, color[use])

        page = np.minimum(2.6, height_a[use] * 0.16)
        t_page = np.clip((rr - (rt - page)) / np.maximum(page, 1e-3), 0.0, 1.0)
        half_p = (da0[use] + (da1[use] - da0[use]) * t_page) * 0.98
        dist_p = np.minimum(np.minimum(rt - rr, rr - (rt - page)), (half_p - dang) * rr)
        blend(cols, np.clip(0.5 + dist_p * OUT_SCALE / 1.35, 0.0, 1.0).astype(np.float32), (246, 242, 234))

        line = np.maximum(1.7, thick_a[use] * 0.16) / thick_a[use]
        mark0 = mark[use] == 0
        if np.any(mark0):
            top = rt - page - 1.0
            bot = rb + height_a[use] * 0.18
            span_m = np.maximum(top - bot, 1e-3)
            t_m = np.clip((rr - bot) / span_m, 0.0, 1.0)
            half_m = (da0[use] + (da1[use] - da0[use]) * t_m) * line
            dist_m = np.minimum(np.minimum(top - rr, rr - bot), (half_m - dang) * rr)
            dist_m = np.where(mark0, dist_m, -4.0)
            dark = np.clip(color[use] - 34.0, 0, 255)
            blend(cols, np.clip(0.5 + dist_m * OUT_SCALE / 1.35, 0.0, 1.0).astype(np.float32), dark)

        mark1 = mark[use] == 1
        if np.any(mark1):
            block = np.maximum(3.2, height_a[use] * 0.22)
            top = rt - page - 1.2
            bot = top - block
            span_b = np.maximum(block, 1e-3)
            t_b = np.clip((rr - bot) / span_b, 0.0, 1.0)
            half_b = (da0[use] + (da1[use] - da0[use]) * t_b) * 0.46
            dist_b = np.minimum(np.minimum(top - rr, rr - bot), (half_b - dang) * rr)
            dist_b = np.where(mark1, dist_b, -4.0)
            light = np.clip(color[use] + 30.0, 0, 255)
            blend(cols, np.clip(0.5 + dist_b * OUT_SCALE / 1.35, 0.0, 1.0).astype(np.float32), light)
        flat[idx] = cols

    row(R_OUT - 27.2, 0, 0.86)
    row(R_OUT - 51.6, 3, 0.72)


def build():
    out_w = int(round((RIGHT - LEFT) * OUT_SCALE))
    out_h = int(round((BOTTOM - TOP) * OUT_SCALE))
    out = shelf_body(out_w, out_h)
    crest_px = (PIVOT_X - LEFT) / (RIGHT - LEFT) * out_w
    crest_py = (CREST_Y - TOP) / (BOTTOM - TOP) * out_h
    place_x = 320.0 - (crest_px - out_w / 2) * SPRITE_SCALE
    place_y = 386.2 - (crest_py - out_h / 2) * SPRITE_SCALE
    print("shelf", out.size, "area", out_w * out_h)
    print("place", round(place_x, 2), round(place_y, 2), "scale", SPRITE_SCALE)
    out.save(OUT)


def composite():
    shelf = Image.open(OUT).convert("RGBA")
    ren = Image.open(os.path.join(MAPSET, "sb", "ren.png")).convert("RGBA")
    bg = Image.open(os.path.join(MAPSET, "sb", "intro-bg.png")).convert("RGBA")
    canvas = Image.new("RGBA", (854, 480), (232, 244, 248, 255))
    canvas.alpha_composite(bg.resize((854, 480), Image.Resampling.BILINEAR), (0, 0))
    rh = 432
    rw = int(round(ren.size[0] * rh / ren.size[1]))
    girl = ren.resize((rw, rh), Image.Resampling.LANCZOS)
    gx = int(round(320 + 107 - rw / 2))
    gy = int(round(232 - rh / 2))
    canvas.alpha_composite(girl, (gx, gy))
    shelf_s = shelf.resize((shelf.size[0] // 2, shelf.size[1] // 2), Image.Resampling.LANCZOS)
    cx = (LEFT + RIGHT) / 2
    cy = (TOP + BOTTOM) / 2
    px = int(round(cx + 107 - shelf_s.size[0] / 2))
    py = int(round(cy - shelf_s.size[1] / 2))
    canvas.alpha_composite(shelf_s, (px, py))
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    canvas.convert("RGB").save(PREVIEW, quality=90)
    # Crest vs a point 160px to the side, and whether shoes survive.
    spx = shelf_s.load()
    tops = {}
    for name, x in (("mid", int(320 + 107)), ("side", int(480 + 107))):
        for y in range(shelf_s.size[1]):
            if spx[x - px, y][3] > 80:
                tops[name] = py + y
                break
    print("crest", tops)


if __name__ == "__main__":
    build()
