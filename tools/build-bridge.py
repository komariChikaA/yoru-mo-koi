"""Build the agreed 40–52.5s bridge, without altering game originals.

The curved page is rasterized as one complete frame; Storybrew and Godot share
the same images and millisecond timeline. Requires Pillow, numpy and OpenCV.
"""
from pathlib import Path
import argparse
import json
import math
import re
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}/解包/场景')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
OUT = ROOT / 'godot/kobe-map/assets/bridge'
SIZE = (1920, 1080)
PAPER = (231, 226, 213)
MATTE = (22, 27, 37)
MONTAGE_START = int(re.search(r'\bDrumCut1Ms\s*=\s*(\d+)\s*;',
    (ROOT/'Bridge.cs').read_text(encoding='utf-8-sig')).group(1))


def scene(name):
    return Image.open(GAME / name).convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)


def card(image):
    sheet = Image.new('RGB', (1752, 996), PAPER)
    sheet.paste(image.resize((1728, 972), Image.Resampling.LANCZOS), (12, 12))
    stage = Image.new('RGB', SIZE, MATTE)
    stage.paste(sheet, (84, 42))
    return sheet, stage


def dark_night(image):
    image = ImageEnhance.Color(image).enhance(.78)
    image = image.point(lambda x: round(255 * (x / 255) ** 1.12))
    mask = Image.new('L', SIZE, 0)
    pen = ImageDraw.Draw(mask)
    pen.ellipse((-550, -650, 1050, 800), fill=92)
    pen.ellipse((1320, 280, 2220, 1100), fill=48)
    mask = mask.filter(ImageFilter.GaussianBlur(170))
    return Image.composite(Image.new('RGB', SIZE, (7, 12, 24)), image, mask)


def letterbox(image):
    # Full-width sky, with no side border or paper frame.
    result = image.copy()
    pen = ImageDraw.Draw(result)
    pen.rectangle((0, 0, 1919, 71), fill='black')
    pen.rectangle((0, 1008, 1919, 1079), fill='black')
    return result


def focus_light(image, night=False):
    """Soft background, retained focus detail, and broad light on the subject."""
    yy, xx = np.indices((1080, 1920), dtype=np.float32)
    x, y = xx / 1920, yy / 1080
    cx, cy = (.5, .61) if night else (.25, .36)
    focus = np.exp(-(((x-cx)/.17)**2 + ((y-cy)/.29)**2) * 1.6)
    soft = np.asarray(image.filter(ImageFilter.GaussianBlur(11)), dtype=np.float32)
    detail = np.asarray(image.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
    pixels = soft * (1-focus[:, :, None]) + detail * focus[:, :, None]
    if night:
        light = np.exp(-(((x-.50)/.16)**2 + ((y-.67)/.38)**2))
        pixels *= (.88 + .35 * light[:, :, None])
        pixels += light[:, :, None] * np.array([5, 10, 19], dtype=np.float32)
    else:
        light = np.exp(-(((x-.13)/.36)**2 + ((y-.23)/.63)**2))
        pixels *= (.95 + .18 * light[:, :, None])
        pixels += light[:, :, None] * np.array([22, 17, 8], dtype=np.float32)
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


def camera_card(image, zoom, cx, cy):
    half_x, half_y = 1920 / (2*zoom), 1080 / (2*zoom)
    crop = image.transform((1728, 972), Image.Transform.EXTENT,
                           (1920*cx-half_x, 1080*cy-half_y,
                            1920*cx+half_x, 1080*cy+half_y), Image.Resampling.BICUBIC)
    sheet = Image.new('RGB', (1752, 996), PAPER)
    sheet.paste(crop, (12, 12))
    stage = Image.new('RGB', SIZE, MATTE)
    stage.paste(sheet, (84, 42))
    return sheet, stage


def page_frame(front, under, progress):
    """A diagonal cylindrical curl, grabbed at bottom-right toward top-left.

    The still-flat portion stays registered. A curved band and the cream paper
    underside travel along a diagonal crease; the next scene is revealed below.
    """
    if progress <= 0:
        result = Image.new('RGB', SIZE, MATTE)
        result.paste(front, (84, 42))
        return result
    if progress >= 1:
        return under.copy()
    p = progress * progress * (3 - 2 * progress)
    width, height = front.size
    length = math.hypot(width, height)
    nx, ny = width / length, height / length
    radius = 22 + 150 * math.sin(math.pi * p) ** .7
    crease = length * (1 - p) - 230 * p
    yy, xx = np.indices((1080, 1920), dtype=np.float32)
    px, py = xx - 84, yy - 42
    normal = nx * px + ny * py
    tangent = -ny * px + nx * py
    texture = np.asarray(front)
    result = np.asarray(under).copy()
    flat = (px >= 0) & (px < width) & (py >= 0) & (py < height) & (normal <= crease)
    result[flat] = texture[py[flat].astype(int), px[flat].astype(int)]
    layers = []
    tilt = .32
    amplitude = math.sqrt(1 + tilt * tilt)
    value = ((normal - crease) / radius - tilt) / amplitude
    arc = np.arcsin(np.clip(value, -1, 1))
    phi = math.atan(tilt)
    # Near/front curl, far/back curl, then the fully turned underside.
    candidates = [(arc + phi, False), (math.pi - arc + phi, False),
                  (np.full_like(normal, math.pi), True)]
    for theta, folded_flat in candidates:
        if folded_flat:
            distance = radius * (math.pi + 2 * tilt) - (normal - crease)
            valid = distance >= math.pi * radius
        else:
            distance = theta * radius
            valid = (np.abs(value) <= 1) & (theta >= 0) & (theta <= math.pi)
        source_normal = crease + distance
        u = nx * source_normal - ny * tangent
        v = ny * source_normal + nx * tangent
        valid &= (u >= 0) & (u < width-1) & (v >= 0) & (v < height-1)
        if not np.any(valid):
            continue
        color = cv2.remap(texture, u.astype(np.float32), v.astype(np.float32),
                          cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        back = theta > math.pi / 2
        color[back] = PAPER
        # Smooth cylindrical light/shade, strongest at the curved lip.
        shade = .74 + .26 * np.abs(np.cos(theta))
        color = np.clip(color.astype(np.float32) * shade[:, :, None], 0, 255).astype(np.uint8)
        layers.append((valid, color))
    if layers:
        mask = np.zeros((1080, 1920), np.uint8)
        for valid, _ in layers:
            mask[valid] = 255
        shadow = cv2.GaussianBlur(mask, (0, 0), 12).astype(np.float32) / 255
        result = np.clip(result.astype(np.float32) * (1 - shadow[:, :, None] * .2), 0, 255).astype(np.uint8)
        for valid, color in layers:
            result[valid] = color[valid]
    return Image.fromarray(result)


def build(mapset):
    OUT.mkdir(parents=True, exist_ok=True)
    day_photo = focus_light(scene('秘密基地の中_昼.png'))
    night_photo = focus_light(dark_night(scene('山道_夜.png')), night=True)
    _, day = camera_card(day_photo, 2.04, .25, .35)
    front, _ = camera_card(day_photo, 2.04, .25, .44)
    _, night = camera_card(night_photo, 1.50, .50, .51)
    # Letterboxing is animated natively, rather than baked into these skies.
    sunset = scene('空_夕.png')
    sky_day = scene('空_昼.png')
    pictures = {'base-day.png': day, 'path-night.png': night,
                'day-focus.png': day_photo, 'night-focus.png': night_photo,
                'sky-evening.png': sunset, 'sky-day.png': sky_day,
                'sky-evening-bw.png': ImageOps.grayscale(sunset).convert('RGB'),
                'sky-day-bw.png': ImageOps.grayscale(sky_day).convert('RGB')}
    for name, im in pictures.items():
        im.save(OUT / name)
    Image.new('RGB', (1, 1), MATTE).save(OUT / 'matte.png')
    Image.new('RGB', (1, 1), 'black').save(OUT / 'black.png')
    frame = Image.new('RGBA', SIZE, MATTE + (255,))
    pen = ImageDraw.Draw(frame)
    pen.rectangle((84, 42, 1835, 1037), fill=PAPER + (255,))
    pen.rectangle((96, 54, 1823, 1025), fill=(0, 0, 0, 0))
    frame.save(OUT / 'paper-mask.png')
    # Optional fields: camera zoom / center-x / starting center-y / ending center-y.
    timeline = [(40000, 42900, 'day-focus.png', 0, 0, 2.04, .25, .35, .44),
                (40000, 42900, 'paper-mask.png', 0, 0)]
    for i in range(10):
        name = f'page-{i:02}.jpg'
        page_frame(front, night, i / 9).save(OUT / name, quality=96, subsampling=0)
        timeline.append((42900 + i * 25, 42925 + i * 25, name, 0, 0))
    def sky_row(begin, end, name, fade_in=0, fade_out=0):
        # One continuous camera path, including all overlapping monochrome layers.
        y_at = lambda time: .485 + .030 * (time - 46000) / 5260
        return (begin, end, name, fade_in, fade_out, 1.06, .5,
                y_at(begin), y_at(end), 'full')
    timeline.extend([(43150, 46000, 'night-focus.png', 0, 0, 1.50, .50, .51, .59),
                     (43150, 46000, 'paper-mask.png', 0, 0),
                     sky_row(46000, 47500, 'sky-evening.png'),
                     sky_row(47500, 47860, 'sky-evening-bw.png'),
                     sky_row(47620, 48180, 'sky-day-bw.png', 240),
                     sky_row(47860, MONTAGE_START, 'sky-day.png', 320)])
    (OUT / 'timeline.tsv').write_text('\n'.join('\t'.join(map(str, row)) for row in timeline) + '\n', encoding='utf-8')
    # Start / slide end / visibility end / bar height at 1080p.
    (OUT / 'letterbox.tsv').write_text(f'46000\t46360\t{MONTAGE_START}\t108\n', encoding='utf-8')
    lines = ['明けない夜は無いと', '夜明け前がただ暗いと',
             'この先に待つ明日が', 'そんなに輝くもんかなぁ']
    sky_font = ImageFont.truetype('C:/Windows/Fonts/YuGothR.ttc', 60)
    vertical_font = ImageFont.truetype('C:/Windows/Fonts/yumin.ttf', 44)
    lyric_times = [(40080, 42870), (43170, 45900), (46100, 48200), (48200, 52000)]
    lyric_rows = []
    motion_rows = []
    def lyric_part(image, name, begin, end, fade_in=0, fade_out=0,
                   enter=0, leave=0, enter_y=0, leave_y=0,
                   enter_scale=1, leave_scale=1, initial_alpha=0):
        bounds = image.getbbox()
        image.crop(bounds).save(OUT / name)
        motion_rows.append((begin, end, name, fade_in, fade_out, 'lyric',
                            (bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2,
                            enter, leave, enter_y, leave_y,
                            enter_scale, leave_scale, initial_alpha))
    for i, (line, (begin, end)) in enumerate(zip(lines, lyric_times)):
        im = Image.new('RGBA', SIZE)
        pen = ImageDraw.Draw(im)
        if i < 2:
            cx = 1536 if i == 0 else 384
            pen.rectangle((cx-39, 235, cx+38, 844), fill=(255, 255, 255, 255))
            lyric_part(im, f'lyric-{i+1}-strip.png', begin, end, 100, 80)
            step = 52
            first = 540 - (len(line)-1)*step/2
            for j, glyph in enumerate(line):
                box = pen.textbbox((0, 0), glyph, font=vertical_font)
                x = cx - (box[2]+box[0])/2
                y = first + j*step - (box[3]+box[1])/2
                pen.text((x, y), glyph, font=vertical_font, fill=(12, 12, 12, 255))
                glyph_image = Image.new('RGBA', SIZE)
                ImageDraw.Draw(glyph_image).text((x, y), glyph, font=vertical_font,
                                               fill=(12, 12, 12, 255))
                bounds = glyph_image.getbbox()
                for band in range(4):
                    top = round(bounds[1] + (bounds[3]-bounds[1])*band/4)
                    bottom = round(bounds[1] + (bounds[3]-bounds[1])*(band+1)/4)
                    piece = Image.new('RGBA', SIZE)
                    piece.paste(glyph_image.crop((bounds[0], top, bounds[2], bottom)),
                                (bounds[0], top))
                    lyric_part(piece, f'lyric-{i+1}-glyph-{j:02}-band-{band}.png',
                               begin+100+j*135+band*25, end, 25, 80)
        else:
            # Reference-style single Japanese credit line in the image center.
            box = pen.textbbox((0, 0), line, font=sky_font)
            tracking = 4
            advances = [sky_font.getlength(glyph) for glyph in line]
            x = 960 - (sum(advances) + tracking * (len(line)-1)) / 2
            y = 540 - (box[3] + box[1]) / 2
            mask = Image.new('L', SIZE)
            mask_pen = ImageDraw.Draw(mask)
            for glyph, advance in zip(line, advances):
                mask_pen.text((x, y), glyph, font=sky_font, fill=255)
                x += advance + tracking
            bounds = mask.getbbox()
            centered = Image.new('L', SIZE)
            centered.paste(mask.crop(bounds),
                           (round(960-(bounds[2]-bounds[0])/2),
                            round(540-(bounds[3]-bounds[1])/2)))
            mask = centered
            rim = mask.filter(ImageFilter.MaxFilter(3))
            halo = Image.new('RGBA', SIZE, (98, 225, 255, 0))
            halo.putalpha(rim.filter(ImageFilter.GaussianBlur(6)).point(
                lambda a: min(170, round(a * 1.5))))
            im.alpha_composite(halo)
            outline = Image.new('RGBA', SIZE, (249, 255, 255, 0))
            outline.putalpha(rim.point(lambda a: round(a * .75)))
            im.alpha_composite(outline)
            bounds = mask.getbbox()
            phase = np.clip((np.arange(1080) - bounds[1]) /
                            max(1, bounds[3] - bounds[1]), 0, 1)
            colors = (np.array([255, 255, 255]) * (1-phase[:, None]) +
                      np.array([158, 226, 252]) * phase[:, None]).astype(np.uint8)
            ink = Image.fromarray(np.broadcast_to(colors[:, None, :],
                                                  (1080, 1920, 3)).copy()).convert('RGBA')
            ink.putalpha(mask)
            im.alpha_composite(ink)
            face = Image.new('RGBA', SIZE)
            face.alpha_composite(outline)
            face.alpha_composite(ink)
            lyric_part(halo, f'lyric-{i+1}-halo.png', begin, end, 180, 180,
                       180, 180, 14, -10, 1.12, 1.16)
            lyric_part(face, f'lyric-{i+1}-face.png', begin, end, 180, 180,
                       180, 180, 14, -10, .985, .985, .25 if i == 3 else 0)
        name = f'lyric-{i+1}.png'
        im.save(OUT / name)
        lyric_rows.append((begin, end, name, 180 if i >= 2 else 100, 180 if i >= 2 else 80))
    (OUT / 'lyrics.tsv').write_text('\n'.join('\t'.join(map(str, row)) for row in lyric_rows) + '\n', encoding='utf-8')
    # The sunset hard cuts carry no subtitles. Close the previous sky lyric
    # exactly at the first cut instead of moving it above the new scenery.
    montage_lyrics = []
    for row in motion_rows:
        if row[0] == 48200 and row[1] == 52000:
            before = list(row); before[1] = MONTAGE_START; before[4] = 0; before[9] = 0
            montage_lyrics.append(before)
        else: montage_lyrics.append(row)
    motion_rows = montage_lyrics
    (OUT / 'lyrics-motion.tsv').write_text('\n'.join('\t'.join(map(str, row)) for row in motion_rows) + '\n', encoding='utf-8')
    (OUT / 'sources.json').write_text(json.dumps({
        'song_interval_ms': [40000, 53260], 'montage_from_ms': MONTAGE_START,
        'sources': [str(GAME / n) for n in ['秘密基地の中_昼.png', '山道_夜.png', '空_夕.png', '空_昼.png']],
        'night_treatment': 'saturation 0.78; gamma 1.12; blurred local reduction of upper-left spill and right foliage',
        'page_turn': '250ms; 10 whole frames at 40fps; bottom-right to top-left diagonal cylindrical curl; plain cream back; shadow',
        'camera': 'day: zoom 2.04, x .25, y .35 to .44; night: zoom 1.50, x .50, y .51 to .59; native linear downward pan',
        'focus_light': '11px Gaussian background / 1.2px focus detail; warm map daylight and cool road spotlight',
        'vertical_lyrics': 'Yu Mincho regular 44px; black on 78x610px white strip; x1536 day / x384 night',
        'lyric_motion': f'vertical: 100ms strip entry, each glyph written downward in four 25ms bands, 135ms glyph interval; sky: 180ms upward entry/glow expansion and upward exit/glow dispersal; second sky face starts visibly at 25% alpha at 48200ms; lyric closes exactly at the first drum cut, {MONTAGE_START}ms; montage has no subtitles',
        'sky_lyrics': 'one Japanese line centered at (960,540); Yu Gothic Regular 60px; 4px extra tracking; white-to-ice-blue gloss, 75% 1px rim, 6px cyan bloom; second sky lyric starts visibly at 25% alpha at 48200ms and settles in 180ms; no Chinese',
        'sky_time_transition': '47500ms monochrome sunset; 47620-47860ms monochrome crossfade; 47860-48180ms restore daytime color',
        'sky_camera': f'full-frame native pan: zoom 1.06, x .5; y .485 + .030 * (time - 46000) / 5260 until {MONTAGE_START}ms; identical camera pose during monochrome crossfades',
        'letterbox_slide': f'46000-46360ms; top/bottom 108px black bars slide inward with OutCubic; remain until {MONTAGE_START}ms',
        'frames': 'first pair 12px cream paper at 1080p; sky only 108px top/bottom black bars',
        'lyrics': lines,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if mapset:
        target = mapset / 'sb/bridge'
        target.mkdir(parents=True, exist_ok=True)
        for path in OUT.iterdir():
            if path.suffix in ['.png', '.jpg', '.tsv', '.json']:
                shutil.copy2(path, target / path.name)
    print(f'Bridge assets: {OUT}; mapset: {mapset}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path, default=MAPSET)
    build(parser.parse_args().mapset)
