"""Keep the rebuilt hair plate; transplant only existing eye/mouth hidden paint."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'godot/chorus-four/assets'
STAGE = Path('../../工作文件夹/output/CGC14-15_scene4/'
             '头发逐层重拆/CGC14/stage-cliff-wind-v2')


def rgb(path):
    return np.array(Image.open(path).convert('RGB'))


def compose(stage=STAGE):
    original = rgb(ASSETS / 'CGC14_a.png')
    repaired = rgb(stage / 'repaired-plate.png')
    previous_clean = rgb(ASSETS / 'CGC14-native-clean.png')
    assert original.shape == repaired.shape == previous_clean.shape == (1080, 1920, 3)
    eye_edit = np.array(Image.open(ASSETS / 'CGC14-eyes/edit-region.png').convert('L')) > 0
    mouth_edit = np.zeros((1080, 1920), np.uint8)
    # Same footprint as compose-cgc14-cleanplates.py's existing native mouth repair.
    cv2.ellipse(mouth_edit, (1528, 366), (13, 8), 54, 0, 360, 255, -1)
    requested = eye_edit | (mouth_edit > 0)

    # The older eye mask crosses the rebuilt cheek/fringe. Preserve both the
    # newly revealed painting and the cluster's fixed native support pixels.
    repaired_hair = np.any(repaired != original, axis=2)
    native_hair = np.zeros((1080, 1920), bool)
    record = json.loads((stage / 'stage.json').read_text(encoding='utf-8-sig'))
    for part in record['parts']:
        path = Path(part.get('native_texture', part['id'] + '-native.png'))
        if not path.is_absolute():
            path = stage / path
        alpha = np.array(Image.open(path).convert('RGBA'))[:, :, 3]
        assert alpha.shape == native_hair.shape
        native_hair |= alpha > 0
    protected = repaired_hair | native_hair
    apply = requested & ~protected
    combined = repaired.copy()
    combined[apply] = previous_clean[apply]
    assert np.array_equal(combined[protected], repaired[protected])
    assert np.array_equal(combined[~requested], repaired[~requested])
    destination = ASSETS / 'CGC14-rebuilt-eye-clean.png'
    Image.fromarray(combined).save(destination)
    summary = dict(output=str(destination), base_stage=str(stage),
        eye_edit_bbox=Image.fromarray(eye_edit.astype(np.uint8)).getbbox(),
        requested_pixels=int(requested.sum()), copied_pixels=int(apply.sum()),
        protected_overlap_pixels=int((requested & protected).sum()),
        changed_pixels=int(np.any(combined != repaired, axis=2).sum()),
        rebuilt_hair_and_fixed_support='unchanged', outside_eye_and_mouth='unchanged')
    print(json.dumps(summary, ensure_ascii=False))
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, default=STAGE)
    compose(parser.parse_args().stage.resolve())
