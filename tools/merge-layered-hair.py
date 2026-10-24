"""Combine spatially independent repair branches without overwriting another.

Each --branch is the final plate of an ordered local extraction sequence that
started at --base. Supply every native extraction stage with --layer, in
front-to-back order. Only changed pixels are carried from each repair branch.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def merge(base, branches, layers, out):
    original = np.array(Image.open(base/'repaired-plate.png').convert('RGB'))
    combined = original.copy()
    changed = np.zeros(original.shape[:2], dtype=bool)
    for branch in branches:
        plate = np.array(Image.open(branch/'repaired-plate.png').convert('RGB'))
        local = np.any(plate != original, axis=2)
        conflict = local & changed & np.any(plate != combined, axis=2)
        if conflict.any():
            raise ValueError(f'{branch}: {int(conflict.sum())} conflicting repair pixels; '
                             'continue overlapping layers in sequence instead')
        combined[local] = plate[local]
        changed |= local
    parts, overlays, seen = [], [], set()
    for stage in layers:
        record = read(stage/'stage.json')
        for item in record['parts']:
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            part = dict(item)
            texture = Path(part.get('native_texture', part['id']+'-native.png'))
            part['native_texture'] = str(texture if texture.is_absolute() else stage/texture)
            parts.append(part)
        for item in record.get('static_overlays', []):
            if isinstance(item, str):
                path = Path(item)
                overlay = str(path if path.is_absolute() else stage/path)
            else:
                overlay = dict(item)
                key = 'path' if 'path' in overlay else 'texture'
                path = Path(overlay[key])
                overlay[key] = str(path if path.is_absolute() else stage/path)
            if overlay not in overlays:
                overlays.append(overlay)
    record = read(base/'stage.json')
    record.update(parts=parts, static_overlays=overlays, removed_ids=[p['id'] for p in parts],
                  state='merged_native_layers_gpu_pending', base_stage=str(base),
                  repair_branches=[str(p) for p in branches],
                  native_stages=[str(p) for p in layers])
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(combined).save(out/'repaired-plate.png')
    Image.fromarray(np.uint8(changed)*255).save(out/'composite-mask.png')
    (out/'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n',
                                  encoding='utf-8')
    print(json.dumps({'stage': str(out), 'parts': [p['id'] for p in parts]}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--branch', type=Path, action='append', required=True)
    parser.add_argument('--layer', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    merge(args.base.resolve(), [p.resolve() for p in args.branch],
          [p.resolve() for p in args.layer], args.out.resolve())
