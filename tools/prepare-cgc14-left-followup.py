"""Prepare the ordered left hair follow-up without changing central definitions."""
import argparse
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC14-left-followup.json'
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


def reconnect_s(stage):
    """Keep the revealed rear ribbons connected across the S-shaped opening."""
    record = original_load(stage / 'stage.json')
    assert record['ids'] == ['CGC14_L01_S_FREE_END']
    before = np.array(Image.open(stage / 'before.png').convert('RGB'))
    aligned = np.array(Image.open(stage / 'generated-aligned.png').convert('RGB'))
    edit = np.array(Image.open(stage / 'allowed-edit.png'))
    mask = np.zeros_like(edit)
    cv2.fillConvexPoly(mask, cv2.convexHull(cv2.findNonZero(edit)), 255)
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35)))
    mask = layered.clip_supported_side(mask, record['parts'][0])
    x, y, w, h = cv2.boundingRect(mask)
    repaired = cv2.seamlessClone(aligned, before, mask.copy(),
        (x+w//2, y+h//2), cv2.NORMAL_CLONE)
    repaired[mask == 0] = before[mask == 0]
    Image.fromarray(mask).save(stage / 'composite-mask.png')
    Image.fromarray(repaired).save(stage / 'composited-plate.png')
    Image.fromarray(repaired).save(stage / 'repaired-plate.png')
    a, b = np.asarray(record['parts'][0]['fixed_transition']['cut_line'], dtype=float)
    normal = np.array([-(b-a)[1], (b-a)[0]])
    if np.dot(np.asarray(record['parts'][0]['chain'][-1])-a, normal) < 0:
        normal = -normal
    yy, xx = np.mgrid[:1080, :1920]
    upstream = (xx-a[0])*normal[0]+(yy-a[1])*normal[1] < 0
    delta = np.abs(before.astype(int)-repaired.astype(int))
    record.update(state='static_checked_gpu_pending', blend='connected-s-poisson',
        connected_surface='35px dilated convex support-side mask reconnects rear ribbons across the S opening',
        outside_edit_max_rgb=int(delta[edit == 0].max()),
        outside_composite_mask_max_rgb=int(delta[mask == 0].max()),
        upstream_max_rgb=int(delta[upstream].max()),
        visual_review='raw generated, complete S native, exposed rear ribbons and reassembly inspected; GPU pending parent')
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    layered.save_review(stage, record, before, repaired, edit)
    review(stage)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--id', required=True)
    p.add_argument('--prior', required=True)
    p.add_argument('--context-size', type=int, default=512)
    p.add_argument('--variant', default='left-followup-v1')
    p = sub.add_parser('compose')
    p.add_argument('--stage', required=True)
    p.add_argument('--generated', required=True)
    p.add_argument('--blend', choices=['alpha', 'poisson', 'seam'], default='seam')
    p = sub.add_parser('review')
    p.add_argument('--stage', required=True)
    p = sub.add_parser('reconnect-s')
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
    elif args.mode == 'reconnect-s':
        reconnect_s(Path(args.stage))
    else:
        review(Path(args.stage))


if __name__ == '__main__':
    main()
