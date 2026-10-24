# Three acceptance frames for the seamless flip background.
# The live storyboard stays on the unflipped scene until these frames are confirmed.
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
FONT = os.path.join(ROOT, "851CHIKARA-YOWAKU_002.ttf")
OUT = os.path.join(ROOT, "_preview", "flip-keys")

# One edge length. 8 by 5 squares, centered on the widescreen, running off the frame.
SIDE = 120
COLS = 8
ROWS = 5
OX = 320 - COLS * SIDE // 2
OY = 240 - ROWS * SIDE // 2
PIVOT = (320.0, 900.0)

WHITE = (255, 255, 255, 255)
BLUE = (186, 224, 242, 255)
YELLOW = (255, 232, 160, 255)
INK = (32, 108, 176, 255)
PAPER = (248, 252, 255, 230)

# About a quarter of the cells turn. Same hinge direction inside each cluster.
FLIPS = {
    (1, 1): ("left", BLUE, "dots", None, 0),
    (1, 2): ("left", WHITE, None, ("HEIGHT", "153 cm"), 1),
    (1, 3): ("left", BLUE, None, ("EYES", "GREEN"), 2),
    (2, 1): ("left", YELLOW, "star", None, 3),
    (5, 1): ("top", WHITE, None, ("HAIR", "BLONDE"), 0),
    (6, 1): ("top", YELLOW, "star", None, 1),
    (5, 2): ("top", BLUE, "slash", None, 2),
    (6, 2): ("top", YELLOW, None, ("CV.", "藤咲ウサ"), 3),
    (6, 3): ("top", WHITE, "dots", None, 4),
    (7, 2): ("top", BLUE, "dots", None, 5),
}


def pose(x, y, alpha):
    delta = math.radians(alpha - 90.0)
    dx = x - PIVOT[0]
    up = PIVOT[1] - y
    cos = math.cos(delta)
    sin = math.sin(delta)
    return (
        PIVOT[0] + dx * cos - up * sin,
        PIVOT[1] - (dx * sin + up * cos),
    )


def star4(draw, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def fit_text(draw, lines, size):
    pad = 16
    while size >= 12:
        font = ImageFont.truetype(FONT, size)
        blocks = []
        widest = 0
        total = 0
        for line in lines:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            tw, th = right - left, bottom - top
            blocks.append((line, left, top, tw, th))
            widest = max(widest, tw)
            total += th
        gap = 4
        total += gap * (len(lines) - 1)
        if widest <= SIDE - pad and total <= SIDE - pad:
            return font, blocks, total, gap
        size -= 1
    raise SystemExit("text does not fit: " + " ".join(lines))


def make_face(fill, deco, lines):
    im = Image.new("RGBA", (SIDE, SIDE), fill)
    draw = ImageDraw.Draw(im)
    ink = INK
    if deco == "dots":
        for y in range(28, SIDE - 20, 22):
            for x in range(28, SIDE - 20, 22):
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=ink)
    elif deco == "slash":
        for i in range(-1, 6):
            x = 16 + i * 22
            draw.line((x, SIDE - 18, x + 36, 18), fill=ink, width=3)
    elif deco == "star":
        star4(draw, SIDE / 2, SIDE / 2, 28, (232, 176, 48, 255))
    if lines:
        font, blocks, total, gap = fit_text(draw, lines, 28)
        y = (SIDE - total) / 2
        for line, left, top, tw, th in blocks:
            draw.text(((SIDE - tw) / 2 - left, y - top), line, font=font, fill=ink)
            y += th + gap
    return im


def hinge_quad(x, y, hinge, progress):
    # progress 0 is flat, 0.5 is edge-on, 1 is the back fully open.
    span = abs(math.cos(progress * math.pi))
    pinch = math.sin(progress * math.pi)
    inset = SIDE * 0.16 * pinch
    reach = SIDE * span
    if hinge == "left":
        return [
            (x, y),
            (x + reach, y + inset),
            (x + reach, y + SIDE - inset),
            (x, y + SIDE),
        ]
    return [
        (x, y),
        (x + SIDE, y),
        (x + SIDE - inset, y + reach),
        (x + inset, y + reach),
    ]


def find_coeffs(origin, target):
    matrix = []
    vector = []
    for (sx, sy), (dx, dy) in zip(origin, target):
        matrix.append([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy])
        matrix.append([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy])
        vector.append(dx)
        vector.append(dy)
    return np.linalg.solve(np.array(matrix, dtype=np.float64), np.array(vector, dtype=np.float64))


def paint_cell(sheet, origin, face, quad):
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    if max(xs) - min(xs) < 1.2 and max(ys) - min(ys) < 1.2:
        return
    # Full squares are copied on integer pixels so neighbours share an edge.
    full = all(abs(quad[i][0] - (origin[0] + SIDE * (i in (1, 2))) ) < 0.01 and
               abs(quad[i][1] - (origin[1] + SIDE * (i in (2, 3))) ) < 0.01
               for i in range(4))
    if full:
        sheet.paste(face, (int(origin[0]), int(origin[1])))
        return
    minx = int(math.floor(min(xs)))
    miny = int(math.floor(min(ys)))
    maxx = int(math.ceil(max(xs)))
    maxy = int(math.ceil(max(ys)))
    bw = max(1, maxx - minx)
    bh = max(1, maxy - miny)
    local = [(p[0] - minx, p[1] - miny) for p in quad]
    src = [(0, 0), (SIDE, 0), (SIDE, SIDE), (0, SIDE)]
    coeffs = find_coeffs(local, src)
    warped = face.transform((bw, bh), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    sheet.alpha_composite(warped, (minx, miny))


def build_sheet(mode):
    # Rest-space sheet. Pixel (0, 0) is screen (-400, -200).
    ox, oy = -400, -200
    sheet = Image.new("RGBA", (1500, 1000), (0, 0, 0, 0))
    if mode == "seamless":
        return sheet, ox, oy
    for (col, row), (hinge, fill, deco, text, order) in FLIPS.items():
        if mode == "mid":
            progress = 0.22 + order * 0.12
        else:
            progress = 1.0
        x = OX + col * SIDE
        y = OY + row * SIDE
        if progress < 0.5:
            face = Image.new("RGBA", (SIDE, SIDE), PAPER)
        else:
            face = make_face(fill, deco, text)
        quad = hinge_quad(x, y, hinge, progress)
        local_origin = (int(round(x - ox)), int(round(y - oy)))
        local_quad = [(px - ox, py - oy) for px, py in quad]
        paint_cell(sheet, local_origin, face, local_quad)
    return sheet, ox, oy


def affine_to_preview(sheet, ox, oy, alpha):
    delta = math.radians(alpha - 90.0)
    cos = math.cos(delta)
    sin = math.sin(delta)
    # Preview pixel (px, py) -> sheet pixel. Derived from the scene pose inverse.
    coeffs = (
        cos,
        -sin,
        320 - ox - 427 * cos + 900 * sin,
        sin,
        cos,
        900 - oy - 427 * sin - 900 * cos,
    )
    return sheet.transform((854, 480), Image.Transform.AFFINE, coeffs, Image.Resampling.BICUBIC)


def blit_sprite(canvas, image, rest_x, rest_y, scale, alpha):
    resized = image.resize(
        (max(1, int(round(image.size[0] * scale))), max(1, int(round(image.size[1] * scale)))),
        Image.Resampling.LANCZOS,
    )
    turned = resized.rotate(alpha - 90.0, resample=Image.Resampling.BICUBIC, expand=True)
    cx, cy = pose(rest_x, rest_y, alpha)
    canvas.alpha_composite(turned, (int(round(cx + 107 - turned.size[0] / 2)), int(round(cy - turned.size[1] / 2))))


def stamp_foreground(canvas, alpha):
    ren = Image.open(os.path.join(MAPSET, "sb", "ren.png")).convert("RGBA")
    ren_scale = (432.0 / ren.size[1]) * 1.5
    blit_sprite(canvas, ren, 320, 428, ren_scale, alpha)

    shelf = Image.open(os.path.join(MAPSET, "sb", "arc-shelf.png")).convert("RGBA")
    blit_sprite(canvas, shelf, 320, 896, 0.75, alpha)

    layout = os.path.join(MAPSET, "sb", "ren-name", "layout.txt")
    for raw in open(layout, encoding="utf-8"):
        parts = raw.split()
        if not parts or parts[0] != "slice":
            continue
        glyph = Image.open(os.path.join(MAPSET, "sb", "ren-name", os.path.basename(parts[2]))).convert("RGBA")
        blit_sprite(canvas, glyph, float(parts[3]), float(parts[4]), 0.5, alpha)


def main():
    os.makedirs(OUT, exist_ok=True)
    # Hold pose at 12s: 80° plus the slow cruise toward 100°.
    arrived = 9958
    hold_ms = 13000 - arrived
    alpha = 80.0 + 20.0 * (12000 - arrived) / hold_ms
    base = Image.open(os.path.join(OUT, "t012000.png")).convert("RGBA")
    frames = (
        ("01-seamless", "seamless"),
        ("02-midflip", "mid"),
        ("03-revealed", "revealed"),
    )
    for name, mode in frames:
        sheet, sox, soy = build_sheet(mode)
        grid = affine_to_preview(sheet, sox, soy, alpha)
        frame = base.copy()
        frame.alpha_composite(grid)
        stamp_foreground(frame, alpha)
        path = os.path.join(OUT, name + ".png")
        frame.convert("RGB").save(path)
        print(name, "alpha", round(alpha, 2), path)


if __name__ == "__main__":
    main()
