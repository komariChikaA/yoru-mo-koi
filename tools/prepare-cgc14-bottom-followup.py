"""Prepare the sleeve-front loose tips without changing central definitions."""
import argparse
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC14-bottom-followup.json'
spec = importlib.util.spec_from_file_location('layered_hair', ROOT / 'tools/prepare-layered-hair.py')
layered = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layered)
original_load = layered.load


def load_definition(path):
    if path == layered.PROJECT / 'hair-redo/CGC14-traces.json':
        return original_load(DEFINITION)
    return original_load(path)


layered.load = load_definition


def review(stage):
    record = original_load(stage / 'stage.json')
    source = Image.open(stage / 'before.png').convert('RGB')
    for part in record['parts']:
        mask = Image.open(stage / (part['id'] + '-mask.png')).convert('L')
        native = Image.open(stage / (part['id'] + '-native.png')).convert('RGBA')
        box = mask.getbbox()
        box = (max(0, box[0]-16), max(0, box[1]-16), min(1920, box[2]+16), min(1080, box[3]+16))
        w, h = box[2]-box[0], box[3]-box[1]
        checker = Image.new('RGBA', (w, h), '#555b65')
        draw = ImageDraw.Draw(checker)
        for y in range(0, h, 12):
            for x in range(0, w, 12):
                if (x//12+y//12)%2:
                    draw.rectangle((x, y, x+11, y+11), fill='#737b85')
        checker.alpha_composite(native.crop(box))
        checker.convert('RGB').resize((w*4, h*4), Image.Resampling.LANCZOS).save(stage / (part['id']+'-check-4x.png'))
        boundary = source.crop(box).resize((w*4, h*4), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(boundary)
        contours, _ = cv2.findContours(np.uint8(np.array(mask)>127), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            points = [((int(p[0][0])-box[0])*4, (int(p[0][1])-box[1])*4) for p in contour]
            if len(points)>1:
                draw.line(points+[points[0]], fill='#00e6ff', width=1)
        cut = part['fixed_transition']['cut_line']
        draw.line([((p[0]-box[0])*4, (p[1]-box[1])*4) for p in cut], fill='#ff5030', width=4)
        px, py = part['support_point']
        px, py = (px-box[0])*4, (py-box[1])*4
        draw.ellipse((px-10, py-10, px+10, py+10), outline='#ff5030', width=3)
        boundary.save(stage / (part['id']+'-boundary-4x.png'))
    return record


def repair_native(stage):
    """Continue the smooth pink sleeve from its own nearby native colours.

    This free tip stays entirely in front of the sleeve. The failed broad
    hidden-plate request is not retried; no rear-hair texture is invented here.
    """
    record = original_load(stage/'stage.json')
    before = np.array(Image.open(stage/'before.png').convert('RGB')).astype(float)
    edit = np.array(Image.open(stage/'allowed-edit.png'))
    shadow = cv2.warpAffine(edit, np.float32([[1, 0, 4], [0, 1, 9]]), (1920, 1080))
    mask = cv2.dilate(np.maximum(edit, shadow),
                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    yy, xx = np.mgrid[:1080, :1920]
    mask[(xx < 1165) & (yy < 839)] = 0
    r, g, b = before.transpose(2, 0, 1)
    known = ((xx > 1070) & (xx < 1220) & (yy > 850) & (yy < 1000)
             & (r-g > 85) & (r > 245) & (b > 125) & (b < 185) & (mask == 0))
    x, y = (xx-1150)/120, (yy-910)/100
    terms = np.stack([np.ones(x.shape), x, y, x*x, x*y, y*y], axis=-1)
    matrix, colours = terms[known], before[known]
    keep = np.ones(len(colours), dtype=bool)
    for unused in range(5):
        coefficients = np.linalg.lstsq(matrix[keep], colours[keep], rcond=None)[0]
        residual = np.linalg.norm(matrix@coefficients-colours, axis=1)
        keep = residual < np.percentile(residual, 75)
    field = np.clip(terms@coefficients, 0, 255)
    from PIL import ImageFilter
    alpha = np.array(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(2)))/255.0
    alpha[mask > 127] = 1
    # Fade on the authored seam's downstream normal; the whole seam stays exact.
    part = record['parts'][0]
    line = np.array(part['fixed_transition']['cut_line'], dtype=float)
    normal = np.array([-(line[1]-line[0])[1], (line[1]-line[0])[0]])
    normal /= np.linalg.norm(normal)
    if np.dot(np.array(part['chain'][-1])-line[0], normal) < 0:
        normal = -normal
    distance = (xx-line[0, 0])*normal[0]+(yy-line[0, 1])*normal[1]
    release = np.clip(distance/24.0, 0, 1)
    alpha *= release*release*(3-2*release)
    repaired = np.uint8(np.clip(before*(1-alpha[..., None])+field*alpha[..., None], 0, 255))
    composite = np.uint8(alpha > 0)*255
    repaired[composite == 0] = np.uint8(before[composite == 0])
    Image.fromarray(repaired).save(stage/'repaired-plate.png')
    Image.fromarray(repaired).save(stage/'composited-plate.png')
    Image.fromarray(composite).save(stage/'composite-mask.png')
    record.update(state='native_material_repair_gpu_pending',
                  repair_method='native sleeve shading fit; narrow silhouette and cast-shadow cleanup; 24px seam release',
                  outside_composite_mask_max_rgb=0)
    (stage/'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    layered.save_review(stage, record, np.uint8(before), repaired, composite)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--id', required=True)
    p.add_argument('--prior', required=True)
    p.add_argument('--context-size', type=int, default=512)
    p.add_argument('--variant', default='bottom-followup-v1')
    p = sub.add_parser('compose')
    p.add_argument('--stage', required=True)
    p.add_argument('--generated', required=True)
    p.add_argument('--blend', choices=['alpha', 'poisson', 'seam'], default='seam')
    p = sub.add_parser('review')
    p.add_argument('--stage', required=True)
    p = sub.add_parser('repair-native')
    p.add_argument('--stage', required=True)
    args = parser.parse_args()
    if args.mode == 'prepare':
        layered.prepare(14, [args.id], args.prior, args.context_size, args.variant)
        stage = layered.OUT / 'CGC14' / ('stage-'+args.id+('-'+args.variant if args.variant else ''))
        review(stage)
        record = original_load(stage/'stage.json')
        record['definition_file'] = str(DEFINITION)
        (stage/'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    elif args.mode == 'compose':
        stage = Path(args.stage)
        layered.compose(stage, args.generated, args.blend)
        review(stage)
    elif args.mode == 'repair-native':
        repair_native(Path(args.stage))
    else:
        review(Path(args.stage))


if __name__ == '__main__':
    main()
