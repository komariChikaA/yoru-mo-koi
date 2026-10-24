"""Extract the five full-body SD illustrations from CGZ14-18's white matte.

Run with --upscale for the existing local Real-ESRGAN anime model as well.
The native cutouts preserve source pixels; only the antialiased outside edges
are unmatted. Original game CGs and the previous video-derived set stay intact.
"""
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

SOURCE = Path("${GAME_ROOT}/解包/CG")
ROOT = Path("E:/系统默认/桌面/mad/素材/yumeiro_CG_SD")
MODEL = Path("E:/系统默认/桌面/mad/素材/yumeiro_op_SD/工作文件/realesr-animevideov3.pth")
ITEMS = [
    ("01_姬色_CGZ14", "hiiro", 14, []),
    ("02_恋_CGZ16", "ren", 16, [(1240, 401), (1246, 736)]),
    ("03_云_CGZ17", "kumo", 17, []),
    ("04_鸥_CGZ15", "kamome", 15, []),
    ("05_紫织_CGZ18", "shiori", 18,
     [(1812, 555), (1709, 711), (1315, 789), (1750, 808)]),
]
NATIVE = ROOT / "原尺寸透明PNG"
HIGH = ROOT / "高清4倍透明PNG"
WORK = ROOT / "工作文件"
FONT = "C:/Windows/Fonts/msyh.ttc"


def extract(name, actor, number, gap_seeds):
    source = SOURCE / f"CGZ{number}.png"
    rgb = np.array(Image.open(source).convert("RGB"))
    # The biggest connected ink region is the full character. This excludes
    # the logo, decorative dots and Ren's detached question marks.
    labels, _ = ndi.label(rgb.min(axis=2) < 250, np.ones((3, 3)))
    areas = np.bincount(labels.ravel())
    areas[0] = 0
    ink = labels == int(areas.argmax())
    inside = ndi.binary_fill_holes(ink)
    # White shirt/stockings/highlights remain opaque. Only hand-inspected
    # background spaces enclosed by hair are opened, using source coordinates.
    holes, _ = ndi.label(inside & ~ink)
    for x, y in gap_seeds:
        hole_id = int(holes[y, x])
        if not hole_id:
            raise ValueError(f"{source.name}: gap seed {x}, {y} is not a white hole")
        inside[holes == hole_id] = False

    # Recover coverage and foreground colour from the known white matte.
    # Interior RGB stays exactly as drawn, including white costume details.
    distance = ndi.distance_transform_edt(inside)
    core = inside & (distance >= 2.0) & (rgb.min(axis=2) < 210)
    core_distance, indices = ndi.distance_transform_edt(~core, return_indices=True)
    estimate = rgb[tuple(indices)].astype(np.float32)
    pixels = rgb.astype(np.float32)
    contrast = 255.0 - estimate
    coverage = ((255.0 - pixels) * contrast).sum(axis=2) / np.maximum((contrast * contrast).sum(axis=2), 1.0)
    coverage = np.clip(coverage, 0.0, 1.0)
    edge = inside & (distance <= 2.5) & (core_distance <= 4.0)
    alpha = inside.astype(np.float32)
    alpha[edge] = coverage[edge]
    unmatte = (pixels - 255.0 * (1.0 - alpha[:, :, None])) / np.maximum(alpha[:, :, None], 1.0 / 255.0)
    pixels[edge] = np.clip(unmatte[edge], 0, 255)
    a8 = np.rint(alpha * 255).astype(np.uint8)
    # Inspecting Hiiro/Kumo's very thin purple hair tips on dark grey reveals
    # tiny white matte islands beyond the line. Their costume whites have
    # dark closed outlines and do not touch this outermost silhouette band.
    if number in (14, 17):
        tip_distance = ndi.distance_transform_edt(a8 > 0)
        white_tips = (tip_distance <= 1.5) & (pixels.min(axis=2) > 245) & (a8 > 240)
        a8[white_tips] = 0
    pixels[a8 == 0] = 0
    rgba = Image.fromarray(np.dstack((np.rint(pixels).astype(np.uint8), a8)))
    bbox = rgba.getbbox()
    crop = rgba.crop(bbox)
    # Modest transparent padding keeps transformations and mipmaps comfortable.
    padded = Image.new("RGBA", (crop.width + 32, crop.height + 32))
    padded.alpha_composite(crop, (16, 16))
    padded.save(NATIVE / f"{name}.png")
    Image.fromarray(a8).save(WORK / f"{name}_原图遮罩.png")
    Image.open(source).crop(bbox).save(WORK / f"{name}_原图裁切.png")
    print(name, "native", padded.size, "source_bounds", bbox, flush=True)
    return {"actor": actor, "source": str(source), "file": name + ".png",
            "source_bounds": list(bbox), "native_size": list(padded.size),
            "background_gap_seeds": [list(s) for s in gap_seeds]}


def upscale():
    import torch
    from torch import nn
    from torch.nn import functional as F
    torch.set_num_threads(8)

    class SRVGG(nn.Module):
        def __init__(self):
            super().__init__()
            layers = [nn.Conv2d(3, 64, 3, 1, 1), nn.PReLU(64)]
            for _ in range(16):
                layers.extend([nn.Conv2d(64, 64, 3, 1, 1), nn.PReLU(64)])
            layers.append(nn.Conv2d(64, 48, 3, 1, 1))
            self.body = nn.Sequential(*layers)

        def forward(self, x):
            return F.pixel_shuffle(self.body(x), 4) + F.interpolate(x, scale_factor=4, mode="nearest")

    model = SRVGG().eval()
    weights = torch.load(MODEL, map_location="cpu", weights_only=True)
    model.load_state_dict(weights.get("params_ema", weights.get("params", weights)))
    # Tiles reuse the existing model without allocating full-image feature maps.
    for name, *_ in ITEMS:
        im = Image.open(NATIVE / f"{name}.png").convert("RGBA")
        a = np.array(im)
        indices = ndi.distance_transform_edt(a[:, :, 3] < 240, return_distances=False, return_indices=True)
        rgb = a[:, :, :3][tuple(indices)]
        result = np.empty((im.height * 4, im.width * 4, 3), dtype=np.uint8)
        tile, pad = 256, 24
        with torch.inference_mode():
            for y in range(0, im.height, tile):
                for x in range(0, im.width, tile):
                    x1, y1 = min(x + tile, im.width), min(y + tile, im.height)
                    xa, ya = max(x - pad, 0), max(y - pad, 0)
                    xb, yb = min(x1 + pad, im.width), min(y1 + pad, im.height)
                    tensor = torch.from_numpy(rgb[ya:yb, xa:xb].transpose(2, 0, 1).copy()).float().div_(255).unsqueeze(0)
                    high = model(tensor).clamp_(0, 1)
                    high = (high[0].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
                    result[y*4:y1*4, x*4:x1*4] = high[(y-ya)*4:(y1-ya)*4, (x-xa)*4:(x1-xa)*4]
        alpha = np.array(im.getchannel("A").resize((im.width * 4, im.height * 4), Image.Resampling.LANCZOS))
        result[alpha == 0] = 0
        Image.fromarray(np.dstack((result, alpha))).save(HIGH / f"{name}.png")
        print(name, "anime 4x", (im.width * 4, im.height * 4), flush=True)


def previews():
    font = ImageFont.truetype(FONT, 23)
    sheet = Image.new("RGB", (1800, 1240), "#e8ebef")
    draw = ImageDraw.Draw(sheet)
    for i, (name, *_rest) in enumerate(ITEMS):
        im = Image.open(NATIVE / f"{name}.png")
        im.thumbnail((330, 520), Image.Resampling.LANCZOS)
        for row, background in enumerate(["checker", "#242832"]):
            tile = Image.new("RGBA", (350, 550), background if row else "#eef0f4")
            if not row:
                td = ImageDraw.Draw(tile)
                for y in range(0, 550, 20):
                    for x in range(0, 350, 20):
                        if (x // 20 + y // 20) % 2 == 0:
                            td.rectangle((x, y, x + 19, y + 19), fill="#d7dce4")
            tile.alpha_composite(im, ((350 - im.width) // 2, 535 - im.height))
            sheet.paste(tile.convert("RGB"), (i * 360 + 5, row * 620 + 5))
            draw.text((i * 360 + 14, row * 620 + 570), name, font=font, fill="#283241")
    sheet.save(ROOT / "预览.png")


if __name__ == "__main__":
    for folder in [NATIVE, HIGH, WORK]:
        folder.mkdir(parents=True, exist_ok=True)
    manifest = [extract(*item) for item in ITEMS]
    previews()
    if "--upscale" in sys.argv:
        upscale()
    (ROOT / "sources.json").write_text(json.dumps({
        "items": manifest, "method": "Connected white-matte extraction, inspected hair-gap masks and edge unmatting",
        "native": "Source RGB preserved except anti-aliased matte boundary; 16px transparent padding",
        "upscale": "Optional existing Real-ESRGAN realesr-animevideov3; 4x; alpha resampled separately",
        "source_modified": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
