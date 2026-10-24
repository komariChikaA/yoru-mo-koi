"""Refine only the isolated CGC14 right-U hidden plate from native material.

Run prepare-cgc14-right-followup.py --native-only first to refresh native v2.
This script never replaces repaired-plate.png or writes a production stage.
"""
from pathlib import Path
import argparse
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import PchipInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC14-right-followup.json'
PART = 'CGC14_RIGHT_LONG_U_LOOSE'


def native_sky_guide(base):
    """Take sunset gradients from the clear right/lower native sunset.

    The lower donor is below all loose tips. The upper donor lies to the
    right of the original U. A smooth transition keeps the sky strokes
    continuous without a tiled seam or an inpainting blur.
    """
    height, width = base.shape[:2]
    yy, xx = np.indices((height, width), np.float32)
    t = np.clip((yy - 780) / 60, 0, 1)
    t = t * t * (3 - 2 * t)
    return cv2.remap(
        base, np.minimum(width - 1, xx + 140 - 40 * t),
        np.minimum(height - 1, yy + 120 * t), cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101).astype(float)


def deeper_native_strip(base, guide, destination, edit):
    """Bridge the native brown rear strip across the removed U bend.

    Edge positions follow its visible upper/lower cross-sections. Native
    transverse colour profiles at y875 and y935 provide its linework and
    shading; visible native portions remain exact.
    """
    height, width = edit.shape
    strip = np.zeros((height, width), bool)
    left = PchipInterpolator(
        [800, 850, 875, 900, 920, 935, 950, 955],
        [1582.0, 1585.0, 1585.6, 1586.5, 1584.4, 1581.7, 1579.0, 1577.8])
    right = PchipInterpolator(
        [800, 850, 875, 900, 920, 935, 950, 955],
        [1603.0, 1607.8, 1608.8, 1610.8, 1610.9, 1610.1, 1608.7, 1608.0])
    native_x = np.arange(width)
    for y in range(800, 956):
        lo, hi = float(left(y)), float(right(y))
        xs = np.arange(int(np.floor(lo)), int(np.ceil(hi)) + 1)
        across = (xs - lo) / (hi - lo)
        if y <= 875 or y >= 935:
            colours = base[y, xs].astype(float)
        else:
            t = (y - 875) / 60
            upper = np.stack([
                np.interp(1585.6 + across * (1608.8 - 1585.6),
                          native_x, base[875, :, c]) for c in range(3)], axis=-1)
            lower = np.stack([
                np.interp(1581.7 + across * (1610.1 - 1581.7),
                          native_x, base[935, :, c]) for c in range(3)], axis=-1)
            colours = (1 - t) * upper + t * lower
        guide[y, xs] = colours
        strip[y, xs] = True
        selected = edit[y, xs] > 0
        destination[y, xs[selected]] = colours[selected]
    return strip


def dirichlet_blend(guide, destination, unknown):
    """Solve the actual irregular mask; use exact native boundary pixels.

    This retains the sampled sunset gradients rather than smoothing the
    hole into a flat U band. The fixed foreground and rear strand have
    their own gradients in the guide and remain known boundary values.
    """
    height, width = unknown.shape
    ys, xs = np.where(unknown)
    count = len(xs)
    ids = np.full((height, width), -1, np.int32)
    ids[ys, xs] = np.arange(count)
    rows, cols = [np.arange(count)], [np.arange(count)]
    values = [np.full(count, 4.0)]
    rhs = 4 * guide[ys, xs]
    for dy, dx in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        ny, nx = ys + dy, xs + dx
        neighbour_ids = ids[ny, nx]
        inside = neighbour_ids >= 0
        rows.append(np.arange(count)[inside])
        cols.append(neighbour_ids[inside])
        values.append(np.full(np.count_nonzero(inside), -1.0))
        rhs -= guide[ny, nx]
        rhs[~inside] += destination[ny[~inside], nx[~inside]]
    matrix = coo_matrix(
        (np.concatenate(values), (np.concatenate(rows), np.concatenate(cols))),
        shape=(count, count)).tocsr()
    result = destination.copy()
    result[ys, xs] = spsolve(matrix, rhs)
    return np.uint8(np.clip(np.rint(result), 0, 255))


def review_sheet(stage, base, result, native, rear_native):
    crop = (1320, 520, 1820, 1020)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 21)
    problem = Image.open(stage / 'repaired-plate.png').convert('RGB')
    grey = Image.new('RGBA', native.size, '#465362')
    grey.alpha_composite(native)
    # This displacement is solely a hidden-plate inspection, not an
    # animation/deformation preview; the production support stays fixed.
    displaced = Image.fromarray(result).convert('RGBA')
    displaced.alpha_composite(rear_native)
    displaced.alpha_composite(native, (145, -20))
    foreground = Image.open(stage / 'static-B10-crossing-native.png').convert('RGBA')
    displaced.alpha_composite(foreground)
    assembled = Image.fromarray(result).convert('RGBA')
    assembled.alpha_composite(native)
    assembled.alpha_composite(foreground)
    assembled.convert('RGB').save(stage / 'native-refine-reassembled-v3.png')
    rear_join = Image.fromarray(result).convert('RGBA')
    rear_join.alpha_composite(rear_native)
    rear_join.crop((1510, 820, 1650, 1000)).resize((560, 720)).convert('RGB').save(
        stage / 'native-refine-r01-join-check-v3.png')
    sheet = Image.new('RGB', (2000, 545), '#202832')
    draw = ImageDraw.Draw(sheet)
    for index, (picture, label) in enumerate([
        (problem, '原补绘：U色带与后层断点'),
        (Image.fromarray(result), '原生纹理精修：移除U后的隐藏底'),
        (grey, '原生v2：完整外细环发体'),
        (displaced, '移开U＋后层R01连接（非动画预览）')]):
        sheet.paste(picture.convert('RGB').crop(crop), (index * 500, 45))
        draw.text((index * 500 + 10, 10), label, font=font, fill='white')
    sheet.save(stage / 'native-refine-review-v3.jpg', quality=97)
    Image.fromarray(result).crop(crop).resize((1000, 1000)).save(
        stage / 'native-refine-crop-v3.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path)
    args = parser.parse_args()
    definition = json.loads(DEFINITION.read_text(encoding='utf-8'))
    stage = args.stage or Path(definition['output'])
    stage_metadata = json.loads((stage / 'stage.json').read_text(encoding='utf-8'))
    prior_metadata = json.loads((Path(stage_metadata['base_stage']) / 'stage.json').read_text(encoding='utf-8'))
    rear_part = next(p for p in prior_metadata['parts'] if 'R01' in p['id'])
    rear_native = Image.open(rear_part['native_texture']).convert('RGBA')
    base = np.array(Image.open(stage / 'before.png').convert('RGB'))
    native = Image.open(stage / f'{PART}-native-v2.png').convert('RGBA')
    alpha = np.array(native.getchannel('A'))
    edit = cv2.dilate(np.uint8(alpha > 6) * 255, np.ones((21, 21), np.uint8))
    crossing = np.array(Image.open(
        stage / 'static-B10-crossing-native.png').getchannel('A')) > 0
    protected = cv2.dilate(crossing.astype('uint8'), np.ones((7, 7), np.uint8)) > 0
    edit[:550] = 0
    edit[protected] = 0
    guide = native_sky_guide(base)
    guide[protected] = base[protected]
    destination = base.astype(float).copy()
    strip = deeper_native_strip(base, guide, destination, edit)
    result = dirichlet_blend(guide, destination, (edit > 0) & ~strip)
    result[edit == 0] = base[edit == 0]
    output = stage / 'repaired-plate-native-refine-v3.png'
    Image.fromarray(result).save(output)
    Image.fromarray(edit).save(stage / 'native-refine-edit-v3.png')
    problem = np.array(Image.open(stage / 'repaired-plate.png').convert('RGB'))
    changed = np.uint8(np.any(result != problem, axis=2)) * 255
    Image.fromarray(changed).save(stage / 'native-refine-changed-v3.png')
    final_part = dict(next(p for p in stage_metadata['parts'] if p['id'] == PART))
    final_part.update(definition['part'])
    final_part.update(native_texture=str(stage / f'{PART}-native-v2.png'),
                      ready_for_extract=True,
                      status='native-v2-hidden-refined-awaiting-gpu-review')
    (stage / 'native-part-definition-v2.json').write_text(
        json.dumps(final_part, ensure_ascii=False, indent=2), encoding='utf-8')
    refined_metadata = dict(stage_metadata)
    refined_metadata.update(
        parts=[final_part], repaired_plate=str(output),
        state='native-v2-hidden-refined-awaiting-gpu-review',
        refinement_script=str(Path(__file__).resolve()),
        edit_mask=str(stage / 'native-refine-edit-v3.png'),
        rear_root_continuity='static deep strip reconstructed to native lower section y935..955; R01 starts at fixed y950')
    (stage / 'native-refine-stage-v3.json').write_text(
        json.dumps(refined_metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    delta = np.abs(result.astype(int) - base.astype(int))
    checks = dict(
        output=str(output), input=str(stage / 'before.png'),
        native=str(stage / f'{PART}-native-v2.png'),
        native_mask=str(stage / f'{PART}-mask-v2.png'),
        part_definition=str(stage / 'native-part-definition-v2.json'),
        stage_metadata=str(stage / 'native-refine-stage-v3.json'),
        edit_mask=str(stage / 'native-refine-edit-v3.png'),
        changed_mask=str(stage / 'native-refine-changed-v3.png'),
        outside_edit_max_rgb=int(delta[edit == 0].max()),
        above_fixed_cross_section_max_rgb=int(delta[:550].max()),
        static_b10_all_pixels_max_rgb=int(delta[crossing].max()),
        selected_above_fixed_cross_section=int(np.count_nonzero(alpha[:550])),
        edited_pixel_count=int(np.count_nonzero(edit)),
        changed_from_problem_pixel_count=int(np.count_nonzero(changed)),
        rear_strip_bridge_rows=[876, 934],
        rear_root_native=str(rear_part['native_texture']),
        rear_root_join_check=str(stage / 'native-refine-r01-join-check-v3.png'),
        method='native adjacent sunset gradients with irregular-mask Dirichlet solve; native upper/lower rear-strip profiles',
        scope='isolated outputs only; repaired-plate.png, production stages and runtime are not written')
    (stage / 'native-refine-record-v3.json').write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    review_sheet(stage, base, result, native, rear_native)
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
