# Name card. One sprite per glyph, drawn big and scaled to 0.5 in the storyboard.
# The outline is a round dilation, not a stack of thin vertical strips.
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"../.."
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
FONT = os.path.join(ROOT, "851CHIKARA-YOWAKU_002.ttf")
OUT = os.path.join(MAPSET, "sb", "ren-name")
LAYOUT = os.path.join(OUT, "layout.txt")
SS = 8
OUT_SCALE = 2

MAIN_FILL = (255, 216, 32, 255)
MAIN_STROKE = (28, 122, 206, 255)
SUB_FILL = (255, 228, 110, 255)
SUB_STROKE = (78, 156, 214, 255)


def dilate(alpha, radius):
    src = np.asarray(alpha, dtype=np.uint8)
    height, width = src.shape
    padded = np.pad(src, radius, mode="constant")
    acc = np.zeros((height, width), dtype=np.uint8)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            y0 = radius + dy
            x0 = radius + dx
            acc = np.maximum(acc, padded[y0:y0 + height, x0:x0 + width])
    return Image.fromarray(acc, "L")


def glyph_image(ch, font, fill, stroke_rgb, radius):
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    left, top, right, bottom = probe.textbbox((0, 0), ch, font=font)
    pad = radius + 4
    size = (right - left + pad * 2, bottom - top + pad * 2)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((pad - left, pad - top), ch, font=font, fill=255)
    outline = dilate(mask, radius)
    stroke = Image.new("RGBA", size, stroke_rgb)
    stroke.putalpha(outline)
    ink = Image.new("RGBA", size, fill)
    ink.putalpha(mask)
    stroke.alpha_composite(ink)
    bbox = stroke.split()[-1].getbbox()
    return stroke.crop(bbox)


def to_screen(im):
    w = max(1, round(im.size[0] / SS * OUT_SCALE))
    h = max(1, round(im.size[1] / SS * OUT_SCALE))
    return im.resize((w, h), Image.Resampling.LANCZOS)


def emit_line(text, font, fill, stroke_rgb, radius, tracking, space, kind, y, lines):
    parts = []
    for ch in text:
        if ch == " ":
            parts.append(space)
            continue
        parts.append(glyph_image(ch, font, fill, stroke_rgb, radius))
    width = 0.0
    for part in parts:
        width += part if isinstance(part, (int, float)) else part.size[0] / SS + tracking
    if parts and not isinstance(parts[-1], (int, float)):
        width -= tracking
    line_h = max((part.size[1] / SS for part in parts if not isinstance(part, (int, float))), default=1)
    pen = 320.0 - width / 2.0
    index = 0
    for part in parts:
        if isinstance(part, (int, float)):
            pen += part
            continue
        im = to_screen(part)
        screen_w = part.size[0] / SS
        screen_h = part.size[1] / SS
        name = f"{kind}-{index:03d}.png"
        im.save(os.path.join(OUT, name))
        cx = pen + screen_w / 2.0
        cy = y + (line_h - screen_h) / 2.0
        lines.append(f"slice {kind} sb/ren-name/{name} {cx:.2f} {cy:.2f}")
        pen += screen_w + tracking
        index += 1
    return width, index


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name.endswith(".png"):
            os.remove(os.path.join(OUT, name))

    main_font = ImageFont.truetype(FONT, 52 * SS)
    sub_font = ImageFont.truetype(FONT, 26 * SS)
    lines = []
    main_y = 328.0
    sub_y = 378.0
    main_w, main_n = emit_line("乙原 恋", main_font, MAIN_FILL, MAIN_STROKE, 22, 6, 16, "m", main_y, lines)
    sub_w, sub_n = emit_line("Otohara Ren", sub_font, SUB_FILL, SUB_STROKE, 12, 1.5, 8, "s", sub_y, lines)
    gap = 10
    bar_w = 26
    left = 320.0 - sub_w / 2.0 - gap
    right = 320.0 + sub_w / 2.0 + gap
    lines.append(f"rule left {left:.2f} {sub_y:.2f} {bar_w}")
    lines.append(f"rule right {right:.2f} {sub_y:.2f} {bar_w}")
    lines.append(f"spark {left - bar_w - 8:.2f} {sub_y:.2f}")
    lines.append(f"spark {right + bar_w + 8:.2f} {sub_y:.2f}")
    with open(LAYOUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("main", round(main_w, 1), "glyphs", main_n, "sub", round(sub_w, 1), "glyphs", sub_n)


if __name__ == "__main__":
    main()
