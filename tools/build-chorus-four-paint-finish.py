"""Build the local dry-brush wipe and cream wall end card for shot four.

Uses the existing Eagle brush, handwritten lettering and inverse-Bridge dust.
Does not rebuild puppets, change the production sequence, or include bells.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
W, H = 1920, 1080
DELIVERY = Path('../../工作文件夹/output/CGC14-15_scene4')
BRUSH = Path('${EAGLE_ROOT}/精选图片.library/images/LP88LES5EY98D.info/brush_D_0003.png')
FONT = ROOT/'assets/fonts/Yomogi-Regular.ttf'
FONT_PX = 58
LETTER_SPACING = 3
TITLE_SIZE = (1400, 180)
TITLE = '全種類のカラーベルを獲得しました！'
STROKE_ANGLE = 80.0  # From horizontal; 90 degrees travels vertically upwards.
TEXT_SOURCE = Path('${GAME_ROOT}/解包/其他图片/铃铛/カラーベル全種類.png')


def grid_noise(rng, columns, rows, width=W, height=H):
    small = rng.normal(0, 1, (rows, columns)).astype(np.float32)
    result = cv2.resize(small, (width, height), interpolation=cv2.INTER_CUBIC)
    return result / max(float(result.std()), .001)


def smoothstep(a, b, value):
    value = np.clip((value-a)/(b-a), 0, 1)
    return value*value*(3-2*value)


def brush_assets(out, brush_path):
    source = Image.open(brush_path).convert('RGBA')
    alpha = source.getchannel('A')
    alpha = alpha.crop(alpha.getbbox())
    # Preserve the source's longitudinal fibres, rather than rounding a polygon.
    alpha.resize((2400, 280), Image.Resampling.LANCZOS).save(out/'brush-bristles-alpha.png')
    a = np.array(alpha).astype(np.float32)/255
    profile = np.mean(a[:, :max(2, a.shape[1]//3)], axis=1)
    profile = cv2.GaussianBlur(profile[:, None], (1, 5), .65).ravel()
    profile -= profile.min()
    profile /= max(float(profile.max()), .001)
    return profile, a


def make_wet_paint(along, across, brush_detail):
    """Loaded paint ridges and broken, granular bristle tracks."""
    rng = np.random.default_rng(80018)
    span = int(np.ceil(across.max()))+2
    fibres = rng.normal(0, 1, span).astype(np.float32)
    fibres = cv2.GaussianBlur(fibres[:, None], (1, 9), 1.15).ravel()
    fibres /= max(float(fibres.std()), .001)
    ridge = np.interp(across, np.arange(span), fibres)
    # Long ridges follow the stroke axis, with small changes in pigment load.
    load = .5+.5*np.sin(along*19+ridge*.4)
    granules = grid_noise(rng, 640, 360)
    rake = granules-np.roll(granules, (2, 1), axis=(0, 1))
    clumps = grid_noise(rng, 240, 135)
    relief = ridge*5.2+(brush_detail-.6)*21+load*3+rake*3.8+clumps*2.3
    rgb = np.array([248., 239., 210.])+relief[..., None]
    rgb += load[..., None]*np.array([1., 1.5, 4.])
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255)))


def make_wall(rng, yy, xx, across, state, common):
    # Keep the relief anchored; only fine grain and nearby micro-pits boil at 12Hz.
    # Paired highlights/shadows read as raised paint rather than dark dirt noise.
    fine = rng.normal(0, 1.05, (H, W)).astype(np.float32)
    medium = grid_noise(rng, 640, 360)*.8
    micro = grid_noise(rng, 960, 540)
    micro -= np.roll(micro, (1, 1), axis=(0, 1))
    bristle = np.interp(np.mod(across+.18*state, 350),
                        np.arange(len(common['bristle'])), common['bristle'])
    n = (common['relief']*3.8+common['clumps']*1.5-common['pits']*4.8
         +common['tracks']*2.1+common['broad']*.6+bristle*.65
         +fine+medium+micro*.65)
    warm = .5+.5*np.sin((xx*.34+yy*.15)/570)
    rgb = np.array([247.0, 241.0, 222.0])+n[..., None]
    rgb -= warm[..., None]*np.array([.5, .8, 1.5])
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255)))


def make_dust(out):
    # Add readable charcoal paint specks over the cream relief. A mixture of
    # small dots, irregular flecks and a few scratches keeps the wall airy.
    dot = Image.new('RGBA', (16, 16))
    ImageDraw.Draw(dot).ellipse((6, 6, 10, 10), fill=(54, 47, 35, 195))
    dot = dot.filter(ImageFilter.GaussianBlur(.25))
    fleck = Image.new('RGBA', (20, 20))
    ImageDraw.Draw(fleck).polygon([(7, 6), (10, 5), (13, 8), (12, 11),
                                  (9, 13), (6, 10)], fill=(68, 56, 36, 160))
    scratch = Image.new('RGBA', (48, 24))
    ImageDraw.Draw(scratch).line([(8, 17), (18, 12), (23, 13), (34, 7)],
                                fill=(80, 72, 57, 105), width=1)
    soft = Image.new('RGBA', (48, 48))
    ImageDraw.Draw(soft).ellipse((18, 18, 30, 30), fill=(74, 66, 48, 30))
    soft = soft.filter(ImageFilter.GaussianBlur(5))
    sprites = {'dot': dot, 'fleck': fleck, 'scratch': scratch, 'soft': soft}
    for key, sprite in sprites.items():
        sprite.save(out/f'dust-{key}.png')
    rng = np.random.default_rng(1306)
    particles = []
    for i in range(172):
        kind = 'dot' if i < 112 else 'fleck' if i < 148 else 'scratch' if i < 164 else 'soft'
        x, y = float(rng.uniform(16, 1904)), float(rng.uniform(70, 1010))
        # Soften only the lettering lane, so no dark fleck competes with a glyph.
        text_lane = 250 < x < 1670 and 515 < y < 635
        particles.append(dict(kind=kind, x=x,
            y=y, scale=float(rng.uniform(.50, .95) if kind != 'scratch' else rng.uniform(.3, .65)),
            rotation=float(rng.uniform(-1.2, 1.2)),
            alpha=float(rng.uniform(.55, .95))*(.30 if text_lane else 1.0),
            phase=float(rng.uniform(0, 2*np.pi))))
    for state in range(6):
        canvas = Image.new('RGBA', (W, H))
        for p in particles:
            sprite = sprites[p['kind']]
            size = tuple(max(1, round(n*p['scale'])) for n in sprite.size)
            sprite = sprite.resize(size, Image.Resampling.LANCZOS).rotate(
                p['rotation']*180/np.pi, resample=Image.Resampling.BICUBIC, expand=True)
            sprite.putalpha(sprite.getchannel('A').point(lambda a: round(a*p['alpha'])))
            # Six nearby positions loop without a large teleport of every dot.
            phase = 2*np.pi*state/6+p['phase']
            x = p['x']+np.sin(phase)*1.5
            y = p['y']+np.cos(phase)*1.1
            canvas.alpha_composite(sprite, (round(x-sprite.width/2), round(y-sprite.height/2)))
        canvas.save(out/f'dust-state-{state}.png')
    return particles


def make_title(out):
    # Fixed lettering geometry. Only nib pressure, dry skips and edge granules
    # change between states; neither the glyphs nor the whole line is translated.
    scale = 4
    font = ImageFont.truetype(str(FONT), FONT_PX*scale)
    widths = [font.getlength(ch)/scale for ch in TITLE]
    total = sum(widths)+LETTER_SPACING*(len(TITLE)-1)
    base = np.random.default_rng(191019).uniform(-1, 1, (len(TITLE), 2))
    canvas = Image.new('RGBA', tuple(n*scale for n in TITLE_SIZE))
    x = (TITLE_SIZE[0]-total)/2
    for index, (ch, width) in enumerate(zip(TITLE, widths)):
        glyph = Image.new('RGBA', (int((width+28)*scale), 108*scale))
        ImageDraw.Draw(glyph).text((glyph.width/2, glyph.height/2), ch,
            font=font, anchor='mm', fill=(14, 12, 9, 255),
            stroke_width=3, stroke_fill=(14, 12, 9, 255))
        glyph = glyph.rotate(base[index, 0]*1.8, Image.Resampling.BICUBIC)
        canvas.alpha_composite(glyph, (round((x+width/2)*scale-glyph.width/2),
            round((TITLE_SIZE[1]/2+base[index, 1]*2.0)*scale-glyph.height/2)))
        x += width+LETTER_SPACING
    bounds = canvas.getbbox()
    ink_origin = (round((canvas.width-bounds[0]-bounds[2])/2),
                  round((canvas.height-bounds[1]-bounds[3])/2))
    centered = Image.new('RGBA', canvas.size)
    centered.alpha_composite(canvas, ink_origin)
    mask = (np.array(centered.getchannel('A')) > 127).astype(np.uint8)
    distance = (cv2.distanceTransform(mask, cv2.DIST_L2, 5)
                - cv2.distanceTransform(1-mask, cv2.DIST_L2, 5))
    near_edge = 1-smoothstep(.5*scale, 1.6*scale, np.abs(distance))
    states = []
    for state in range(6):
        rng = np.random.default_rng(191019+state)
        pressure = grid_noise(rng, 140, 18, centered.width, centered.height)
        granules = grid_noise(rng, 700, 90, centered.width, centered.height)
        edge_width = np.clip(.22*pressure+.12*granules, -.4, .4)*scale
        coverage = smoothstep(-.65, .65, distance+edge_width)
        dry_skips = smoothstep(1.0, 2.0, granules)
        coverage *= (1-.38*dry_skips*near_edge)*(.90+.10*smoothstep(-1.8, 1.8, pressure))
        # Tiny low-opacity ink crumbs stay within 1.6px of the fixed outline.
        crumbs = (distance < 0)*near_edge*smoothstep(1.3, 2.0, granules)*.20
        alpha = np.uint8(np.clip(np.maximum(coverage, crumbs)*255, 0, 255))
        canvas = Image.new('RGBA', centered.size, (14, 12, 9, 0))
        canvas.putalpha(Image.fromarray(alpha))
        canvas = canvas.resize(TITLE_SIZE, Image.Resampling.LANCZOS)
        canvas.save(out/f'all-collected-title-state-{state}.png')
        states.append(canvas)
    states[0].save(out/'all-collected-title.png')
    full = Image.new('RGBA', (W, H))
    full.alpha_composite(states[0], (960-TITLE_SIZE[0]//2, 577-TITLE_SIZE[1]//2))
    full.save(out/'all-collected-title-full.png')
    return full


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'godot/chorus-four/assets/paint-finish')
    parser.add_argument('--review', type=Path, default=DELIVERY/'粉刷全收集')
    parser.add_argument('--brush', type=Path, default=BRUSH)
    args = parser.parse_args()
    out, review = args.out, args.review
    out.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261018)
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    angle = np.deg2rad(STROKE_ANGLE)
    direction = np.array([np.cos(angle), -np.sin(angle)])
    along_px = direction[0]*xx+direction[1]*yy
    along_span = float(np.ptp(along_px))
    along = (along_px-along_px.min())/along_span
    across = np.sin(angle)*xx+np.cos(angle)*yy
    profile, native_brush = brush_assets(out, args.brush)
    # Eight irregular bristle groups make the loaded brush head readable.
    bristle = np.interp(np.mod(across, 230)/230*(len(profile)-1),
                         np.arange(len(profile)), profile)
    group_positions = np.linspace(0, float(across.max()), 8)
    group_offsets = np.array([42, -72, 61, -51, 85, -64, 48, -30], np.float32)
    front = np.interp(across, group_positions, group_offsets)/along_span
    irregular = grid_noise(rng, 160, 90)*.0075+grid_noise(rng, 640, 360)*.002
    arrival = along+front+(1-bristle)*.063+irregular
    arrival = .025+.95*(arrival-arrival.min())/(arrival.max()-arrival.min())
    # R=arrival, identical RGB channels make Godot import straightforward.
    Image.fromarray(np.uint8(arrival*255)).convert('RGB').save(out/'paint-arrival.png')
    # Map the source's two-dimensional dry fibres to the same 80-degree axes.
    brush_detail = cv2.remap(native_brush,
        np.float32(along*(native_brush.shape[1]-1)),
        np.float32((.12+.76*np.mod(across, 360)/360)*(native_brush.shape[0]-1)),
        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # Sparse discontinuous skips interrupt the long fibres like a lightly loaded
    # wall brush. They fill behind the front instead of surviving as CG pinholes.
    skips = smoothstep(.65, 1.8, grid_noise(rng, 384, 216))
    brush_detail = np.clip(brush_detail*(1-.58*skips), 0, 1)
    Image.fromarray(np.uint8(np.clip(brush_detail, 0, 1)*255)).save(out/'paint-bristle-detail.png')
    granules = grid_noise(rng, 480, 270)
    relief = granules-np.roll(granules, (2, 1), axis=(0, 1))
    common = dict(broad=grid_noise(rng, 20, 12), relief=relief,
                  clumps=grid_noise(rng, 192, 108),
                  pits=np.maximum(grid_noise(rng, 640, 360)-1.2, 0),
                  tracks=brush_detail-.6,
                  bristle=rng.normal(0, 1, 350).astype(np.float32))
    for state in range(6):
        wall = make_wall(rng, yy, xx, across, state, common)
        wall.save(out/f'wall-state-{state}.png')
    make_wet_paint(along, across, brush_detail).save(out/'paint-surface.png')
    particles = make_dust(out)
    title = make_title(out)
    metadata = dict(canvas=[W, H], brush_source=str(args.brush),
        eagle_item='LP88LES5EY98D', bridge_source='tools/build-bridge-montage.py:intertitles',
        font=str(FONT), font_px=FONT_PX, letter_spacing_px=LETTER_SPACING,
        font_source='https://github.com/google/fonts/tree/main/ofl/yomogi',
        font_license='assets/fonts/OFL-Yomogi.txt',
        title=TITLE, text_source=str(TEXT_SOURCE),
        title_texture='all-collected-title.png', title_position=[960, 577],
        title_style='Fixed Yomogi lettering; six ink-edge grain, dry-skip and pressure variants',
        title_edge_variation_px=.4, title_transform_jitter=False,
        title_states=[f'all-collected-title-state-{i}.png' for i in range(6)],
        title_state_rate_hz=10,
        wall_states=[f'wall-state-{i}.png' for i in range(6)],
        dust_states=[f'dust-state-{i}.png' for i in range(6)], state_rate_hz=12,
        arrival_texture='paint-arrival.png', paint_texture='paint-surface.png',
        direction='80 degrees from horizontal, upwards and slightly right',
        stroke_angle_degrees=STROKE_ANGLE, stroke_vector_image=direction.tolist(),
        brush_head_group_offsets_px=group_offsets.tolist(),
        bristle_texture='paint-bristle-detail.png', wet_surface='paint-surface.png',
        coverage='Broken 0.003 arrival edge; 80% dry-bristle skips settle over 0.30 progress behind the front',
        roughness='Anchored 3-10px paint relief, clumps and stroke tracks; six-state fine grain at 12Hz',
        complete='At progress=1 every pixel is opaque; do not keep dry holes at the end.',
        particles=particles,
        scope='Local paint/end-card assets only; no puppet, sequence or bell changes')
    (out/'paint-finish.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    source = Image.open(DELIVERY/'inputs/CGC15_c-user-20261018.png').convert('RGB').resize((W, H), Image.Resampling.LANCZOS)
    surface = np.array(Image.open(out/'paint-surface.png')).astype(np.float32)
    paper = np.array(Image.open(out/'wall-state-0.png')).astype(np.float32)
    contact = Image.new('RGB', (W, 772), '#252525')
    small_font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    for i, progress in enumerate([0, .22, .44, .66, .86, 1.0]):
        fresh = (1-smoothstep(0, .30, progress-arrival))*(1-smoothstep(.88, 1, progress))
        coverage = (1-smoothstep(progress-.003, progress+.003, arrival))*(1-.80*(1-brush_detail)*fresh)
        pigment = paper*(1-fresh[..., None]*.9)+surface*fresh[..., None]*.9
        rgb = np.array(source)*(1-coverage[..., None])+pigment*coverage[..., None]
        frame = Image.fromarray(np.uint8(rgb)).convert('RGBA')
        if i == 5:
            frame.alpha_composite(Image.open(out/'dust-state-0.png'))
            frame.alpha_composite(title)
            frame.save(review/'全收集-静态检查.png')
        x, y = (i%3)*640, (i//3)*386
        contact.paste(frame.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS), (x, y+26))
        ImageDraw.Draw(contact).text((x+10, y+3), f'粉刷进度 {progress:.0%}', font=small_font, fill='white')
    contact.save(review/'粉刷80度覆盖-检查.jpg', quality=95)
    Image.open(out/'wall-state-0.png').crop((720, 340, 1200, 700)).resize((960, 720)).save(review/'粉墙颗粒-局部检查.png')
    print(json.dumps(dict(assets=str(out), review=str(review), font=str(FONT),
        states=6, title=TITLE, arrival_range=[float(arrival.min()), float(arrival.max())]), ensure_ascii=False))


if __name__ == '__main__':
    main()
