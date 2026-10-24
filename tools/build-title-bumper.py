"""Deterministic print assets for the YUME / bell / IRO opening only.

No generated scene image, CRT effects or changes to later shot assets. The
paper and its shared 16px tile are pixel-identical at the 900ms handoff.
"""
from pathlib import Path
import argparse
import json
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from paper_material import opening_stock, SPARSE_OPACITY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/title-bumper'
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
PAPER = (247, 228, 161)
CAP_HEIGHT = 66
BELL_HEIGHT = 74
S = 2
WORD_GAP = 28
IRO_TRACKING = 10
OBSOLETE = ([f'ink-{name}-{i}.png' for name in ('yume', 'bell', 'iro') for i in range(6)]
            + [f'tile-{i:02d}.png' for i in range(24)])


def remove_obsolete(directory):
    # Only filenames owned by earlier versions of this generator.
    for name in OBSOLETE:
        (directory / name).unlink(missing_ok=True)


def slab_capital_i(font, scale):
    """Wide I with square slab bars measured from the same font's E.

    The bars share E's actual horizontal ink thickness; the stem retains
    Arial Bold's I weight. All measurements are made at the output resolution.
    """
    def glyph(ch, glyph_scale=scale):
        box = font.getbbox(ch)
        mask = Image.new('L', (box[2] - box[0], box[3] - box[1]))
        ImageDraw.Draw(mask).text((-box[0], -box[1]), ch, font=font, fill=255)
        return mask.resize((round(mask.width * glyph_scale), round(mask.height * glyph_scale)),
                           Image.Resampling.LANCZOS)

    e, stem = glyph('E'), glyph('I')
    # YUME and IRO have slightly different font bounds (U vs O). Measure
    # the displayed YUME E, rather than rounding a subtly thinner IRO E.
    reference_height = max(font.getbbox(ch)[3] - font.getbbox(ch)[1] for ch in 'YUME')
    reference_e = glyph('E', CAP_HEIGHT * S / reference_height)
    ink = np.array(reference_e) > 127
    rows = np.flatnonzero(ink[:, round(reference_e.width * .6)])
    top = int(np.flatnonzero((np.array(e) > 127)[:, round(e.width * .6)])[0])
    thickness = int(np.flatnonzero(np.diff(rows) != 1)[0]) + 1
    width = e.point(lambda p: 255 if p > 127 else 0).getbbox()[2]
    stem = stem.crop(stem.getbbox())
    mask = Image.new('L', (width, e.height))
    mask.paste(stem, ((width - stem.width) // 2, e.height - stem.height))
    draw = ImageDraw.Draw(mask)
    draw.rectangle((0, top, width - 1, top + thickness - 1), fill=255)
    draw.rectangle((0, e.height - thickness, width - 1, e.height - 1), fill=255)
    return mask, {'width': width / S, 'bar_thickness': thickness / S,
                  'stem_width': stem.width / S}


def lettering(text, font_path, size, height, tracking, slab_i=False):
    font = ImageFont.truetype(str(font_path), size * S)
    pieces = []
    for ch in text:
        box = font.getbbox(ch)
        if ch == ' ':
            pieces.append(None)
            continue
        im = Image.new('L', (box[2] - box[0], box[3] - box[1]))
        ImageDraw.Draw(im).text((-box[0], -box[1]), ch, font=font, fill=255)
        pieces.append(im)
    scale = height * S / max(p.height for p in pieces if p is not None)
    glyphs = [p.resize((round(p.width * scale), round(p.height * scale)), Image.Resampling.LANCZOS)
              if p is not None else None for p in pieces]
    if slab_i:
        glyphs = [slab_capital_i(font, scale)[0] if ch == 'I' else p
                  for ch, p in zip(text, glyphs)]
    gap = round(tracking * S)
    space = round(height * S * .6)
    width = sum(p.width if p is not None else space for p in glyphs) + gap * (len(glyphs) - 1)
    mask = Image.new('L', (width, round(height * S)))
    x = 0
    for p in glyphs:
        if p is not None:
            mask.paste(p, (x, mask.height - p.height))
        x += (p.width if p is not None else space) + gap
    rgba = Image.new('RGBA', mask.size, 'white')
    rgba.putalpha(mask)
    return rgba


def build(font_dir):
    OUT.mkdir(parents=True, exist_ok=True)
    remove_obsolete(OUT)
    words = {
        'yume': lettering('YUME', font_dir / 'arialbd.ttf', 92, CAP_HEIGHT, 2.5),
        'iro': lettering('IRO', font_dir / 'arialbd.ttf', 92, CAP_HEIGHT, IRO_TRACKING, slab_i=True),
    }
    font = ImageFont.truetype(str(font_dir / 'arialbd.ttf'), 92 * S)
    iro_height = max(font.getbbox(ch)[3] - font.getbbox(ch)[1] for ch in 'IRO')
    _, slab_metrics = slab_capital_i(font, CAP_HEIGHT * S / iro_height)
    bell = Image.open(ROOT / 'graphics/mapset/sb/bell-body.png').convert('RGBA')
    alpha = bell.getchannel('A')
    alpha = alpha.crop(alpha.getbbox())
    alpha = alpha.resize((round(alpha.width * BELL_HEIGHT * S / alpha.height), BELL_HEIGHT * S),
                         Image.Resampling.LANCZOS)
    words['bell'] = Image.new('RGBA', alpha.size, 'white')
    words['bell'].putalpha(alpha)
    for name, im in words.items():
        im.save(OUT / f'{name}.png')
    # The logo is settled before either glitch; bake the same row's objects
    # together instead of asking the renderer to draw three separate plates.
    gap = WORD_GAP * S
    plate = Image.new('RGBA', (sum(im.width for im in words.values()) + gap * 2, BELL_HEIGHT * S))
    x = 0
    for name in ('yume', 'bell', 'iro'):
        im = words[name]
        plate.alpha_composite(im, (x, (plate.height - im.height) // 2))
        x += im.width + gap
    for i in range(6):
        top, bottom = BELL_HEIGHT * S * i // 6, BELL_HEIGHT * S * (i + 1) // 6
        plate.crop((0, top, plate.width, bottom)).save(OUT / f'ink-{i}.png')
    subtitle = lettering('YUME TO IRO DE DEKITEIRU', font_dir / 'arial.ttf', 18, 8.5, 2.1)
    subtitle.save(OUT / 'subtitle.png')

    tile, paper = opening_stock(PAPER)
    tile.save(OUT / 'tile.png')
    paper.save(OUT / 'paper.png')
    (OUT / 'manifest.json').write_text(json.dumps({
        'paper_rgb': PAPER, 'ink_rgb': [61, 48, 42], 'pink_rgb': [233, 132, 165],
        'cyan_rgb': [112, 185, 212], 'cap_height': CAP_HEIGHT, 'bell_height': BELL_HEIGHT,
        'scale': .5, 'word_gap': WORD_GAP, 'tracking': {'yume': 2.5, 'iro': IRO_TRACKING},
        'slab_i': slab_metrics, 'tile_size': 16,
        'tiles': 1, 'ink_bands': 6, 'ink_width': plate.width, 'columns': 54, 'rows': 30, 'paper_source': 'imagetexture_00049.jpg', 'paper_opacity': SPARSE_OPACITY,
        'sizes': {k: list(v.size) for k, v in words.items()},
        'subtitle': 'YUME TO IRO DE DEKITEIRU', 'subtitle_height': 8.5,
        'font': 'Windows Arial Bold / Arial',
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path, default=MAPSET)
    parser.add_argument('--font-dir', type=Path, default=Path('C:/Windows/Fonts'))
    parser.add_argument('--no-install', action='store_true')
    args = parser.parse_args()
    build(args.font_dir)
    if not args.no_install:
        target = args.mapset / 'sb/title-bumper'
        target.mkdir(parents=True, exist_ok=True)
        remove_obsolete(target)
        for p in OUT.iterdir():
            if p.is_file():
                destination = target / p.name
                # Storybrew may hold unchanged logo PNGs open; install only changed assets.
                if not destination.exists() or p.read_bytes() != destination.read_bytes():
                    shutil.copyfile(p, destination)
    print('Built shared print stock, six logo bands and spaced lettering')
