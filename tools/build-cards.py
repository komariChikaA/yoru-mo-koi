# Intro info cards. Flat rounded panels, binder margin and punch holes.
# Drawn at 4x and saved at 2x, so the storyboard scale is 0.5.
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
FONT = os.path.join(ROOT, "851CHIKARA-YOWAKU_002.ttf")
OUT = os.path.join(MAPSET, "sb")
S = 4

FILL = (246, 251, 254, 255)
MARGIN = (226, 240, 248, 255)
BORDER = (78, 158, 206, 255)
HOLE_RING = (58, 142, 198, 255)
HOLE = (190, 222, 236, 255)
YELLOW = (255, 226, 132, 255)
INK = (36, 122, 194, 255)
LINE = (168, 208, 230, 255)
DOT = (112, 180, 210, 255)
STAR = (255, 206, 88, 255)


def star4(draw, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.38
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def holes(draw, x, ys, r):
    for y in ys:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=HOLE_RING)
        inner = r * 0.52
        draw.ellipse((x - inner, y - inner, x + inner, y + inner), fill=HOLE)


def label(draw, text, box, size, fill):
    font = ImageFont.truetype(FONT, size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    x = box[0] + (box[2] - box[0] - tw) / 2 - left
    y = box[1] + (box[3] - box[1] - th) / 2 - top
    draw.text((x, y), text, font=font, fill=fill)


def card(name, design_w, design_h, hinge_right):
    w, h = design_w * S, design_h * S
    margin = 34 * S
    radius = 18 * S
    border = 7
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=radius, fill=MARGIN)
    if hinge_right:
        draw.rounded_rectangle((1, 1, w - margin + radius, h - 2), radius=radius, fill=FILL)
        seam = w - margin
    else:
        draw.rounded_rectangle((margin - radius, 1, w - 2, h - 2), radius=radius, fill=FILL)
        seam = margin
    draw.line((seam, 28 * S, seam, h - 28 * S), fill=LINE, width=S)
    hole_x = (w - margin / 2) if hinge_right else margin / 2
    holes(draw, hole_x, (h * 0.40, h * 0.54, h * 0.68), 7 * S)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=radius, outline=BORDER, width=border)
    return im, draw, seam


def build_left():
    im, draw, seam = card("left", 240, 258, True)
    bar = (22 * S, 20 * S, seam - 18 * S, 52 * S)
    draw.rounded_rectangle(bar, radius=8 * S, fill=YELLOW)
    label(draw, "PROFILE", bar, 16 * S, INK)
    y = 70 * S
    draw.line((22 * S, y, seam - 18 * S, y), fill=LINE, width=S + 2)
    ox, oy = 36 * S, 96 * S
    for row in range(3):
        for col in range(3):
            cx = ox + col * 16 * S
            cy = oy + row * 16 * S
            draw.ellipse((cx - 2.2 * S, cy - 2.2 * S, cx + 2.2 * S, cy + 2.2 * S), fill=DOT)
    star4(draw, 168 * S, 150 * S, 11 * S, STAR)
    draw.arc((150 * S, 186 * S, 214 * S, 250 * S), 200, 340, fill=LINE, width=S + 3)
    save(im, "card-left.png")


def build_right():
    im, draw, seam = card("right", 178, 208, False)
    bar = (seam + 16 * S, 18 * S, im.size[0] - 20 * S, 48 * S)
    draw.rounded_rectangle(bar, radius=8 * S, fill=YELLOW)
    label(draw, "NOTE", bar, 15 * S, INK)
    y = 66 * S
    draw.line((seam + 16 * S, y, im.size[0] - 20 * S, y), fill=LINE, width=S + 2)
    star4(draw, seam + 36 * S, 108 * S, 9 * S, STAR)
    ox, oy = seam + 62 * S, 96 * S
    for row in range(2):
        for col in range(3):
            cx = ox + col * 14 * S
            cy = oy + row * 16 * S
            draw.ellipse((cx - 2 * S, cy - 2 * S, cx + 2 * S, cy + 2 * S), fill=DOT)
    draw.arc((seam + 28 * S, 132 * S, seam + 96 * S, 196 * S), 20, 160, fill=LINE, width=S + 2)
    save(im, "card-right.png")


def save(im, name):
    out = im.resize((im.size[0] // 2, im.size[1] // 2), Image.Resampling.LANCZOS)
    path = os.path.join(OUT, name)
    out.save(path)
    print(name, out.size)


if __name__ == "__main__":
    build_left()
    build_right()
