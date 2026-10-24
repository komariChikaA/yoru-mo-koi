"""Prepare and compose one foreground removal at a time, from authored contours.

Image requests use the unmodified imagegen skill CLI separately. A subsequent
cutout must be extracted from the preceding repaired plate, not the original CG.
"""
from pathlib import Path
import argparse
import json
import re
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'godot/chorus-four'
OUT = Path('../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contour_mask(path):
    # Keep authored subpixel curves; the old helper rounds before supersampling.
    tokens = re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?', path)
    points, index, current = [], 0, None
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command in ('M', 'L'):
            current = np.array(tokens[index:index+2], dtype=float)
            index += 2
            points.append(current)
        elif command == 'C':
            values = np.array(tokens[index:index+6], dtype=float).reshape(3, 2)
            index += 6
            start = current
            for t in np.linspace(0, 1, 100)[1:]:
                points.append((1-t)**3*start+3*(1-t)**2*t*values[0]
                    +3*(1-t)*t*t*values[1]+t**3*values[2])
            current = values[2]
        elif command != 'Z':
            raise ValueError(command)
    canvas = Image.new('L', (3840, 2160))
    ImageDraw.Draw(canvas).polygon([tuple(p*2) for p in points], fill=255)
    return canvas.resize((1920, 1080), Image.Resampling.LANCZOS)


def part_mask(part):
    paths = part.get('outlines', [part['outline']])
    mask = np.maximum.reduce([np.array(contour_mask(path)) for path in paths])
    holes = part.get('exclude', [])
    if isinstance(holes, str):
        holes = [holes]
    for path in holes:
        mask = np.minimum(mask, 255-np.array(contour_mask(path)))
    return Image.fromarray(mask)


def clip_supported_side(mask, part):
    cut = part.get('fixed_transition', {}).get('cut_line', part.get('fixed_root_seam'))
    if cut:
        a, b = np.asarray(cut, dtype=float)
        normal = np.array([-(b-a)[1], (b-a)[0]])
        if np.dot(np.asarray(part['chain'][-1])-a, normal) < 0:
            normal = -normal
        yy, xx = np.mgrid[:mask.shape[0], :mask.shape[1]]
        mask[(xx-a[0])*normal[0]+(yy-a[1])*normal[1] < 0] = 0
    return mask


def prepare(cg, ids, prior, context_size=1024, variant=''):
    definition = load(PROJECT / f'hair-redo/CGC{cg}-traces.json')
    parts = [p for p in definition['front_to_back'] if p['id'] in ids]
    assert len(parts) == len(ids), 'Unknown or repeated layer identifier'
    history = []
    static_overlays = []
    if prior:
        prior_dir = Path(prior)
        record = load(prior_dir / 'stage.json')
        history = record['removed_ids']
        # These foreground strands were deliberately kept out of the lower
        # plate. Preserve them as independent overlays in each subsequent stage.
        for overlay in record.get('static_overlays', []):
            if isinstance(overlay, str):
                path = Path(overlay)
                static_overlays.append(str(path if path.is_absolute() else prior_dir/path))
            else:
                overlay = dict(overlay)
                key = 'path' if 'path' in overlay else 'texture'
                path = Path(overlay[key])
                overlay[key] = str(path if path.is_absolute() else prior_dir/path)
                static_overlays.append(overlay)
        source = prior_dir / 'repaired-plate.png'
    else:
        source = PROJECT / ('assets/CGC14_a.png' if cg == 14 else 'assets/CGC15_c.png')
    for part in parts:
        assert part.get('ready_for_extract', True) and part.get('status') != 'draft-rejected', (
            part['id'], 'Contour is still rejected or marked as analysis only')
        assert not part.get('prior_repaired_required') or prior, (
            part['id'], 'Extract this layer from the preceding repaired plate with --prior')
        assert not part.get('occluded_by') or set(part['occluded_by']).issubset(history), (
            part['id'], 'Remove and repair the occluding layer first', part['occluded_by'])
    stage = OUT / f'CGC{cg}' / ('stage-' + '-'.join(ids) + ('-'+variant if variant else ''))
    stage.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert('RGB')
    image.save(stage / 'before.png')
    masks = []
    for part in parts:
        mask = part_mask(part)
        mask.save(stage / f"{part['id']}-mask.png")
        cutout = image.convert('RGBA')
        cutout.putalpha(mask)
        cutout.save(stage / f"{part['id']}-native.png")
        masks.append(np.array(mask))
    # Dilation must not repaint the firmly supported section above the cut.
    # Clip each part separately before combining, so independent supports do
    # not incorrectly clip the other part's hidden surface.
    edit = np.zeros((1080, 1920), dtype=np.uint8)
    for part, mask in zip(parts, masks):
        local_edit = cv2.dilate(np.uint8(mask > 6)*255, np.ones((9, 9), np.uint8))
        if part.get('repair_outline'):
            local_edit = np.maximum(local_edit, np.array(contour_mask(part['repair_outline'])))
        edit = np.maximum(edit, clip_supported_side(local_edit, part))
    # Square input preserves original pixel scale; pad at image edges, never stretch.
    x, y, w, h = cv2.boundingRect(edit)
    if max(w, h) > 900:
        box = [0, 0, 1920, 1088]
        request_size = [1920, 1088]
    else:
        side = max(context_size, max(w, h)+48)
        side = min(1024, side)
        left = max(0, min(1920-side, x+w//2-side//2))
        top = max(0, min(1080-side, y+h//2-side//2))
        box = [left, top, left+side, top+side]
        request_size = [1024, 1024]
    # Masks have opaque protected pixels and transparent edit pixels.
    request = Image.new('RGB', (box[2]-box[0], box[3]-box[1]))
    request.paste(image.crop(tuple(box)), (0, 0))
    request = request.resize(tuple(request_size), Image.Resampling.LANCZOS)
    request.save(stage / 'edit-input.png')
    alpha = Image.fromarray(255-edit).crop(tuple(box)).resize(tuple(request_size), Image.Resampling.NEAREST)
    rgba = Image.new('RGBA', request.size, (255, 255, 255, 255))
    rgba.putalpha(alpha)
    rgba.save(stage / 'edit-mask.png')
    Image.fromarray(edit).save(stage / 'allowed-edit.png')
    descriptions = '; '.join(p['label'] + ': ' + p.get('notes', '') for p in parts)
    prompt = (
        'Use case: precise-object-edit. Make ONE static hidden layer for a 2D anime hair puppet. '
        'The provided image is the edit target, already with any previous foreground locks removed. '
        'Remove ONLY the foreground golden hair part(s) in the transparent mask: ' + descriptions + '. '
        'Continue the actual lower layers underneath: rebuild coherent uninterrupted golden hair locks '
        'with their own thin clean ink outlines, smooth shading and highlights wherever other hair is behind; '
        'rebuild the original pink clothing, skin or warm sunset background only where that material is behind. '
        'Do not replace a hair region with background when it belongs to a lower hair layer. '
        'Connect newly revealed hair through the removed occluder where another loose section needs '
        'to move; firmly supported upper hair remains static and does not need extraction to the scalp. '
        'No detached ends, surviving pieces of the removed foreground lock, '
        'smearing, blur, broad flat patches or replacement stray locks. '
        'Preserve ALL unmasked visible parts, exact character identity, face, eyes, pose, clothing, '
        'remaining hair, original coordinates, linework, light and composition. No text, labels or border. '
        'This is an ordered hidden-surface reconstruction, not a redesign or an animation frame.'
    )
    (stage / 'prompt.txt').write_text(prompt, encoding='utf-8')
    record = dict(cg=cg, input=str(source), ids=ids, removed_ids=history+ids, static_overlays=static_overlays,
        crop=box, request_size=request_size, parts=parts, state='awaiting_generated_hidden_plate',
        amplitude_reference=dict(old_multiplier=16, perceived_percent=100,
            note='Perceptual reference; retrace and re-rig before mapping displacement'))
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(stage, flush=True)


def compose(stage, generated, blend='alpha'):
    stage = Path(stage)
    record = load(stage / 'stage.json')
    before = np.array(Image.open(stage / 'before.png').convert('RGB'))
    edit = np.array(Image.open(stage / 'allowed-edit.png'))
    box = record['crop']
    target = np.array(Image.open(stage / 'edit-input.png').convert('RGB'))
    raw_actual = Image.open(generated).convert('RGB')
    actual = np.array(raw_actual.resize(
        (target.shape[1], target.shape[0]), Image.Resampling.LANCZOS))
    local_mask = np.array(Image.fromarray(edit).crop(tuple(box)).resize(
        (target.shape[1], target.shape[0]), Image.Resampling.NEAREST))
    detector = cv2.SIFT_create(nfeatures=5000)
    ka, da = detector.detectAndCompute(cv2.cvtColor(actual, cv2.COLOR_RGB2GRAY), None)
    kb, db = detector.detectAndCompute(cv2.cvtColor(target, cv2.COLOR_RGB2GRAY),
        255-cv2.dilate(local_mask, np.ones((21, 21), np.uint8)))
    good = [m for m, n in cv2.BFMatcher().knnMatch(da, db, k=2) if m.distance < .67*n.distance]
    assert len(good) >= 12, 'Not enough unchanged features to register the generated plate'
    matrix, inliers = cv2.estimateAffinePartial2D(
        np.float32([ka[m.queryIdx].pt for m in good]), np.float32([kb[m.trainIdx].pt for m in good]),
        method=cv2.RANSAC, ransacReprojThreshold=2.0)
    assert matrix is not None and int(inliers.sum()) >= 10, 'Generated plate registration failed'
    generated_full = before.copy()
    # Feature detection can use a normalized copy, but final pixels go from the
    # original API output straight to the native crop in one resampling pass.
    sx, sy = target.shape[1]/raw_actual.width, target.shape[0]/raw_actual.height
    raw_to_request = np.array([[sx, 0, (sx-1)/2], [0, sy, (sy-1)/2], [0, 0, 1]])
    sx, sy = (box[2]-box[0])/target.shape[1], (box[3]-box[1])/target.shape[0]
    request_to_native = np.array([[sx, 0, (sx-1)/2], [0, sy, (sy-1)/2], [0, 0, 1]])
    native_matrix = (request_to_native @ np.vstack([matrix, [0, 0, 1]]) @ raw_to_request)[:2]
    native_aligned = cv2.warpAffine(np.array(raw_actual), native_matrix,
        (box[2]-box[0], box[3]-box[1]), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    height = min(1080-box[1], native_aligned.shape[0])
    generated_full[box[1]:box[1]+height, box[0]:box[2]] = native_aligned[:height]
    Image.fromarray(generated_full).save(stage / 'generated-aligned.png')
    composite_mask = edit.copy()
    if blend == 'seam':
        # The generated collar line can shift locally even after registration.
        # Let the join move into nearby matching colour instead of cutting that
        # line at the narrow removal mask. The support's static side stays locked.
        outer = np.zeros_like(edit)
        for part in record['parts']:
            core = cv2.dilate(np.uint8(np.array(part_mask(part)) > 6)*255,
                np.ones((9, 9), np.uint8))
            if part.get('repair_outline'):
                core = np.maximum(core, np.array(contour_mask(part['repair_outline'])))
            core = clip_supported_side(core, part)
            candidate = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (57, 57)))
            outer = np.maximum(outer, clip_supported_side(candidate, part))
        finder = cv2.detail_GraphCutSeamFinder('COST_COLOR_GRAD')
        masks = finder.find([cv2.UMat(before.astype(np.float32)),
            cv2.UMat(generated_full.astype(np.float32))], [(0, 0), (0, 0)],
            [cv2.UMat(np.uint8(edit == 0)*255), cv2.UMat(outer)])
        composite_mask = masks[1].get()
        composite_mask[edit > 0] = 255
        composite_mask[outer == 0] = 0
    if blend in ('poisson', 'seam'):
        x, y, w, h = cv2.boundingRect(composite_mask)
        # OpenCV modifies its mask argument. Keep the authored support clip for
        # exterior restoration instead of allowing the filled bounding box.
        repaired = cv2.seamlessClone(generated_full, before, composite_mask.copy(),
            (x+w//2, y+h//2), cv2.NORMAL_CLONE)
        repaired[composite_mask == 0] = before[composite_mask == 0]
    else:
        alpha = np.array(Image.fromarray(edit).filter(ImageFilter.GaussianBlur(.65)))/255.0
        alpha[edit == 0] = 0
        repaired = np.uint8(np.clip(before*(1-alpha[..., None])+generated_full*alpha[..., None], 0, 255))
    Image.fromarray(composite_mask).save(stage / 'composite-mask.png')
    Image.fromarray(repaired).save(stage / 'composited-plate.png')
    Image.fromarray(repaired).save(stage / 'repaired-plate.png')
    record.update(state='painted_awaiting_visual_review', generated=str(Path(generated).resolve()), blend=blend,
        registration=dict(matches=len(good), inliers=int(inliers.sum()), affine=matrix.tolist(),
            raw_to_native_affine=native_matrix.tolist(), final_resampling_passes=1),
        outside_edit_max_rgb=int(np.abs(before.astype(int)-repaired.astype(int))[edit == 0].max()),
        outside_composite_mask_max_rgb=int(np.abs(before.astype(int)-repaired.astype(int))[
            composite_mask == 0].max()))
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    save_review(stage, record, before, repaired, edit)


def save_review(stage, record, before, repaired, edit):
    # Reassemble only for contour ownership; always inspect the exposed plate too.
    assembled = Image.fromarray(repaired).convert('RGBA')
    for part in reversed(record['parts']):
        assembled = Image.alpha_composite(assembled, Image.open(stage / f"{part['id']}-native.png"))
    assembled.convert('RGB').save(stage / 'reassembled.png')
    # Show the native cutout on grey, the removed view and the rebuilt hidden view at matching coordinates.
    x, y, w, h = cv2.boundingRect(edit)
    region = (max(0, x-30), max(0, y-30), min(1920, x+w+30), min(1080, y+h+30))
    panels = [Image.fromarray(before), Image.new('RGBA', (1920, 1080), '#455060'),
        Image.fromarray(repaired), assembled.convert('RGB')]
    for part in reversed(record['parts']):
        panels[1] = Image.alpha_composite(panels[1], Image.open(stage / f"{part['id']}-native.png"))
    sheet = Image.new('RGB', (1600, 1040), '#222831')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 25)
    for i, (panel, label) in enumerate(zip(panels, ['原图当前层', '本层原生透明部件', '移除后补绘下一层', '原位重组检查'])):
        thumb = panel.crop(region).convert('RGB')
        scale = min(780/thumb.width, 460/thumb.height)
        thumb = thumb.resize((round(thumb.width*scale), round(thumb.height*scale)), Image.Resampling.LANCZOS)
        px, py = (i % 2)*800, (i//2)*520
        sheet.paste(thumb, (px+(800-thumb.width)//2, py+50+(460-thumb.height)//2))
        draw.text((px+16, py+10), label, font=font, fill='white')
    sheet.save(stage / 'layer-review.jpg', quality=96)
    print(stage / 'layer-review.jpg', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--cg', type=int, choices=[14, 15], required=True)
    p.add_argument('--ids', nargs='+', required=True)
    p.add_argument('--prior')
    p.add_argument('--context-size', type=int, default=1024,
        help='Native crop size, enlarged to a 1024px request for small details')
    p.add_argument('--variant', default='', help='Keep corrected requests beside earlier attempts')
    p = sub.add_parser('compose')
    p.add_argument('--stage', required=True)
    p.add_argument('--generated', required=True)
    p.add_argument('--blend', choices=['alpha', 'poisson', 'seam'], default='alpha')
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.cg, args.ids, args.prior, args.context_size, args.variant)
    else:
        compose(args.stage, args.generated, args.blend)
