"""Restore only the native R10 support join; leave the previous stage intact."""
import copy
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
SOURCE = OUT / '头发逐层重拆/CGC15/stage-cliff-wind-v2-edge-refined'
TARGET = SOURCE.parent / 'stage-reference-wind-root-clean'
USER = OUT / 'inputs/CGC15_c-user-20261018.png'
REVIEW = OUT / '头发参考重制-20261018'
PART = '15-R10-upper-falling-lock'


def smooth(low, high, value):
    u = np.clip((value-low)/(high-low), 0, 1)
    return u*u*(3-2*u)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def composite(stage, plate, replacement=None):
    image = Image.fromarray(plate).convert('RGBA')
    for part in sorted(stage['parts'], key=lambda p: p['depth'], reverse=True):
        layer = replacement if part['id'] == PART and replacement is not None else Image.open(part['native_texture']).convert('RGBA')
        if layer.size != image.size:
            layer = layer.crop((0, 0, *image.size))
        image = Image.alpha_composite(image, layer)
    return image.convert('RGB')


def build():
    stage = read(SOURCE / 'stage.json')
    part = next(p for p in stage['parts'] if p['id'] == PART)
    native = np.array(Image.open(USER).convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS))
    rgba = np.array(Image.open(part['native_texture']).convert('RGBA'))
    plate = np.array(Image.open(SOURCE / 'repaired-plate.png').convert('RGB'))
    fixed = rgba.copy()

    # The RGB already is the user's native image. The retained old threshold
    # alpha drops the brown underside, then steps into the newer vector matte.
    # Locate that one lower contour in the native image, before the next lock.
    columns = np.arange(1450, 1531)
    lower = []
    upper = []
    for x in columns:
        signal = native[145:180, x, 1].astype(float)-0.5*native[145:180, x, 0]
        rows = np.flatnonzero(signal > 0)
        y = int(rows[-1])+145
        a = float(native[y, x, 1])-0.5*float(native[y, x, 0])
        b = float(native[y+1, x, 1])-0.5*float(native[y+1, x, 0])
        lower.append(y+np.clip(a/max(1e-6, a-b), 0, 1))
        upper.append(int(np.flatnonzero(rgba[70:145, x, 3] > 128)[0])+70)
    lower = np.array(lower)
    lower = np.convolve(np.pad(lower, 1, mode='edge'), [.25, .5, .25], mode='valid')
    upper = np.array(upper)
    for index, x in enumerate(columns):
        y = np.arange(1080)
        coverage = np.clip(lower[index]+0.5-y, 0, 1)
        coverage[y <= upper[index]] = 0
        weight = 1-smooth(1490, 1530, float(x))
        old = rgba[:, x, 3].astype(float)
        fixed[:, x, 3] = np.uint8(np.rint(old+weight*(np.maximum(old, 255*coverage)-old)))

    # Restore the held upstream pixels and red background at the join. Never
    # paint native moving hair back into its hidden plate on the free side.
    yy, xx = np.mgrid[:1080, :1920]
    vertical = smooth(65, 85, yy)*(1-smooth(220, 240, yy))
    horizontal = smooth(1410, 1440, xx)*(1-smooth(1450, 1490, xx))
    foreground = np.zeros((1080, 1920), bool)
    for other in stage['parts']:
        if other['id'] == PART:
            continue
        alpha = np.array(Image.open(other['native_texture']).convert('RGBA'))[:1080, :1920, 3]
        foreground |= alpha > 3
    red_background = native[:, :, 1].astype(float)-0.5*native[:, :, 0] < -10
    allowed = (xx <= 1450) | (red_background & ~foreground & (fixed[:, :, 3] == 0))
    weight = horizontal*vertical*allowed
    new_plate = np.uint8(np.rint(plate*(1-weight[:, :, None])+native*weight[:, :, None]))

    TARGET.mkdir(parents=True, exist_ok=True)
    target_texture = TARGET / (PART+'-native.png')
    target_mask = TARGET / (PART+'-root-clean-mask.png')
    Image.fromarray(fixed).save(target_texture)
    Image.fromarray(fixed[:, :, 3]).save(target_mask)
    Image.fromarray(new_plate).save(TARGET / 'repaired-plate.png')
    updated = copy.deepcopy(stage)
    repaired = next(p for p in updated['parts'] if p['id'] == PART)
    repaired['native_texture'] = str(target_texture)
    repaired['alpha_mask'] = str(target_mask)
    updated['base_stage'] = str(SOURCE)
    changed_alpha = fixed[:, :, 3] != rgba[:, :, 3]
    changed_plate = np.any(new_plate != plate, axis=2)
    alpha_box = (xx >= 1450) & (xx <= 1530) & (yy >= 70) & (yy < 180)
    plate_box = (xx >= 1410) & (xx < 1490) & (yy >= 65) & (yy < 240)
    assert np.array_equal(fixed[:, :, :3], rgba[:, :, :3])
    assert not np.any(changed_alpha & ~alpha_box)
    assert not np.any(changed_plate & ~plate_box)
    assert repaired['fixed_transition'] == part['fixed_transition']
    for old, new in zip(stage['parts'], updated['parts']):
        if old['id'] != PART:
            assert old == new
    proof = {
        'source_stage': str(SOURCE), 'user_image': str(USER),
        'normalized_size': [1920, 1080], 'normalized_resampling': 'Pillow LANCZOS',
        'root_cause': 'Native RGB is exact; retained threshold alpha loses the brown underside and steps into vector alpha, while nearby held plate pixels differ from native.',
        'repaired_part': PART, 'alpha_edit_box': [1450, 70, 1531, 180],
        'plate_edit_box': [1410, 65, 1490, 240],
        'alpha_transition_x': [1490, 1530], 'plate_transition_px': [30, 40],
        'alpha_changed_pixels': int(changed_alpha.sum()),
        'plate_changed_pixels': int(changed_plate.sum()),
        'rgb_changed_pixels': 0, 'outside_boxes_changed_pixels': 0,
        'fixed_support_and_rig': 'unchanged', 'other_parts': 'unchanged absolute references',
        'gpu_validation': 'pending final GPU',
    }
    updated['reference_root_repair'] = proof
    (TARGET / 'stage.json').write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    (TARGET / 'root-repair.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')

    box = (1395, 80, 1540, 225)
    panels = [Image.fromarray(native), composite(stage, plate), composite(updated, new_plate, Image.fromarray(fixed))]
    sheet = Image.new('RGB', (145*4*3, 145*4+36), '#202020')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    for i, (label, panel) in enumerate(zip(['用户原图', '旧静态接合', '局部原生接合修复'], panels)):
        sheet.paste(panel.crop(box).resize((580, 580), Image.Resampling.NEAREST), (580*i, 36))
        draw.text((580*i+8, 5), label, font=font, fill='white')
    REVIEW.mkdir(exist_ok=True)
    sheet.save(REVIEW / 'R10-根部修复-原图旧新版.png')
    print(json.dumps({'stage': str(TARGET), **proof}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
