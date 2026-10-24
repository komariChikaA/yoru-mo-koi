# Square flip faces. One shared paper front, one back per turning cell.
# Cells are 120px and placed on integer centers so neighbours meet exactly at scale 1.
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
FONT = os.path.join(ROOT, "851CHIKARA-YOWAKU_002.ttf")
OUT = os.path.join(MAPSET, "sb", "flip")

SIDE = 120
COLS = 8
ROWS = 5
OX = 320 - COLS * SIDE // 2
OY = 240 - ROWS * SIDE // 2

WHITE = (255, 255, 255, 255)
BLUE = (186, 224, 242, 255)
YELLOW = (255, 232, 160, 255)
INK = (32, 108, 176, 255)
PAPER = (248, 252, 255, 255)

# hinge, fill, deco, text, wave order. 10 of 40 cells.
FLIPS = [
    (1, 1, "left", BLUE, "dots", None, 0),
    (1, 2, "left", WHITE, None, ("HEIGHT", "153 cm"), 1),
    (1, 3, "left", BLUE, None, ("EYES", "GREEN"), 2),
    (2, 1, "left", YELLOW, "star", None, 3),
    (5, 1, "top", WHITE, None, ("HAIR", "BLONDE"), 0),
    (6, 1, "top", YELLOW, "star", None, 1),
    (5, 2, "top", BLUE, "slash", None, 2),
    (6, 2, "top", YELLOW, None, ("CV.", "藤咲ウサ"), 3),
    (6, 3, "top", WHITE, "dots", None, 4),
    (7, 2, "top", BLUE, "dots", None, 5),
]


def star4(draw, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = -3.14159265 / 2 + i * 3.14159265 / 4
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * __import__("math").cos(ang), cy + rad * __import__("math").sin(ang)))
    draw.polygon(pts, fill=color)


def draw_text(draw, lines):
    size = 28
    pad = 16
    font = None
    blocks = []
    total = 0
    gap = 4
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
        total += gap * (len(lines) - 1)
        if widest <= SIDE - pad and total <= SIDE - pad:
            break
        size -= 1
    else:
        raise SystemExit("text does not fit: " + " ".join(lines))
    y = (SIDE - total) / 2
    for line, left, top, tw, th in blocks:
        draw.text(((SIDE - tw) / 2 - left, y - top), line, font=font, fill=INK)
        y += th + gap


def make_face(fill, deco, lines):
    im = Image.new("RGBA", (SIDE, SIDE), fill)
    draw = ImageDraw.Draw(im)
    if deco == "dots":
        for y in range(28, SIDE - 20, 22):
            for x in range(28, SIDE - 20, 22):
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=INK)
    elif deco == "slash":
        for i in range(-1, 6):
            x = 16 + i * 22
            draw.line((x, SIDE - 18, x + 36, 18), fill=INK, width=3)
    elif deco == "star":
        star4(draw, SIDE / 2, SIDE / 2, 28, (232, 176, 48, 255))
    if lines:
        draw_text(draw, lines)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name.endswith(".png") or name == "layout.txt":
            os.remove(os.path.join(OUT, name))
    Image.new("RGBA", (SIDE, SIDE), PAPER).save(os.path.join(OUT, "paper.png"))
    lines = []
    for index, (col, row, hinge, fill, deco, text, order) in enumerate(FLIPS):
        face = make_face(fill, deco, text)
        if face.size != (SIDE, SIDE):
            raise SystemExit("bad size")
        name = f"b{index:02d}.png"
        face.save(os.path.join(OUT, name))
        cx = OX + col * SIDE + SIDE / 2
        cy = OY + row * SIDE + SIDE / 2
        lines.append(f"{hinge} sb/flip/{name} {cx:.2f} {cy:.2f} {order}")
    with open(os.path.join(OUT, "layout.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("flip cells", len(lines), "side", SIDE)


if __name__ == "__main__":
    main()
