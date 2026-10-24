# Three keyframes for the diagonal band wipe.
# Bands are horizontal in a local sheet, then one rotation covers the 16:9 frame.
import math
import os

from PIL import Image, ImageDraw

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
OUT = os.path.join(ROOT, "_preview", "band-keys")

W, H = 854, 480
ANGLE = 18.0
N = 8
# Whole cover is about half a second. Neighbours are 48ms apart.
DRAW = 208
STAGGER = 48
HOLD = 112
SHRINK = 192
GAP = 48

COLORS = [
    (169, 216, 243, 255),  # #A9D8F3
    (111, 182, 232, 255),  # #6FB6E8
    (201, 228, 242, 255),  # #C9E4F2
    (243, 222, 138, 255),  # #F3DE8A
    (247, 243, 232, 255),  # #F7F3E8
]


def ease_out_cubic(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t ** 3


def sheet_size():
    rad = math.radians(ANGLE)
    c, s = abs(math.cos(rad)), abs(math.sin(rad))
    length = int(math.ceil(W * c + H * s)) + 8
    cross = int(math.ceil(W * s + H * c)) + 8
    # Equal integer pitch, with a little extra so the rotated sheet clears the corners.
    pitch = int(math.ceil(cross / N))
    cross = pitch * N
    return length, cross, pitch


def paint(mode, length, cross, pitch):
    sheet = Image.new("RGBA", (length, cross), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for i in range(N):
        y0 = i * pitch
        y1 = y0 + pitch
        color = COLORS[i % len(COLORS)]
        if mode == "full":
            # One extra pixel so neighbours share an edge after filtering.
            draw.rectangle((0, y0, length, min(cross, y1 + 1)), fill=color)
            continue
        if mode == "cover":
            # Sample where the cascade is halfway across the stack.
            elapsed = 3 * STAGGER + int(DRAW * 0.42)
            p = ease_out_cubic((elapsed - i * STAGGER) / DRAW)
            if p <= 0:
                continue
            # The local right end sits on the right of the frame. Filling back
            # from that end draws the band toward the left.
            x0 = int(round(length * (1.0 - p)))
            draw.rectangle((x0, y0, length, min(cross, y1 + 1)), fill=color)
            continue
        # Shrink in reverse draw order. Sample when the first bands are gone
        # and the middle of the stack is closing.
        order = N - 1 - i
        elapsed = (N // 2) * GAP + int(SHRINK * 0.72)
        u = (elapsed - order * GAP) / SHRINK
        if u >= 1:
            continue
        width = 1.0 - ease_in_cubic(u)
        if width <= 0.012:
            continue
        cy = y0 + pitch / 2.0
        half = pitch * width / 2.0
        top = cy - half
        bot = cy + half
        if width > 0.94:
            top -= 1
            bot += 1
        draw.rectangle((0, top, length, bot), fill=color)
    return sheet


def composite(base, sheet):
    turned = sheet.rotate(ANGLE, resample=Image.BICUBIC, expand=True)
    frame = base.convert("RGBA")
    ox = (frame.width - turned.width) // 2
    oy = (frame.height - turned.height) // 2
    frame.paste(turned, (ox, oy), turned)
    return frame


def uncovered(frame, base):
    a = frame.convert("RGB")
    b = base.convert("RGB")
    holes = 0
    # A hole is a pixel that still matches the page underneath.
    step = 1
    for y in range(0, H, step):
        row_a = [a.getpixel((x, y)) for x in range(0, W, step)]
        row_b = [b.getpixel((x, y)) for x in range(0, W, step)]
        for pa, pb in zip(row_a, row_b):
            if pa == pb:
                holes += 1
    return holes


def fit_cover(path):
    src = Image.open(path).convert("RGB")
    scale = max(W / src.width, H / src.height)
    resized = src.resize((int(round(src.width * scale)), int(round(src.height * scale))), Image.BICUBIC)
    left = (resized.width - W) // 2
    top = (resized.height - H) // 2
    return resized.crop((left, top, left + W, top + H))


def main():
    os.makedirs(OUT, exist_ok=True)
    length, cross, pitch = sheet_size()
    print("sheet", length, cross, "pitch", pitch, "angle", ANGLE)
    current = Image.open(os.path.join(ROOT, "_preview", "band-base", "t012000.png")).convert("RGB")
    nxt = fit_cover(os.path.join(MAPSET, "bg.jpg"))
    specs = (
        ("01-covering", "cover", current),
        ("02-covered", "full", current),
        ("03-shrinking", "shrink", nxt),
    )
    for name, mode, base in specs:
        frame = composite(base, paint(mode, length, cross, pitch))
        frame.convert("RGB").save(os.path.join(OUT, name + ".png"))
        if mode == "full":
            print("full holes", uncovered(frame, base))
        print("wrote", name)


if __name__ == "__main__":
    main()
