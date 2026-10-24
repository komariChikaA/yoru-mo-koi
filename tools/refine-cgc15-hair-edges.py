"""Repair observed CGC15 matte stair steps; retain native RGB and rig settings."""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
CG = OUT/'头发逐层重拆/CGC15'
WORK = CG/'edge-fix-20261018'
STAGE = CG/'stage-cliff-wind-v2-edge-refined'
DELIVERY = OUT/'CGC15边缘与时序修订-20261018'
GODOT = Path('D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def vector_alpha(paths, size, curve_samples=300, full_canvas=False):
    alpha = np.zeros((size[1], size[0]), np.uint8)
    for path in paths:
        tokens = re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?', path)
        i, points, current = 0, [], np.zeros(2)
        while i < len(tokens):
            command = tokens[i]
            i += 1
            if command in ('M', 'L'):
                current = np.array(tokens[i:i+2], float)
                i += 2
                points.append(current)
            elif command == 'C':
                values = np.array(tokens[i:i+6], float).reshape(3, 2)
                i += 6
                start = current
                for t in np.linspace(0, 1, curve_samples)[1:]:
                    points.append((1-t)**3*start+3*(1-t)**2*t*values[0]
                                  +3*(1-t)*t*t*values[1]+t**3*values[2])
                current = values[2]
        points = np.array(points)
        if full_canvas:
            # R10's reviewed raster used the complete 8x canvas. Retaining it
            # also preserves four 1/255 alpha values affected by crop rounding.
            canvas = Image.new('L', (size[0]*8, size[1]*8))
            ImageDraw.Draw(canvas).polygon([tuple(v*8) for v in points], fill=255)
            alpha = np.maximum(alpha, np.array(canvas.resize(size, Image.Resampling.LANCZOS)))
            continue
        low = np.maximum(0, np.floor(points.min(0)-3)).astype(int)
        high = np.minimum(size, np.ceil(points.max(0)+4)).astype(int)
        local = Image.new('L', tuple((high-low)*8))
        ImageDraw.Draw(local).polygon([tuple((v-low)*8) for v in points], fill=255)
        coverage = Image.new('L', size)
        coverage.paste(local.resize(tuple(high-low), Image.Resampling.LANCZOS), tuple(low))
        alpha = np.maximum(alpha, np.array(coverage))
    return alpha


def fixed_distance(part, shape):
    line = np.array(part['fixed_transition']['cut_line'], float)
    cross = line[1]-line[0]
    cross /= np.linalg.norm(cross)
    axis = np.array([cross[1], -cross[0]])
    axis *= np.sign(np.dot(axis, np.array(part['chain'][1])-part['chain'][0]))
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return (xx-line[0, 0])*axis[0]+(yy-line[0, 1])*axis[1]


def repair_r10(rgba, part):
    original = rgba[:, :, 3]
    # The reviewed 8x vector candidate restores the original brown lower edge
    # and both fine forks; colour-threshold smoothing was explicitly rejected.
    # R10 was reviewed with 200 samples per cubic; R11/R12 used 300. Keep
    # those exact rasterisation parameters so approved alpha is reproducible.
    alpha = vector_alpha(part['outlines'], (rgba.shape[1], rgba.shape[0]),
                         curve_samples=200, full_canvas=True)
    distance = fixed_distance(part, alpha.shape)
    alpha[distance <= part['fixed_transition']['root_band_px']] = original[distance <= part['fixed_transition']['root_band_px']]
    return alpha


def repair_r11(rgba, part):
    alpha = vector_alpha(part['outlines'], (rgba.shape[1], rgba.shape[0]))
    # Smooth the observed short artificial corner where the side fork meets the
    # main lower contour, not the native vertically returned fine strand.
    box = (1612, 329, 1655, 378)
    x0, y0, x1, y1 = box
    local = alpha[y0:y1, x0:x1]
    inside = np.uint8(local >= 128)
    signed = cv2.distanceTransform(inside, cv2.DIST_L2, 5)-cv2.distanceTransform(1-inside, cv2.DIST_L2, 5)
    smooth = cv2.GaussianBlur(signed, (13, 13), 2.0)
    coverage = np.uint8(np.rint(np.clip(.5+smooth/1.1, 0, 1)*255))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    weight = np.clip((12-np.hypot(xx-1630, yy-352))/5, 0, 1)
    alpha[y0:y1, x0:x1] = np.uint8(np.rint(local*(1-weight)+coverage*weight))
    fixed = fixed_distance(part, alpha.shape) <= part['fixed_transition']['root_band_px']
    alpha[fixed] = rgba[:, :, 3][fixed]
    return alpha


def repair_r12(rgba, part):
    alpha = rgba[:, :, 3].copy()
    # Replace only the stepped main upper arc. The lower independent fine fork
    # and the entire fixed cross-section retain their original exact alpha.
    top_path = ('M1425,296 C1467,280 1504,279 1534,292 '
                'C1572,308 1597,344 1619,380 L1619,1080 L1425,1080 Z')
    upper = vector_alpha([top_path], (rgba.shape[1], rgba.shape[0]))
    inside = np.uint8(upper >= 128)
    signed = cv2.distanceTransform(inside, cv2.DIST_L2, 5)-cv2.distanceTransform(1-inside, cv2.DIST_L2, 5)
    yy, xx = np.mgrid[:alpha.shape[0], :alpha.shape[1]]
    region = (xx >= 1458)&(xx <= 1600)&(yy < 365)&(abs(signed) < 8)
    alpha[region] = upper[region]
    fixed = fixed_distance(part, alpha.shape) <= part['fixed_transition']['root_band_px']
    alpha[fixed] = rgba[:, :, 3][fixed]
    return alpha


def candidate():
    WORK.mkdir(exist_ok=True)
    record = read(CG/'stage-cliff-wind-v2/stage.json')
    for key, repair, box in [('R10', repair_r10, (1430, 70, 1810, 480)),
                             ('R11', repair_r11, (1420, 175, 1720, 440)),
                             ('R12', repair_r12, (1410, 270, 1640, 400))]:
        candidate_part(record, key, repair, box)


def candidate_part(record, key, repair, box):
    part = next(x for x in record['parts'] if key+'-' in x['id'])
    image = Image.open(part['native_texture']).convert('RGBA')
    rgba = np.array(image)
    new = rgba.copy()
    new[:, :, 3] = repair(rgba, part)
    Image.fromarray(new).save(WORK/(key+'-fixed-seam-vector-candidate.png'))
    source = Image.open(Path(part['native_texture']).parent/'before.png').convert('RGB')
    panels = [source, Image.alpha_composite(Image.new('RGBA', image.size, '#50687a'), image).convert('RGB'),
              Image.alpha_composite(Image.new('RGBA', image.size, '#50687a'), Image.fromarray(new)).convert('RGB')]
    w, h = (box[2]-box[0])*3, (box[3]-box[1])*3
    sheet = Image.new('RGB', (3*w, h+35), '#202a34')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    for i, panel in enumerate(panels):
        sheet.paste(panel.crop(box).resize((w, h), Image.Resampling.NEAREST), (w*i, 35))
        draw.text((w*i+10, 5), ['原图', '修前切片', key+'轮廓修复 / 固定截面保留'][i], font=font, fill='white')
    sheet.save(WORK/(key+'-固定截面-原图修前修后.png'))
    print(WORK/(key+'-固定截面-原图修前修后.png'))


def build():
    candidate()
    STAGE.mkdir(exist_ok=True)
    DELIVERY.mkdir(exist_ok=True)
    source = CG/'stage-cliff-wind-v2'
    record = read(source/'stage.json')
    repaired_ids = []
    for key in ['R10', 'R11', 'R12']:
        part = next(x for x in record['parts'] if key+'-' in x['id'])
        old = np.array(Image.open(part['native_texture']).convert('RGBA'))
        repaired = np.array(Image.open(WORK/(key+'-fixed-seam-vector-candidate.png')).convert('RGBA'))
        assert np.array_equal(old[:, :, :3], repaired[:, :, :3]), 'Native RGB must remain exact'
        fixed = fixed_distance(part, old.shape[:2]) <= part['fixed_transition']['root_band_px']
        assert np.array_equal(old[:, :, 3][fixed], repaired[:, :, 3][fixed]), 'Fixed alpha must remain exact'
        target = STAGE/(part['id']+'-native.png')
        Image.fromarray(repaired).save(target)
        part['native_texture'] = str(target)
        repaired_ids.append(part['id'])
        shutil.copyfile(WORK/(key+'-固定截面-原图修前修后.png'), DELIVERY/('CGC15-'+key+'-原图修前修后.png'))
    record['edge_repair'] = dict(
        source_stage=str(source), repaired_parts=repaired_ids,
        method='Reviewed 8x vector contour matte; original native RGB and complete fixed root alpha retained',
        unchanged='All other native textures, plate, overlays, order, gain, bend, model and wind phase')
    (STAGE/'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(source/'repaired-plate.png', STAGE/'repaired-plate.png')
    print(STAGE)


def metrics():
    command = [str(GODOT), '--headless', '--path', str(ROOT/'godot/chorus-four'),
               '--audio-driver', 'Dummy', '--script', 'res://hair-redo/preview.gd', '--',
               '--stage', str(STAGE), '--cg', '15', '--seconds', '9.2', '--metrics-only', 'true']
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    stdout, stderr = result.stdout.decode('utf-8'), result.stderr.decode('utf-8')
    (STAGE/'metrics-120hz.stdout.log').write_text(stdout, encoding='utf-8')
    (STAGE/'metrics-120hz.stderr.log').write_text(stderr, encoding='utf-8')
    assert result.returncode == 0 and not any(x in stderr for x in ['SCRIPT ERROR:', 'ERROR:']), stderr
    proof = next(json.loads(line.removeprefix('SHORT_PREVIEW_PROOF '))
                 for line in stdout.splitlines() if line.startswith('SHORT_PREVIEW_PROOF '))
    assert proof['geometry_samples'] == 1104
    (STAGE/'metrics-120hz-final-formal.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    record = read(STAGE/'stage.json')
    resolved = []
    for p in record['parts']:
        setting = {key: p[key] for key in ['id', 'motion_gain', 'deformation_model', 'bend_length_px']}
        setting['sway_percent'] = p.get('sway_percent', 10)
        resolved.append(setting)
    summary = dict(cg=15, stages=[str(STAGE)], parts=[p['id'] for p in record['parts']],
                   strength=1, seconds=9.2, wind_time_offset=1.4,
                   resolved_motion=resolved, sample_times=[0, .6, 1.2, 1.8, 2.5],
                   frames=5, fps=60, proof=proof, geometry_sampling_hz=120,
                   repaired_parts=record['edge_repair']['repaired_parts'],
                   scope='CGC15 R10/R11 contour alpha repair and R12 main upper arc only. Full 9.2s geometry at 120Hz; selected real GPU moving-phase closeups. Existing motion, grouping, native RGB and fixed support preserved. User perceptual acceptance pending.')
    (DELIVERY/'CGC15-边缘修复-记录.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


def evidence():
    samples = [0, .6, 1.2, 1.8, 2.5]
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
    contact = Image.new('RGB', (1920, len(samples)*305), '#202a34')
    contact_draw = ImageDraw.Draw(contact)
    images = []
    for index, time in enumerate(samples):
        before = Image.open(DELIVERY/'CGC15-边缘修前-右上GPU-render/frames'/f'frame-{index:04d}.png').convert('RGB')
        after = Image.open(DELIVERY/'CGC15-边缘修后-右上GPU-render/frames'/f'frame-{index:04d}.png').convert('RGB')
        result = Image.new('RGB', (2560, 760), '#202a34')
        draw = ImageDraw.Draw(result)
        result.paste(before, (0, 40))
        result.paste(after, (1280, 40))
        draw.text((15, 5), f'修前：原生选区台阶 / t={time:.1f}s', font=font, fill='white')
        draw.text((1295, 5), f'修后：R10/R11/R12边缘 / t={time:.1f}s', font=font, fill='white')
        path = DELIVERY/f'CGC15-右上GPU修前修后-{time:.1f}s.png'
        result.save(path)
        images.append(str(path))
        # Hair occupies the upper half of the GPU crop; keep that area large in
        # the contact sheet rather than reducing the detailed matte comparison.
        for column, image in enumerate([before, after]):
            contact.paste(image.crop((0, 0, 1280, 360)).resize((960, 270), Image.Resampling.LANCZOS),
                          (column*960, index*305+35))
            contact_draw.text((column*960+10, index*305+4),
                              f'{"修前" if column == 0 else "修后"} / {time:.1f}s', font=font, fill='white')
    contact_path = DELIVERY/'CGC15-右上GPU五相位修前修后.jpg'
    contact.save(contact_path, quality=96)
    record_path = DELIVERY/'CGC15-边缘修复-记录.json'
    record = read(record_path)
    record['evidence'] = dict(native_comparisons=[str(DELIVERY/f'CGC15-{key}-原图修前修后.png')
                                                 for key in ['R10', 'R11', 'R12']],
                              real_gpu_comparisons=images, gpu_contact_sheet=str(contact_path))
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(contact_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['candidate', 'build', 'metrics', 'evidence'])
    args = parser.parse_args()
    globals()[args.action]()
