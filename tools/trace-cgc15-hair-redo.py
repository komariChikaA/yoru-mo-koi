"""Export CGC15 support-to-free-end hair masks from the authored trace JSON.

Only ready_for_extract entries are exported as current cutouts. Deprecated scalp
pieces and incomplete later-layer outlines are never restored by this helper.
"""
from pathlib import Path
import importlib.util
import json
import argparse
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC15-traces.json'
OUT = Path('../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆/CGC15')


def prepare_side_arc(definition, helper):
    """Separate the narrow foreground arc before extracting the wide side lock.

    Only the arc pixels inside the downstream wide lock are repaired. Its
    exposed portion over clothing/skin remains untouched in the lower plate.
    Near the upper material edge both sides are not the same material, so use
    the nearest clean native hair on the inward side rather than blending in
    pink collar pixels.
    """
    part = next(p for p in definition['front_to_back'] if p['id'] == '15-F02-chin-side-free-band')
    arc = next(p for p in definition['stationary_foreground'] if p['id'] == '15-S02-side-curved-flyaway')
    prior = OUT / 'stage-15-F00-loose-fringe-cluster-detail-v2/isolated-preview'
    stage = OUT / 'stage-15-S02-static-arc-local-removal'
    stage.mkdir(exist_ok=True)
    image = Image.open(prior / 'repaired-plate.png').convert('RGB')
    rgb = np.array(image)
    full = np.array(helper.part_mask(arc))
    band = np.array(helper.part_mask(part))
    repair = np.minimum(full, band)
    repair = helper.clip_supported_side(repair, part)
    yy, xx = np.mgrid[:1080, :1920].astype(np.float32)
    # Inward normal of the native wide-band flow (about 0.35 down/right).
    vx, vy = -0.33035, 0.94386
    blocked = cv2.dilate(np.uint8(full > 4)*255, np.ones((3, 3), np.uint8))
    # The support cut clips the moving extraction, not its upstream native
    # texture: a clean source just left of that cut is still the same lock.
    r, g, b = rgb.astype(np.int16).transpose(2, 0, 1)
    native_hair = np.uint8((g-b > 6) & (r-g > 20) & (r < 240))*255
    distance = np.zeros_like(xx)
    pending = repair > 0
    for step in range(1, 19):
        clean = cv2.remap(blocked, xx+vx*step, yy+vy*step, cv2.INTER_NEAREST) == 0
        inside = cv2.remap(native_hair, xx+vx*step, yy+vy*step, cv2.INTER_NEAREST) > 240
        found = pending & clean & inside
        distance[found] = step+0.75
        pending[found] = False
    assert not np.any(pending), 'Side arc repair has no same-hair inward source'
    replacement = cv2.remap(rgb, xx+vx*distance, yy+vy*distance, cv2.INTER_CUBIC)
    weight = (repair.astype(np.float32)/255)[:, :, None]
    clean = np.uint8(np.clip(rgb*(1-weight)+replacement*weight, 0, 255))
    image.save(stage / 'before.png')
    Image.fromarray(clean).save(stage / 'repaired-plate.png')
    Image.fromarray(full).save(stage / 'static-side-curved-flyaway-mask.png')
    Image.fromarray(repair).save(stage / 'local-repair-mask.png')
    overlay = image.convert('RGBA')
    overlay.putalpha(Image.fromarray(full))
    overlay.save(stage / 'static-side-curved-flyaway.png')
    record = json.loads((prior / 'stage.json').read_text(encoding='utf-8-sig'))
    inherited = []
    for overlay_ref in record.get('static_overlays', []):
        assert isinstance(overlay_ref, str), 'Expected existing static PNG overlays'
        overlay_path = Path(overlay_ref)
        inherited.append(str(overlay_path if overlay_path.is_absolute() else prior/overlay_path))
    record.update(input=str(prior / 'repaired-plate.png'), ids=[], parts=[],
        state='static-arc-locally-separated-awaiting-root-review',
        static_overlays=inherited+[str(stage / 'static-side-curved-flyaway.png')],
        static_arc_definition=arc,
        static_arc_local_repair={
            'mask': str(stage / 'local-repair-mask.png'),
            'method': 'nearest clean native wide-lock hair sampled inward normal to native flow; only arc/wide-lock overlap downstream of full-width support cut',
            'repaired_pixels': int((repair > 0).sum()),
            'outside_repair_max_rgb_difference': int(np.abs(clean.astype(int)-rgb.astype(int))[repair == 0].max()),
            'prior': str(prior),
            'script': str(ROOT / 'tools/trace-cgc15-hair-redo.py')})
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    restored = Image.alpha_composite(Image.fromarray(clean).convert('RGBA'), overlay).convert('RGB')
    box = (950, 630, 1098, 698)
    panels = [image.crop(box), Image.fromarray(clean).crop(box), restored.crop(box)]
    panel = Image.new('RGB', (sum(i.width for i in panels), panels[0].height))
    for i, crop in enumerate(panels):
        panel.paste(crop, (i*crop.width, 0))
    panel.resize((panel.width*4, panel.height*4)).save(stage / 'arc-before-clean-restored.png')
    print(stage)


def directional_repair(texture, full_mask, foreground_id):
    """Interpolate across a crossing line along the underlying lock's flow.

    Find the nearest clean point on either side instead of copying a distant
    rectangle, which otherwise shifts or doubles the native highlight edges.
    """
    yy, xx = np.mgrid[:1080, :1920].astype(np.float32)
    if foreground_id.endswith('gold-flyaway'):
        slope = np.full_like(xx, 0.95)
    else:
        slope = np.clip(0.45+(xx-960)/150, 0.45, 1.5)
        # Authored native edge continuations at the two observed crossings:
        # (978,288) crosses the steep lower lock; (1025,256) crosses the much
        # shallower upper highlight. One global direction kinks both edges.
        for box, native_slope in [((959, 272, 993, 303), 1.10), ((1003, 237, 1044, 278), 0.48)]:
            x1, y1, x2, y2 = box
            edge_distance = np.minimum.reduce([xx-x1, x2-xx, yy-y1, y2-yy])
            amount = np.clip(edge_distance/4, 0, 1)
            slope = slope*(1-amount)+native_slope*amount
    vx = 1/np.sqrt(1+slope*slope)
    vy = slope*vx
    blocked = cv2.dilate(np.uint8(full_mask > 8)*255, np.ones((3, 3), np.uint8))
    distances = []
    samples = []
    for sign in (-1, 1):
        distance = np.zeros_like(xx)
        pending = blocked > 0
        for step in range(1, 28):
            test = cv2.remap(blocked, xx+sign*vx*step, yy+sign*vy*step, cv2.INTER_NEAREST)
            found = pending & (test == 0)
            distance[found] = step+0.75
            pending[found] = False
        distance[pending] = 28
        sample = cv2.remap(texture, xx+sign*vx*distance, yy+sign*vy*distance, cv2.INTER_CUBIC)
        distances.append(distance)
        samples.append(sample.astype(np.float32))
    a, b = distances
    amount = (a/np.maximum(a+b, 1))[:, :, None]
    return samples[0]*(1-amount)+samples[1]*amount


def protect_native_eye(image, moving_mask, helper):
    saved = json.loads((ROOT / 'godot/cg-puppet/eyes.json').read_text(encoding='utf-8'))
    eye = saved['CGC15_c']['eyes'][1]
    angle = math.radians(eye['angle'])
    axis = np.array([math.cos(angle), math.sin(angle)])
    normal = np.array([-axis[1], axis[0]])
    origin = np.array(eye['center'])
    def world(points):
        values = np.array(points)
        return origin+values[:, 0, None]*axis+values[:, 1, None]*normal
    eye_mask = Image.new('L', image.size)
    draw = ImageDraw.Draw(eye_mask)
    draw.polygon([tuple(v) for v in world(eye['upper']+list(reversed(eye['lower'])))], fill=255)
    lash_band = np.zeros((1080, 1920), np.uint8)
    cv2.polylines(lash_band, [np.round(world(eye['upper'])).astype(np.int32)], False, 255, 36)
    rgb = np.array(image.convert('RGB'))
    r, g, b = rgb.transpose(2, 0, 1)
    lash = (lash_band > 0) & (r < 160) & (g < 100) & (b < 105)
    mask = np.maximum(np.array(eye_mask), np.uint8(lash)*255)
    for path in [
        'M1090,412 C1094,408 1101,405 1104,407 C1110,411 1105,422 1098,428 C1093,433 1088,433 1086,428 C1083,423 1085,417 1090,412 Z',
        'M1168,338 C1174,331 1188,328 1194,334 C1200,341 1190,353 1178,357 C1169,361 1164,353 1168,338 Z'
    ]:
        mask = np.maximum(mask, np.array(helper.contour_mask(path)))
    # Never restore any source pixel belonging to the moving cluster.
    mask[np.array(moving_mask) > 6] = 0
    return np.uint8(mask > 6)*255


def main(stage=None, side_arc=False):
    definition = json.loads(DEFINITION.read_text(encoding='utf-8-sig'))
    spec = importlib.util.spec_from_file_location('hair_contours', ROOT / 'tools/prepare-layered-hair.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if side_arc:
        prepare_side_arc(definition, helper)
        return
    selected_ids = None
    if stage:
        selected_ids = set(json.loads((Path(stage) / 'stage.json').read_text(encoding='utf-8-sig'))['ids'])
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    OUT.mkdir(parents=True, exist_ok=True)
    for part in definition['front_to_back']:
        if not part.get('ready_for_extract'):
            continue
        if selected_ids is not None and part['id'] not in selected_ids:
            continue
        image = Image.open(Path(stage) / 'before.png' if stage else part.get('source', definition['source'])).convert('RGBA')
        mask = helper.part_mask(part)
        outlines = part.get('outlines', [part['outline']])
        mask.save(OUT / (part['id'] + '-mask.png'))
        native = image.copy()
        native.putalpha(mask)
        native.save(OUT / (part['id'] + '-native.png'))
        stationary_ids = set(part.get('stationary_foreground', []))
        stationary = [v for v in definition.get('stationary_foreground', []) if v['id'] in stationary_ids]
        if stationary:
            texture = np.array(image.convert('RGB'))
            clean = texture.astype(np.float32)
            coverage = np.array(mask)
            static_union = np.zeros_like(coverage)
            for foreground in stationary:
                full = np.array(helper.part_mask(foreground))
                overlap = np.minimum(full, coverage)
                static_union = np.maximum(static_union, full)
                foreground_image = image.copy()
                foreground_image.putalpha(Image.fromarray(overlap))
                foreground_image.save(OUT / (foreground['id'] + '.png'))
                replacement = directional_repair(texture, full, foreground['id'])
                removal = cv2.dilate(np.uint8(overlap > 8)*255, np.ones((3, 3), np.uint8))
                removal = np.array(Image.fromarray(removal).filter(ImageFilter.GaussianBlur(0.45)))
                weight = (removal.astype(np.float32)/255)[:, :, None]
                clean = clean*(1-weight)+replacement*weight
            clean_native = Image.fromarray(np.uint8(np.clip(clean, 0, 255))).convert('RGBA')
            clean_native.putalpha(mask)
            clean_native.save(OUT / (part['id'] + '-native-clean.png'))
            static_alpha = np.minimum(static_union, coverage)
            static_image = image.copy()
            static_image.putalpha(Image.fromarray(static_alpha))
            static_image.save(OUT / 'static-crossing-flyaways.png')
            Image.fromarray(static_alpha).save(OUT / 'static-crossing-flyaways-mask.png')
            if stage:
                stage = Path(stage)
                clean_native.save(stage / (part['id'] + '-native-clean.png'))
                static_image.save(stage / 'static-crossing-flyaways.png')
                Image.fromarray(static_alpha).save(stage / 'static-crossing-flyaways-mask.png')
                for foreground in stationary:
                    foreground_image = image.copy()
                    overlap = np.minimum(np.array(helper.part_mask(foreground)), coverage)
                    foreground_image.putalpha(Image.fromarray(overlap))
                    foreground_image.save(stage / (foreground['id'] + '.png'))
                record_file = stage / 'stage.json'
                record = json.loads(record_file.read_text(encoding='utf-8-sig'))
                record['texture_postprocess'] = {
                    'script': str(ROOT / 'tools/trace-cgc15-hair-redo.py'),
                    'command': 'C:/Python312/python.exe tools/trace-cgc15-hair-redo.py --stage "'+str(stage)+'"',
                    'method': 'native flow directed nearest boundary interpolation across two stationary crossing flyaways; all non-overlapping source texture unchanged',
                    'authored_edge_corrections': [
                        {'center': [978, 288], 'native_edge_slope': 1.10, 'region': [959, 272, 993, 303]},
                        {'center': [1025, 256], 'native_edge_slope': 0.48, 'region': [1003, 237, 1044, 278]}
                    ],
                    'stationary_definitions': stationary,
                    'moving_texture': str(stage / (part['id'] + '-native-clean.png')),
                    'static_foreground': str(stage / 'static-crossing-flyaways.png'),
                    'status': 'draft-awaiting-visual-inspection'
                }
                protect = protect_native_eye(image, mask, helper)
                Image.fromarray(protect).save(stage / 'native-right-eye-protection-mask.png')
                eye_overlay = image.copy()
                eye_overlay.putalpha(Image.fromarray(protect))
                eye_overlay.save(stage / 'native-right-eye-protection.png')
                plate_file = stage / 'repaired-plate.png'
                if plate_file.exists():
                    repaired = np.array(Image.open(plate_file).convert('RGB'))
                    before_protection = repaired.copy()
                    repaired[protect > 0] = texture[protect > 0]
                    protected_file = stage / 'repaired-plate-protected.png'
                    Image.fromarray(repaired).save(protected_file)
                    record['native_feature_protection'] = {
                        'plate': str(protected_file),
                        'mask': str(stage / 'native-right-eye-protection-mask.png'),
                        'definition': 'saved original right-eye interior plus source-thresholded upper lash ink and two traced natural tear footprints; every moving-cluster pixel excluded',
                        'restored_changed_pixels': int(np.any(before_protection[protect > 0] != texture[protect > 0], axis=1).sum()),
                        'protected_region_max_rgb_after_restore': int(np.abs(repaired[protect > 0].astype(int)-texture[protect > 0].astype(int)).max()),
                        'moving_source_pixels_restored': int(((protect > 0) & (coverage > 6)).sum())
                    }
                    # Isolated preview uses the cleaned native texture and exact
                    # static overlays, without changing production or raw stage files.
                    preview = stage / 'isolated-preview'
                    preview.mkdir(exist_ok=True)
                    Image.fromarray(repaired).save(preview / 'repaired-plate.png')
                    clean_native.save(preview / (part['id']+'-native.png'))
                    visible_area = np.maximum(coverage, np.array(Image.open(stage / 'composite-mask.png')))
                    preview_static = image.copy()
                    preview_static.putalpha(Image.fromarray(np.minimum(static_union, visible_area)))
                    preview_static.save(preview / 'static-crossing-flyaways.png')
                    preview_record = dict(record)
                    preview_record['static_overlays'] = ['static-crossing-flyaways.png']
                    (preview / 'stage.json').write_text(json.dumps(preview_record, ensure_ascii=False, indent=2), encoding='utf-8')
                    record['isolated_preview_stage'] = str(preview)
                record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        x1, y1, x2, y2 = mask.getbbox()
        box = (max(0, x1-25), max(0, y1-25), min(1920, x2+25), min(1080, y2+25))
        crop = native.crop(box)
        grey = Image.new('RGBA', crop.size, '#3a4552')
        check = Image.alpha_composite(grey, crop).convert('RGB')
        check.resize((check.width*5, check.height*5)).save(OUT / (part['id'] + '-check.png'))
        if stationary:
            clean_crop = clean_native.crop(box)
            clean_check = Image.alpha_composite(grey, clean_crop).convert('RGB')
            clean_check.resize((clean_check.width*4, clean_check.height*4)).save(OUT / 'loose-fringe-native-clean-check.png')
            panel = Image.new('RGB', (check.width*3, check.height), '#3a4552')
            panel.paste(check, (0, 0))
            panel.paste(clean_check, (check.width, 0))
            static_check = Image.alpha_composite(grey, static_image.crop(box)).convert('RGB')
            panel.paste(static_check, (check.width*2, 0))
            panel.resize((panel.width*3, panel.height*3)).save(OUT / 'loose-fringe-flyaway-separation-check.png')
        overlay = image.copy()
        draw = ImageDraw.Draw(overlay)
        edge = mask.filter(ImageFilter.FIND_EDGES)
        tint = Image.new('RGBA', image.size, '#21ffff')
        tint.putalpha(edge)
        overlay = Image.alpha_composite(overlay, tint)
        draw = ImageDraw.Draw(overlay)
        seam = [tuple(p) for p in part['fixed_root_seam']]
        draw.line(seam, fill='#ff321a', width=4)
        sx, sy = part['support_point']
        draw.ellipse((sx-4, sy-4, sx+4, sy+4), fill='#ff321a')
        draw.text((sx-90, sy-45), '固定支点 / 以下渐动', font=font, fill='#ff321a', stroke_width=2, stroke_fill='white')
        overlay.convert('RGB').save(OUT / (part['id'] + '-overlay.png'))
        print(part['id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', help='Write reproducible cleaned texture and static overlays into this stage')
    parser.add_argument('--prepare-side-arc', action='store_true', help='Separate narrow static side arc locally before extracting the full wide band')
    args = parser.parse_args()
    main(args.stage, args.prepare_side_arc)
