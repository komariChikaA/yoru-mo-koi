"""Prepare the independently owned CGC15 follow-up stages.

Image generation remains a separate call to the unmodified bundled imagegen CLI.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC15-circled-followup.json'
spec = importlib.util.spec_from_file_location('layered_hair_prepare', ROOT / 'tools/prepare-layered-hair.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
original_load = base.load
original_part_mask = base.part_mask


def definition_load(path):
    if path.name == 'CGC15-traces.json':
        return original_load(DEFINITION)
    return original_load(path)


def exact_mask(part):
    if part.get('alpha_mask'):
        return Image.open(part['alpha_mask']).convert('L')
    return original_part_mask(part)


base.load = definition_load
base.part_mask = exact_mask


def prepare(ids, prior, variant):
    base.prepare(15, ids, prior, context_size=640, variant=variant)
    stage = base.OUT / 'CGC15' / ('stage-' + '-'.join(ids) + '-' + variant)
    record = original_load(stage / 'stage.json')
    edit = np.zeros((1080, 1920), np.uint8)
    for part in record['parts']:
        local = cv2.dilate(np.uint8(np.array(exact_mask(part)) > 6) * 255,
                           np.ones((17, 17), np.uint8))
        edit = np.maximum(edit, base.clip_supported_side(local, part))
    Image.fromarray(edit).save(stage / 'allowed-edit.png')
    alpha = Image.fromarray(255-edit).crop(tuple(record['crop'])).resize(
        tuple(record['request_size']), Image.Resampling.NEAREST)
    mask = Image.new('RGBA', alpha.size, (255, 255, 255, 255))
    mask.putalpha(alpha)
    mask.save(stage / 'edit-mask.png')
    record['definition'] = str(DEFINITION)
    record['core_mask_dilation_kernel_px'] = 17
    record['state'] = 'native-cutouts-prepared-awaiting-hidden-plate'
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return stage


def extend_tail(stage, height):
    """Keep cropped R15 ends outside the 1080px composition during strong wind."""
    stage = Path(stage)
    subprocess.run([sys.executable, str(ROOT / 'tools/extend-cgc15-r15-tail.py'),
                    '--stage', str(stage), '--height', str(height)], check=True,
                   stdout=subprocess.DEVNULL)
    evidence = original_load(stage / 'R15-extension.json')
    record = original_load(stage / 'stage.json')
    for part in record['parts']:
        if part['id'] == '15-R15-lower-long-tail':
            part['native_texture'] = evidence['image']
            part['native_mask'] = evidence['mask']
            part['texture_size'] = evidence['size']
            part['chain'] = evidence['suggested_chain']
            part['bend_length_px'] = 220
            part['deformation_model'] = 'supported-strip'
            part['off_canvas_extension'] = str(stage / 'R15-extension.json')
    (stage / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return evidence


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command', required=True)
    pp = sub.add_parser('prepare')
    pp.add_argument('--ids', nargs='+', required=True)
    pp.add_argument('--prior', required=True)
    pp.add_argument('--variant', default='circled-native-v1')
    cp = sub.add_parser('compose')
    cp.add_argument('--stage', required=True)
    cp.add_argument('--generated', required=True)
    cp.add_argument('--blend', choices=['alpha','poisson','seam'], default='seam')
    ep = sub.add_parser('extend-tail')
    ep.add_argument('--stage', required=True)
    ep.add_argument('--height', type=int, default=1600)
    a = ap.parse_args()
    if a.command == 'prepare':
        prepare(a.ids, a.prior, a.variant)
    elif a.command == 'extend-tail':
        extend_tail(a.stage, a.height)
    else:
        base.compose(a.stage, a.generated, a.blend)
