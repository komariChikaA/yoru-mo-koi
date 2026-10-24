"""Prepare intact original-color memory windows and readable rounded typography.

Only project/mapset copies are written; original game assets remain untouched.
"""
from pathlib import Path
import argparse
import json
import shutil
from PIL import Image, ImageChops, ImageDraw, ImageFont
from rounded_type import FONT, lettering, photo_label, BUBBLE_URL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/cord-memories'
GAME = Path('${GAME_ROOT}/解包')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')


def build(game, mapset):
    OUT.mkdir(parents=True, exist_ok=True)
    selected = [
        ('after-school.png', game / '场景/通学路_夕.png'),
        ('home.png', game / '场景/自宅前_昼.png'),
        ('hand-in-hand.png', game / 'CG/CGC01_a.png'),
        ('together.png', game / 'CG/CGC02_b.png'),
    ]
    sources = []
    for name, source in selected:
        image = Image.open(source).convert('RGB')
        # Same 16:9 dimensions for the existing flat window scale contract.
        image = image.resize((768, 432), Image.Resampling.LANCZOS)
        image.save(OUT / name)
        sources.append(dict(file=name, source=str(source),
            treatment='full image; unchanged RGB; resampled to 768x432'))

    dialogues = [
        ('dialogue-memory.png', 'TG3-04-12.png', 'ずっと、守っていけますように……'),
        ('dialogue-thanks.png', 'TG3-04-8.png', 'ありがとう、兄さん。'),
        ('dialogue-love.png', 'TG3-04-9.png', '大好きだよ、お兄ちゃん。'),
    ]
    for name, original, line in dialogues:
        source = game / '其他图片/效果' / original
        padded = lettering(line, 64, '#594537', padding=8)
        padded.save(OUT / name)
        # Full-size soft wipe frames keep the rounded letters intact and avoid
        # filtering seams from separately cropped glyphs in the storyboard.
        feather = 96
        for frame in range(1, 18):
            edge = (padded.width + feather) * frame / 18
            ramp = Image.new('L', (padded.width, 1))
            ramp.putdata([round(255 * max(0, min(1, (edge-x) / feather)))
                for x in range(padded.width)])
            reveal = padded.copy()
            reveal.putalpha(ImageChops.multiply(padded.getchannel('A'),
                ramp.resize(padded.size)))
            reveal.save(OUT / f'{Path(name).stem}-reveal-{frame}.png')
        sources.append(dict(file=name,source=str(source),dialogue=line,font=str(FONT),
            treatment='same dialogue retypeset in Zen Maru Gothic Medium; dark warm ink',
            entrance='17 full-canvas alpha wipe frames; 96px soft edge; final rounded text'))

    japanese = ImageFont.truetype('C:/Windows/Fonts/YuGothL.ttc', 64, index=0)

    def text(name, label, font, color):
        box = font.getbbox(label)
        image = Image.new('RGBA', (box[2]-box[0]+12, box[3]-box[1]+12))
        ImageDraw.Draw(image).text((6-box[0], 6-box[1]), label, font=font, fill=color)
        image.save(OUT / name)

    text('lyric-hurt.png', 'そういつも 傷付け合って', japanese, '#765A48')
    text('lyric-love.png', 'また愛し合うのさ', japanese, '#765A48')
    for name, label in [('after-school', 'AFTER SCHOOL'), ('home', 'HOME AGAIN'),
            ('hand-in-hand', 'A QUIET AFTERNOON'), ('together', 'TOGETHER AGAIN')]:
        photo_label(label, tail_side='right' if name in ('after-school', 'together') else 'left').save(OUT / (name + '-caption.png'))
    sources.append(dict(file='*-caption.png', source=BUBBLE_URL,
        page='https://fukidesign.com/e1547/', terms='https://fukidesign.com/terms',
        treatment='text-bearing cream speech labels; e1547 body with downward photo pointers; original Segoe UI Light; 3x raster',
        font='C:/Windows/Fonts/segoeuil.ttf'))

    ring = Image.new('RGBA', (96, 96))
    ImageDraw.Draw(ring).ellipse((8, 8, 88, 88), fill='#FAF9F6', outline='#765A48', width=8)
    ring.resize((48, 48), Image.Resampling.LANCZOS).save(OUT / 'station.png')

    # Transparent expanding holes reveal the existing tint and grid underneath.
    # A very fine champagne contour makes the white highlight legible on cream.
    for frame in range(18):
        rim = Image.new('RGBA', (2048, 2048))
        draw = ImageDraw.Draw(rim)
        draw.ellipse((8, 8, 2040, 2040), fill='#FFFEFA', outline='#D3BAA2', width=4)
        inner = .992 * (1 - (1-frame/17)**2)
        if inner > 0:
            radius = 1016 * inner
            draw.ellipse((1024-radius,1024-radius,1024+radius,1024+radius),fill=(0,0,0,0))
        rim.resize((512,512),Image.Resampling.LANCZOS).save(OUT / f'bubble-rim-{frame}.png')

    # Extract transparent decorations from the supplied game sprite sheets.
    petals_source = game / '其他图片/粒子/花びら_連番４列_fl32.png'
    petals = Image.open(petals_source).convert('RGBA')
    for index, frame in enumerate((0, 1, 2, 3)):
        x, y = frame % 4 * 32, frame // 4 * 32
        petals.crop((x, y, x + 32, y + 32)).save(OUT / f'petal-{index}.png')
    sources.append(dict(file='petal-0.png .. petal-3.png', source=str(petals_source),
        treatment='four open petal frames; 4 columns of 32x32; original RGBA'))

    music_source = game / '其他图片/表情符号/♪アニメ.png'
    music = Image.open(music_source).convert('RGBA')
    for index, frame in enumerate((14, 15, 16)):
        image = music.crop((0, frame * 187, 238, (frame + 1) * 187))
        image = image.crop(image.getbbox())
        # Equal canvas for a stable scale contract, with original proportions.
        canvas = Image.new('RGBA', (160, 160))
        image.thumbnail((140, 140), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, ((160-image.width)//2, (160-image.height)//2))
        canvas.save(OUT / f'music-{index}.png')
    sources.append(dict(file='music-0.png .. music-2.png', source=str(music_source),
        treatment='frames 14..16; vertical 238x187 cells; transparent margins cropped'))

    for name, source, size in (
            ('joy.png', game / '其他图片/表情符号/喜ぶ.png', (95, 90)),
            ('sd-blonde.png', Path('E:/系统默认/桌面/mad/素材/yumeiro_op_SD/高清4倍透明PNG/02_金发绿眼.png'), (680, 728))):
        image = Image.open(source).convert('RGBA')
        if name == 'sd-blonde.png':
            size = (round(image.width * size[1] / image.height), size[1])
        image.resize(size, Image.Resampling.LANCZOS).save(OUT / name)
        treatment = ('repaired source ribbon and ponytail alpha; original proportions; resampled'
            if name == 'sd-blonde.png' else 'original color and alpha; resampled')
        sources.append(dict(file=name, source=str(source), treatment=treatment))
    (OUT / 'sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding='utf-8')
    target = mapset / 'sb/cord-memories'
    target.mkdir(parents=True, exist_ok=True)
    for path in OUT.glob('*.png'):
        destination = target / path.name
        if not destination.exists() or destination.read_bytes() != path.read_bytes():
            shutil.copyfile(path, destination)
    print('Installed memory windows, captions, petals, music symbols, SD character and joy mark.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', type=Path, default=GAME)
    parser.add_argument('--mapset', type=Path, default=MAPSET)
    options = parser.parse_args()
    build(options.game, options.mapset)
