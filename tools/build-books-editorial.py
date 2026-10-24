"""Books page only: fixed palette, book/row pairs, and the supplied paper."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from paper_material import stock, CONTRAST, BACKGROUND_OPACITY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/books-editorial'
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
PALETTE = {
    'background': '#AAD0DE', 'structure': '#30465D', 'deep_blue': '#4B7590',
    'mist_blue': '#92C9D6', 'teal': '#8BBBAA', 'yellow': '#EFD17C',
    'pink': '#E5A0B5', 'purple': '#AA9EBE', 'brick': '#C9847B',
}
# Six yellow accents per phrase; cooler pairs and muted warm punctuation.
COLORS = ['deep_blue', 'yellow', 'mist_blue', 'pink', 'yellow', 'teal',
          'deep_blue', 'purple', 'yellow', 'mist_blue', 'brick', 'yellow',
          'teal', 'deep_blue', 'pink', 'yellow', 'purple', 'yellow']
WIDTHS = [21, 22, 17, 25, 14, 20, 18, 24, 16, 19, 22, 15, 27, 18, 20, 16, 25, 17]
HEIGHTS = [95, 82, 66, 54, 74, 88, 62, 80, 93, 56, 72, 86, 68, 97, 76, 58, 84, 70]
PERIOD, ROW_HEIGHT, S = 396, 102, 2


def build(mapset):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'credit').mkdir(exist_ok=True)
    widths = np.array(WIDTHS, dtype=float)
    widths = np.floor(widths * (PERIOD - len(widths) * 2) / widths.sum()).astype(int)
    widths[:PERIOD - len(widths) * 2 - int(widths.sum())] += 1
    row = Image.new('RGBA', (PERIOD * S, ROW_HEIGHT * S))
    draw = ImageDraw.Draw(row)
    draw.rectangle((0, 98 * S, row.width - 1, row.height - 1), fill=PALETTE['structure'])
    layout, x = [], 0
    for i, (w, h, color) in enumerate(zip(widths.tolist(), HEIGHTS, COLORS)):
        book = Image.new('RGBA', (w * S, h * S))
        d = ImageDraw.Draw(book)
        d.rectangle((0, 0, book.width - 1, book.height - 1), fill=PALETTE['structure'])
        d.rectangle((S, S, book.width - S - 1, book.height - S - 1), fill=PALETTE[color])
        # Printed spine marks use only the supplied palette, with no shading.
        mark = PALETTE['yellow'] if color != 'yellow' else PALETTE['structure']
        if i % 3 == 0:
            d.rectangle((3*S, 7*S, (w-3)*S-1, 10*S-1), fill=mark)
            d.rectangle((3*S, (h-13)*S, (w-3)*S-1, (h-11)*S-1), fill=mark)
        elif i % 3 == 1:
            d.rectangle((4*S, 10*S, 6*S-1, (h-12)*S-1), fill=mark)
        else:
            d.rectangle((3*S, 10*S, (w-3)*S-1, 18*S-1), fill=mark)
        book.save(OUT / f'book-{i:02d}-bottom.png')
        book.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT / f'book-{i:02d}-top.png')
        row.alpha_composite(book, (x*S, (98-h)*S))
        layout.append(f'{i} {x} {w} {h}')
        x += w + 2
    assert x == PERIOD
    # Four periods match the old 1584px strip and preserve its scroll distance.
    strip = Image.new('RGBA', (PERIOD * 4 * S, ROW_HEIGHT * S))
    for i in range(4):
        strip.alpha_composite(row, (i * PERIOD * S, 0))
    strip.save(OUT / 'row-bottom.png')
    strip.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT / 'row-top.png')
    (OUT / 'layout.txt').write_text('\n'.join(layout) + '\n', encoding='utf-8')

    # Keep the existing glyph outlines/layout. Map old blue interiors to navy,
    # and white ink to yellow instead of multiplying an already coloured glyph.
    old_blue = np.array([120, 184, 211], dtype=float)
    delta = 255 - old_blue
    def rgb(hex_color):
        return np.array([int(hex_color[i:i+2], 16) for i in (1, 3, 5)], dtype=float)
    for p in (mapset / 'sb/credit').glob('*.png'):
        im = Image.open(p).convert('RGBA')
        a = np.array(im)
        weight = np.clip(((a[..., :3].astype(float) - old_blue) * delta).sum(axis=2)
                         / (delta * delta).sum(), 0, 1)[..., None]
        a[..., :3] = np.rint(rgb(PALETTE['structure']) * (1-weight)
                            + rgb(PALETTE['yellow']) * weight).astype('uint8')
        Image.fromarray(a).save(OUT / 'credit' / p.name)

    paper_source = ROOT / 'imagetexture_00049.jpg'
    stock().save(OUT / 'paper.png')
    (OUT / 'manifest.json').write_text(json.dumps({
        'palette': PALETTE, 'color_order': COLORS, 'period': PERIOD, 'strip_width': PERIOD*4,
        'row_height': ROW_HEIGHT, 'asset_scale': .5, 'books_per_period': len(COLORS),
        'paper_source': paper_source.name, 'paper_source_sha256': hashlib.sha256(paper_source.read_bytes()).hexdigest(),
        'paper_contrast': CONTRAST, 'paper_opacity': BACKGROUND_OPACITY, 'paper_scale': 1.2,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path, default=MAPSET)
    parser.add_argument('--no-install', action='store_true')
    args = parser.parse_args()
    build(args.mapset)
    if not args.no_install:
        shutil.copytree(OUT, args.mapset / 'sb/books-editorial', dirs_exist_ok=True)
    print('Built editorial books, aligned scroll strips, credit inks and supplied paper')
