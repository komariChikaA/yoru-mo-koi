# Continuous 16 by 9 square grid behind the character.
# Every cell is its own square. Information is split across adjacent cells.
# This pass is the fully open static layout. Flips come after the grid is confirmed.
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
FONT = os.path.join(ROOT, "851CHIKARA-YOWAKU_002.ttf")
OUT = os.path.join(MAPSET, "sb", "pages")
SS = 2
OX = -107.0
OY = 0.0
# 9 rows fill the frame height. The same edge is used for columns, so every cell is a square.
CELL = 480.0 / 9.0
GUTTER = 0.0

WHITE = (255, 255, 255, 235)
BLUE = (176, 220, 242, 228)
YELLOW = (255, 228, 138, 240)
GHOST = (186, 222, 240, 78)
BORDER = (42, 124, 196, 255)
INK = (32, 108, 176, 255)
INK_SOFT = (70, 150, 206, 255)


def rect_for(col, row, n):
    side = n * CELL - 2 * GUTTER
    x0 = OX + col * CELL + GUTTER
    y0 = OY + row * CELL + GUTTER
    return x0, y0, x0 + side, y0 + side


def star4(draw, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.38
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def paint(kind, draw, w, h):
    s = SS
    if kind == "dots":
        step = 14 * s
        r = 2.1 * s
        for y in range(int(16 * s), h - int(12 * s), step):
            for x in range(int(16 * s), w - int(12 * s), step):
                draw.ellipse((x - r, y - r, x + r, y + r), fill=INK_SOFT)
    elif kind == "rules":
        y = h * 0.38
        for i in range(3):
            draw.line((18 * s, y, w - 18 * s, y), fill=INK_SOFT, width=max(2, s))
            y += 12 * s
    elif kind == "star":
        star4(draw, w * 0.5, h * 0.5, min(w, h) * 0.22, (255, 196, 72, 255))
    elif kind == "diamond":
        cx, cy = w * 0.5, h * 0.5
        r = min(w, h) * 0.22
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=INK_SOFT)
    elif kind == "slash":
        gap = 16 * s
        for i in range(-2, 6):
            x = 20 * s + i * gap
            draw.line((x, h - 12 * s, x + 28 * s, 12 * s), fill=INK_SOFT, width=max(2, s))
    elif kind == "arc":
        draw.arc((w * 0.18, h * 0.15, w * 0.82, h * 0.95), 200, 340, fill=INK_SOFT, width=max(2, s + 1))


def draw_text(draw, lines, w, h, size):
    pad = 10 * SS
    blocks = []
    font = None
    while size >= 8:
        font = ImageFont.truetype(FONT, size * SS)
        blocks = []
        total = 0
        widest = 0
        for line in lines:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            tw, th = right - left, bottom - top
            blocks.append((line, left, top, tw, th))
            total += th
            widest = max(widest, tw)
        gap = 3 * SS
        total += gap * (len(blocks) - 1)
        if widest <= w - pad and total <= h - pad:
            break
        size -= 1
    gap = 3 * SS
    total = sum(block[4] for block in blocks) + gap * (len(blocks) - 1)
    y = (h - total) / 2
    for line, left, top, tw, th in blocks:
        draw.text(((w - tw) / 2 - left, y - top), line, font=font, fill=INK)
        y += th + gap


def make(index, col, row, n, fill, lines=None, deco=None, size=15):
    x0, y0, x1, y1 = rect_for(col, row, n)
    side = max(8, int(round((x1 - x0) * SS)))
    pw = ph = side
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, pw - 1, ph - 1), fill=fill)
    draw.rectangle((1, 1, pw - 2, ph - 2), outline=BORDER, width=max(2, SS))
    if deco:
        paint(deco, draw, pw, ph)
    if lines:
        draw_text(draw, lines, pw, ph, size)
    name = f"p{index:02d}.png"
    im.save(os.path.join(OUT, name))
    back_fill = YELLOW if fill == BLUE else BLUE if fill == YELLOW else (255, 236, 176, 240) if fill == WHITE else (255, 228, 138, 220)
    back = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    back_draw = ImageDraw.Draw(back)
    back_draw.rectangle((0, 0, pw - 1, ph - 1), fill=back_fill)
    back_draw.rectangle((1, 1, pw - 2, ph - 2), outline=BORDER, width=max(2, SS))
    if deco:
        paint(deco, back_draw, pw, ph)
    if lines:
        draw_text(back_draw, lines, pw, ph, size)
    back_name = f"b{index:02d}.png"
    back.save(os.path.join(OUT, back_name))
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    return name, back_name, cx, cy


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name.endswith(".png") or name == "layout.txt":
            os.remove(os.path.join(OUT, name))

    cells = {}

    def put(col, row, fill, lines=None, deco=None, size=13):
        cells[(col, row)] = (fill, lines, deco, size)

    def quiet(col, row):
        return BLUE if (col + row) % 3 == 0 else WHITE

    for col in range(16):
        put(col, 0, quiet(col, 0))
        put(col, 1, quiet(col, 1))
    for row in range(2, 6):
        for col in list(range(0, 5)) + list(range(11, 16)):
            put(col, row, quiet(col, row))
    for col in (0, 1, 2, 13, 14, 15):
        put(col, 6, quiet(col, 6))
    for col in (0, 1, 14, 15):
        put(col, 7, GHOST)

    put(0, 0, YELLOW, ["PROFILE"], size=11)
    put(1, 0, YELLOW, ["01"], size=14)
    put(2, 0, BLUE, deco="dots")
    put(4, 0, BLUE, deco="rules")
    put(6, 0, WHITE, ["OTOHARA"], size=10)
    put(7, 0, WHITE, ["REN"], size=14)
    put(9, 0, BLUE, deco="rules")
    put(12, 0, YELLOW, ["CHARACTER"], size=9)
    put(13, 0, YELLOW, ["DATA"], size=12)
    put(14, 0, YELLOW, ["02"], size=14)
    put(15, 0, BLUE, deco="dots")

    put(0, 2, WHITE, ["HEIGHT"], size=11)
    put(1, 2, WHITE, ["153 cm"], size=11)
    put(2, 2, WHITE, deco="star")
    put(3, 2, BLUE, deco="diamond")

    put(0, 3, BLUE, ["EYES"], size=12)
    put(1, 3, BLUE, ["GREEN"], size=11)
    put(2, 3, YELLOW, ["SHY"], size=14)
    put(3, 3, BLUE, deco="diamond")

    put(0, 4, WHITE, ["HARD-"], size=12)
    put(1, 4, WHITE, ["WORKING"], size=10)
    put(2, 4, BLUE, deco="slash")

    put(0, 5, BLUE, ["FAMILY"], size=11)
    put(1, 5, BLUE, ["ORIENTED"], size=9)
    put(2, 5, WHITE, deco="arc")
    put(3, 5, BLUE, deco="dots")

    put(12, 2, WHITE, ["HAIR"], size=12)
    put(13, 2, WHITE, ["BLONDE"], size=10)
    put(14, 2, BLUE, deco="dots")
    put(15, 2, WHITE, deco="star")

    put(12, 3, WHITE, ["AI'S"], size=12)
    put(13, 3, WHITE, ["YOUNGER"], size=9)
    put(14, 3, WHITE, ["SISTER"], size=10)
    put(15, 3, BLUE, deco="star")

    put(12, 4, YELLOW, ["CV."], size=13)
    put(13, 4, YELLOW, ["藤咲ウサ"], size=11)
    put(14, 4, BLUE, deco="diamond")
    put(15, 4, BLUE, deco="dots")

    put(12, 5, YELLOW, ["IMAGE"], size=11)
    put(13, 5, YELLOW, ["COLOR"], size=10)
    put(14, 5, YELLOW, ["SAKURA"], size=9)
    put(15, 5, YELLOW, ["PINK"], size=12)

    put(0, 6, GHOST, deco="slash")
    put(1, 6, BLUE, deco="diamond")
    put(2, 6, GHOST, deco="arc")
    put(13, 6, WHITE, ["SAKURA"], size=9)
    put(14, 6, WHITE, ["COLOR"], size=10)
    put(15, 6, WHITE, ["BELL"], size=12)

    lines = []
    for index, (col, row) in enumerate(sorted(cells, key=lambda item: (item[1], item[0]))):
        fill, text, deco, size = cells[(col, row)]
        name, _back, cx, cy = make(index, col, row, 1, fill, text, deco, size)
        lines.append(f"page sb/pages/{name} {cx:.2f} {cy:.2f}")
    with open(os.path.join(OUT, "layout.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    sides = set()
    for name in os.listdir(OUT):
        if not name.startswith("p") or not name.endswith(".png"):
            continue
        with Image.open(os.path.join(OUT, name)) as im:
            if im.size[0] != im.size[1]:
                raise SystemExit(f"not square {name} {im.size}")
            sides.add(im.size)
    print("pages", len(lines), "sides", sorted(sides))


if __name__ == "__main__":
    main()
