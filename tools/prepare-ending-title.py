"""Compose the native school-uniform cast for the final title beat.

Original game art stays local and ignored. Silhouette/colour changes are applied
by Godot at runtime, so no recoloured source paintings are generated here.
"""
from pathlib import Path
import argparse
import importlib.util
import io
import json
import math
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}')
OUT = ROOT / 'godot/chorus-five/assets/ending-title'
CAST = [('かもめ', 'kamome'), ('姫色', 'hiiro'), ('恋', 'ren'),
        ('紫織', 'shiori'), ('雲', 'kumo')]
TITLE = '夜もすがら君恋ふ'


def prepare_cast():
    OUT.mkdir(parents=True, exist_ok=True)
    compositor = GAME / '立绘合成器'
    sys.path.insert(0, str(compositor))
    spec = importlib.util.spec_from_file_location('title_compositor', compositor / 'server.py')
    composer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composer)
    composer.load_catalog()
    records = []
    for character, name in CAST:
        key = (character, character + '１', '2')
        info = composer.POSES[key]
        selected = []
        for group in info['groups']:
            desired = '制服' if group['name'] == '服装' else ('微笑' if name == 'kumo' else '平常')
            layer = next((v for v in group['layers'] if v['name'] == desired), None)
            layer = layer or next(v for v in group['layers'] if v['id'] == group['default'])
            selected.append(layer['id'])
        image, _, missing = composer.compose(key, selected, crop=False)
        if missing:
            raise RuntimeError((character, missing))
        bounds = image.getchannel('A').getbbox()
        if bounds is None:
            raise RuntimeError(f'Empty native cast: {character}')
        image = image.crop(bounds)
        scale = min(1.0, 1600 / image.height)
        if scale < 1:
            image = image.resize((round(image.width * scale), round(image.height * scale)),
                                 Image.Resampling.LANCZOS)
        image.save(OUT / f'{name}.png')
        records.append(dict(name=name, character=character,
                            texture=f'res://assets/ending-title/{name}.png',
                            source=str(info['folder'] / (info['stem'] + '.pbd')),
                            source_crop=list(bounds), layers=selected,
                            width=image.width, height=image.height))
    (OUT / 'cast.json').write_text(json.dumps(records, ensure_ascii=False, indent=2),
                                   encoding='utf-8')
    print('Prepared five native full-body school-uniform portraits for ending title.')


def render_glyph(font, char):
    bounds = font.getbbox(char)
    image = Image.new('RGBA', (bounds[2] - bounds[0] + 48,
                              bounds[3] - bounds[1] + 48))
    ImageDraw.Draw(image).text((24 - bounds[0], 24 - bounds[1]), char, font=font,
                              fill=(255, 255, 255, 255), stroke_width=0)
    ink_bounds = image.getchannel('A').getbbox()
    return image.crop(ink_bounds) if ink_bounds is not None else None


def compose_geometric_love(outline):
    """Supply suusiki's empty 恋 with its native upper and a legible 心.

    Keep the upper's native triangular counters. The four lower strokes use
    matching 20-unit monoline geometry, separated rather than intertwined.
    Original bounds and the compact upper/lower gap keep the title layout.
    """
    cmap = outline.getBestCmap()
    glyphs = outline.getGlyphSet()
    def contours(char):
        recording = RecordingPen()
        glyphs[cmap[ord(char)]].draw(recording)
        result, current = [], []
        for command in recording.value:
            current.append(command)
            if command[0] in ('closePath', 'endPath'):
                result.append(current)
                current = []
        return result
    joined = TTGlyphPen(glyphs)
    upper = contours('変')
    for index in [0, 12, 13, 14, 15]:
        replayRecording(upper[index], joined)
    def polygon(points):
        points = [(round(x), round(y)) for x, y in points]
        joined.moveTo(points[0])
        for point in points[1:]:
            joined.lineTo(point)
        joined.closePath()

    def stroke(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * 10, dx / length * 10
        polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                 (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])

    # 心: a separate left dot, open angular bowl/hook, centre dot, right dot.
    # The bowl bottom stays at y65, exactly the former glyph's lower bound.
    stroke((365, 245), (337, 145))
    polygon([(420, 310), (440, 310), (440, 85), (628, 85),
             (646, 138), (665, 131), (642, 65), (420, 65)])
    stroke((525, 345), (552, 290))
    stroke((659, 275), (704, 195))
    love_name = cmap[ord('恋')]
    outline['glyf'][love_name] = joined.glyph()
    outline['hmtx'].metrics[love_name] = (1024, 0)
    buffer = io.BytesIO()
    outline.save(buffer)
    buffer.seek(0)
    composed_font = ImageFont.truetype(buffer, 1200)
    image = render_glyph(composed_font, '恋')
    if image is None:
        raise RuntimeError('The geometric title components have no visible outline')
    return image


def prepare_glyphs(font_path, font_index=0):
    """Render exact Japanese glyphs once; only derived local images reach Godot."""
    OUT.mkdir(parents=True, exist_ok=True)
    source = Path(font_path)
    outline = TTFont(source, fontNumber=font_index)
    cmap = outline.getBestCmap()
    missing = [char for char in TITLE if ord(char) not in cmap]
    if missing:
        raise RuntimeError(f'Font lacks title characters: {missing}')
    names = outline['name'].names
    family = next((v.toUnicode() for v in names if v.nameID == 1), source.stem)
    style = next((v.toUnicode() for v in names if v.nameID == 2), '')
    font = ImageFont.truetype(str(source), 1200, index=font_index)
    records = []
    for index, char in enumerate(TITLE):
        construction = 'native_font_glyph'
        image = render_glyph(font, char)
        if image is None and char == '恋' and 'suusiki' in family.lower():
            image = compose_geometric_love(outline)
            construction = 'suusiki 変[0,12,13,14,15] upper + four distinct geometric 心 strokes; 20_font_unit_monoline; original_bounds; component_gap=64_font_units'
        if image is None:
            raise RuntimeError(f'Font maps {char!r} but contains no visible glyph outline')
        image.save(OUT / f'title-glyph-{index}.png')
        guide = None
        if char in '夜君恋':
            # Find the actual top horizontal from the rendered font mask. The
            # runtime adds detached extensions beside this line, never over it.
            alpha = image.getchannel('A')
            rows = []
            for y in range(round(image.height * .05), round(image.height * .45)):
                pixels = alpha.crop((0, y, image.width, y + 1)).getdata()
                best = (0, 0)
                run_start = None
                for x, value in enumerate(pixels):
                    if value > 96 and run_start is None:
                        run_start = x
                    if run_start is not None and (value <= 96 or x == image.width - 1):
                        end = x if value <= 96 else x + 1
                        if end - run_start > best[1] - best[0]:
                            best = (run_start, end)
                        run_start = None
                rows.append((best[1] - best[0], y, best))
            _, y, (left, right) = max(rows)
            guide = [left / image.width, y / image.height,
                     right / image.width, y / image.height]
        records.append(dict(character=char,
                            texture=f'res://assets/ending-title/title-glyph-{index}.png',
                            width=image.width, height=image.height,
                            horizontal_guide=guide, construction=construction))
    document = dict(title=TITLE, font_source=str(source), font_index=font_index,
                    font_family=family, font_style=style, glyphs=records)
    (OUT / 'title-glyphs.json').write_text(json.dumps(document, ensure_ascii=False, indent=2),
                                         encoding='utf-8')
    print(f'Prepared exact title glyphs from {family} {style}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-cast', action='store_true')
    parser.add_argument('--font', default='C:/Users/hiral/AppData/Local/Microsoft/Windows/Fonts/suusiki.ttf')
    parser.add_argument('--font-index', default=0, type=int)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    # The game's full-frame logo includes its intended white background.
    logo_source = GAME / '解包/场景/logo_feng.png'
    shutil.copy2(logo_source, OUT / 'feng-logo.png')
    (OUT / 'feng-logo-source.json').write_text(json.dumps(dict(
        source=str(logo_source), texture='res://assets/ending-title/feng-logo.png',
        operation='native_full_frame_copy'), ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.skip_cast:
        prepare_cast()
    prepare_glyphs(args.font, args.font_index)


if __name__ == '__main__':
    main()
