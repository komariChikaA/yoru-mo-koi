# Cut title.png into per-character sprites with the white page removed.
# Japanese letters stay whole. Each one is saved in reading order.
import os
from collections import deque

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "title.png")
MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
OUT = os.path.join(MAPSET, "sb", "title")
LAYOUT = os.path.join(OUT, "layout.txt")
FIT = 0.40
ANCHOR = (320.0, 240.0)


def label(hard):
    h, w = hard.shape
    owners = np.full(hard.shape, -1, np.int32)
    comps = []
    ys, xs = np.where(hard)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if owners[y0, x0] >= 0:
            continue
        comp_id = len(comps)
        q = deque([(y0, x0)])
        owners[y0, x0] = comp_id
        minx = maxx = x0
        miny = maxy = y0
        count = 0
        sx = sy = 0
        while q:
            y, x = q.pop()
            count += 1
            sx += x
            sy += y
            if x < minx:
                minx = x
            elif x > maxx:
                maxx = x
            if y < miny:
                miny = y
            elif y > maxy:
                maxy = y
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and hard[ny, nx] and owners[ny, nx] < 0:
                    owners[ny, nx] = comp_id
                    q.append((ny, nx))
        comps.append({
            "id": comp_id,
            "minx": minx, "maxx": maxx, "miny": miny, "maxy": maxy,
            "area": count,
            "cx": sx / count,
            "cy": sy / count,
            "bw": maxx - minx + 1,
            "bh": maxy - miny + 1,
        })
    return owners, comps


def dilate(mask, radius):
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            y0s, y0e = max(0, dy), min(h, h + dy)
            x0s, x0e = max(0, dx), min(w, w + dx)
            y1s, y1e = max(0, -dy), min(h, h - dy)
            x1s, x1e = max(0, -dx), min(w, w - dx)
            out[y0s:y0e, x0s:x0e] |= mask[y1s:y1e, x1s:x1e]
    return out


def glyph_index(comp, gray):
    cx = comp["cx"]
    if cx < 430:
        return 0
    if cx < 610:
        return 1
    if cx < 870:
        return 2
    if cx < 1100 and (gray or cx < 1088):
        return 3
    if cx < 1280:
        return 4
    if cx < 1470:
        return 5
    if cx < 1660:
        return 6
    if cx < 1910:
        return 7
    return 8


def is_dot(comp, fill):
    return (
        comp["area"] >= 400
        and fill >= 0.72
        and 0.90 <= comp["bw"] / float(comp["bh"]) <= 1.16
        and 20 <= comp["bw"] <= 90
        and 20 <= comp["bh"] <= 90
    )


def unmatte(src, mask, ink):
    # White page comes out of the color. Core pixels stay opaque and keep their color.
    # The fringe stores the stroke color with partial alpha, so the edge stays smooth on white.
    core = mask & (ink > 28)
    if not core.any():
        core = mask
    color = np.median(src[core], axis=0)
    span = 255.0 - color
    channel = int(np.argmax(span))
    denom = max(float(span[channel]), 1.0)
    ys, xs = np.where(mask)
    out = np.zeros(src.shape[:2] + (4,), np.uint8)
    pixels = src[ys, xs].astype(np.float32)
    alpha = (255.0 - pixels[:, channel]) / denom
    alpha = np.clip(alpha, 0.0, 1.0)
    solid = alpha >= 0.82
    rgba = np.empty((len(ys), 4), np.float32)
    rgba[:, :3] = color
    rgba[solid, :3] = pixels[solid]
    rgba[:, 3] = np.where(solid, 255.0, alpha * 255.0)
    keep = rgba[:, 3] >= 8
    out[ys[keep], xs[keep]] = np.clip(rgba[keep], 0, 255).astype(np.uint8)
    return out, color


def crop_of(image, box, pad=3):
    y0 = max(0, box[0] - pad)
    y1 = min(image.shape[0], box[1] + pad)
    x0 = max(0, box[2] - pad)
    x1 = min(image.shape[1], box[3] + pad)
    crop = image[y0:y1, x0:x1]
    # Transparent texels keep the stroke color so a later scale does not pull in black.
    empty = crop[..., 3] == 0
    if empty.any() and (~empty).any():
        tone = np.median(crop[~empty, :3], axis=0)
        crop = crop.copy()
        crop[empty, :3] = tone
    return crop, (x0 + x1) / 2.0, (y0 + y1) / 2.0


def downscale(rgba):
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    prem = np.zeros_like(rgba, np.uint8)
    prem[..., :3] = np.clip(rgba[..., :3].astype(np.float32) * alpha, 0, 255).astype(np.uint8)
    prem[..., 3] = rgba[..., 3]
    width = max(1, int(round(rgba.shape[1] * FIT)))
    height = max(1, int(round(rgba.shape[0] * FIT)))
    resized = np.array(Image.fromarray(prem, "RGBA").resize((width, height), Image.Resampling.LANCZOS))
    out_a = resized[..., 3:4].astype(np.float32) / 255.0
    rgb = np.zeros_like(resized[..., :3], np.float32)
    np.divide(resized[..., :3], np.maximum(out_a, 1e-4), out=rgb, where=out_a > 0.004)
    result = np.zeros_like(resized)
    result[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    result[..., 3] = resized[..., 3]
    empty = result[..., 3] == 0
    if empty.any() and (~empty).any():
        result[empty, :3] = np.median(result[~empty, :3], axis=0)
    return result


def trace_downscale(mask, color):
    # Hard letter shapes, then one clean edge from the area average.
    # Lanczos on the soft cut was what blurred "Our Times".
    height, width = mask.shape
    out_w = max(1, int(round(width * FIT)))
    out_h = max(1, int(round(height * FIT)))
    alpha = np.array(Image.fromarray(mask.astype(np.uint8) * 255, "L").resize((out_w, out_h), Image.Resampling.BOX))
    rgba = np.zeros((out_h, out_w, 4), np.uint8)
    tone = np.clip(np.round(color), 0, 255).astype(np.uint8)
    rgba[..., :3] = tone
    rgba[..., 3] = alpha
    return rgba


def save_traced(mask, color, box, path):
    y0, y1, x0, x1 = box
    pad = 3
    y0 = max(0, y0 - pad)
    y1 = min(mask.shape[0], y1 + pad)
    x0 = max(0, x0 - pad)
    x1 = min(mask.shape[1], x1 + pad)
    Image.fromarray(trace_downscale(mask[y0:y1, x0:x1], color), "RGBA").save(path)
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def save_piece(sheet, box, path):
    crop, cx, cy = crop_of(sheet, box)
    Image.fromarray(downscale(crop), "RGBA").save(path)
    return cx, cy


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        os.remove(os.path.join(OUT, name))
    src = np.array(Image.open(SRC).convert("RGB"))
    ink = (255 - src.min(axis=2)).astype(np.int16)
    hard = ink > 16
    owners, comps = label(hard)
    for comp in comps:
        if comp["area"] < 12:
            comp["role"] = "noise"
            continue
        mask = owners == comp["id"]
        colors = src[mask]
        mean = colors.mean(axis=0)
        comp["gray"] = int(mean.max() - mean.min()) < 24 and float(mean.mean()) < 190
        comp["fill"] = comp["area"] / float(comp["bw"] * comp["bh"])
        if is_dot(comp, comp["fill"]):
            comp["role"] = "dot"
        elif comp["cy"] >= 510 and comp["gray"]:
            comp["role"] = "en"
        else:
            comp["role"] = "glyph"
            comp["glyph"] = glyph_index(comp, comp["gray"])
    noise = np.isin(owners, [comp["id"] for comp in comps if comp["role"] == "noise"])
    owners[noise] = -1

    rings = []
    for comp in comps:
        if comp["role"] == "noise":
            rings.append(None)
            continue
        rings.append(dilate(owners == comp["id"], 3) & (owners < 0) & (ink > 3))
    for comp, ring in zip(comps, rings):
        if ring is not None:
            owners[ring] = comp["id"]

    by_id = {comp["id"]: comp for comp in comps}
    sheets = {}
    for comp in comps:
        if comp["role"] == "noise":
            continue
        sheet, _ = unmatte(src, owners == comp["id"], ink)
        sheets[comp["id"]] = sheet

    def box(indexes):
        ys, xs = np.where(np.isin(owners, indexes))
        return int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1

    lines = []
    origin_y, origin_x = np.where(hard)
    origin = ((origin_x.min() + origin_x.max()) / 2.0, (origin_y.min() + origin_y.max()) / 2.0)

    def screen(cx, cy):
        return ANCHOR[0] + (cx - origin[0]) * FIT, ANCHOR[1] + (cy - origin[1]) * FIT

    for glyph in range(9):
        indexes = [comp["id"] for comp in comps if comp["role"] == "glyph" and comp["glyph"] == glyph]
        if not indexes:
            raise SystemExit("missing glyph " + str(glyph))
        rect = box(indexes)
        height = rect[1] - rect[0]
        cx, cy = save_piece(sum_sheets(sheets, indexes), rect, os.path.join(OUT, f"g{glyph}.png"))
        sx, sy = screen(cx, cy)
        lines.append(f"glyph g{glyph}.png {sx:.2f} {sy:.2f} {height * FIT:.2f}")

    en_indexes = [comp["id"] for comp in comps if comp["role"] == "en"]
    rect = box(en_indexes)
    en_mask = np.isin(owners, en_indexes) & (ink > 20)
    tone = np.median(src[en_mask & (ink > 70)], axis=0)
    cx, cy = save_traced(en_mask, tone, rect, os.path.join(OUT, "en.png"))
    sx, sy = screen(cx, cy)
    lines.append(f"en en.png {sx:.2f} {sy:.2f}")

    en_comps = [comp for comp in comps if comp["role"] == "en"]
    en_comps.sort(key=lambda comp: comp["cx"])
    clusters = []
    for comp in en_comps:
        if not clusters or comp["minx"] - clusters[-1]["maxx"] > 12:
            clusters.append({"minx": comp["minx"], "maxx": comp["maxx"]})
        else:
            clusters[-1]["maxx"] = max(clusters[-1]["maxx"], comp["maxx"])
    our_left, _ = screen(clusters[0]["minx"], 0)
    our_right, _ = screen(clusters[1]["maxx"], 0)
    lines.append(f"our {our_left:.2f} {our_right:.2f}")

    dots = [comp for comp in comps if comp["role"] == "dot"]
    dots.sort(key=lambda comp: comp["cx"])
    for n, comp in enumerate(dots):
        rect = box([comp["id"]])
        cx, cy = save_piece(sheets[comp["id"]], rect, os.path.join(OUT, f"d{n:02d}.png"))
        sx, sy = screen(cx, cy)
        lines.append(f"dot d{n:02d}.png {sx:.2f} {sy:.2f}")

    with open(LAYOUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("roles", {name: sum(comp["role"] == name for comp in comps) for name in ("glyph", "en", "dot")})
    print("words", [(round(c["minx"]), round(c["maxx"])) for c in clusters])
    print("wrote", len(lines), "lines")


def sum_sheets(sheets, indexes):
    total = np.zeros_like(sheets[indexes[0]])
    for index in indexes:
        part = sheets[index]
        over = part[..., 3] > total[..., 3]
        total[over] = part[over]
    return total


if __name__ == "__main__":
    main()
