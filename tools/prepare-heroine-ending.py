"""Prepare sharp native portraits for the five-sector MAD ending.

Uses the existing game compositor and the same heroine/bell assignments as
chorus-gate; no lit/glowing preview images are used as portrait sources.
"""
from pathlib import Path
import importlib.util
import json
import sys

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}')
OUT = ROOT / 'godot/chorus-five/assets/ending'
CAST = [('恋', 'ren', 'f28bb4'), ('姫色', 'hiiro', 'f0474f'),
        ('紫織', 'shiori', '9158c2'), ('かもめ', 'kamome', '3e403e'),
        ('雲', 'kumo', 'e2e4de')]
MEMORY_SCENES = [('校门前', '学校の校門前_昼.png', '日光中的校园入口'),
                 ('教室', '学校の教室_昼.png', '窗边阳光与空教室'),
                 ('中庭', '学校の中庭_昼.png', '绿树与红砖校舍')]
# Visible eye/mouth/chin centres and heights measured on the 1024px crops.
# Expression-layer bounds include differing amounts of hair and neck, so
# using those bounds alone puts some faces too low in a rotating sector.
CARD_FACES = {'ren': ([.4783333333, .50], 200/600),
              'hiiro': ([.52, .605], 300/1024),
              'shiori': ([.53, .615], 280/1024),
              'kamome': ([.518, .575], 300/1024),
              'kumo': ([.49, .64], 235/1024)}


def prepare_memory_panels():
    """Prepare empty campus backgrounds; warm lighting is applied at runtime."""
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (scene, filename, description) in enumerate(MEMORY_SCENES):
        source = GAME / '解包/场景' / filename
        with Image.open(source) as original:
            source_size = list(original.size)
            image = ImageOps.fit(original.convert('RGB'), (1920, 1080),
                                 method=Image.Resampling.LANCZOS)
        target = OUT / f'memory-{index}.png'
        image.save(target)
        records.append(dict(
            index=index, scene=scene, description=description,
            texture=f'res://assets/ending/memory-{index}.png',
            source=str(source), source_kind='native_game_background',
            source_size=source_size, output_size=[1920, 1080],
            source_song_time=None,
            source_song_range=None, filter_baked=False,
            timing_note='直接取游戏纯场景原图，非视频截帧；无对应歌曲取帧时间。暖色、柔光和高光在Godot着色器中实时处理。'))
    (OUT / 'memory-panels.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    compositor = GAME / '立绘合成器'
    sys.path.insert(0, str(compositor))
    spec = importlib.util.spec_from_file_location('ending_compositor', compositor / 'server.py')
    composer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composer)
    composer.load_catalog()
    records = []
    for character, name, color in CAST:
        if name == 'ren':
            source = GAME / '解包/CG/CGC16.png'
            image = Image.open(source).convert('RGBA')
            box = (600, 0, 1200, 600)
            centre = (887, 270)
            face_height = 285
            selected = []
        else:
            key = (character, character + '１', '2')
            info = composer.POSES[key]
            selected = []
            expression = None
            for group in info['groups']:
                desired = '制服' if group['name'] == '服装' else ('微笑' if name == 'kumo' else '平常')
                layer = next((v for v in group['layers'] if v['name'] == desired), None)
                layer = layer or next(v for v in group['layers'] if v['id'] == group['default'])
                selected.append(layer['id'])
                if group['name'] == '表情':
                    expression = layer
            image, _, missing = composer.compose(key, selected, crop=False)
            if missing:
                raise RuntimeError((character, missing))
            centre = (expression['left'] + expression['width'] / 2,
                      expression['top'] + expression['height'] / 2)
            face_height = expression['height']
            side = round(face_height * 2.1)
            box = (round(centre[0] - side / 2), round(centre[1] - side / 2),
                   round(centre[0] - side / 2) + side, round(centre[1] - side / 2) + side)
            source = str(info['folder'] / (info['stem'] + '.pbd'))
        # Preserve RGB and alpha; palette mapping takes place in the shader.
        crop = image.crop(box).resize((1024, 1024), Image.Resampling.LANCZOS)
        crop.save(OUT / (name + '.png'))
        records.append(dict(name=name, character=character, color=color,
                            texture='res://assets/ending/' + name + '.png',
                            face_uv=[(centre[0] - box[0]) / (box[2] - box[0]),
                                     (centre[1] - box[1]) / (box[3] - box[1])],
                            face_ratio=face_height / (box[3] - box[1]),
                            card_face_uv=CARD_FACES[name][0],
                            card_face_ratio=CARD_FACES[name][1],
                            source=str(source), source_crop=list(box), layers=selected))
    (OUT / 'portraits.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    prepare_memory_panels()
    print('Prepared five sharp native portraits and three empty campus backgrounds.')


if __name__ == '__main__':
    main()
