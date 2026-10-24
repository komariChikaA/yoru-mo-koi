"""Assemble the reviewed cliff-wind revision from the existing local art stages.

This reuses saved native cutouts and hidden plates; it never requests image edits.
Run the right-followup native preparation and refinement before assembling CGC14.
"""
import argparse
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
STAGES = OUT / '头发逐层重拆'
PREVIEWS = STAGES / '悬崖强风增强-20261018'
POLICY = ROOT / 'godot/chorus-four/hair-redo/user-grouping.json'
RIGHT_ID = 'CGC14_RIGHT_LONG_U_LOOSE'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def prepare(cg):
    source = STAGES / f'CGC{cg}/stage-cliff-wind-v1'
    target = STAGES / f'CGC{cg}/stage-cliff-wind-v2'
    policy = read(POLICY)
    record = read(source / 'stage.json')
    for index, part in enumerate(record['parts']):
        part['motion_gain'] = policy['motion_gain_by_id'][part['id']]
        part['deformation_model'] = policy['deformation_by_id'][part['id']]
        part['bend_length_px'] = (330 if part['id'] == '15-R11-middle-swept-lock'
                                 else 320 if part['id'] == '15-R15-lower-long-tail'
                                 else 0)
        if cg == 14:
            # Preserve each original phase before inserting/sorting the new lock.
            part.setdefault('phase', 0.3 + index * 0.79)
    plate = source / 'repaired-plate.png'
    if cg == 14:
        right = STAGES / 'CGC14/right-middle-draft-20261018-support'
        repair = read(right / 'native-refine-record-v3.json')
        part = read(right / 'native-part-definition-v2.json')
        part.update(native_texture=repair['native'], motion_gain=policy['motion_gain_by_id'][RIGHT_ID],
                    deformation_model=policy['deformation_by_id'][RIGHT_ID],
                    bend_length_px=0, phase=3.05, ready_for_extract=True)
        part['notes'] = ('Only loose material below the fixed y550 cross-section; native outer loop '
                         'and U-return tips share one cluster. B10 crossing stays in front. '
                         'Hidden sunset and the deeper R01 connection use the saved native refinement.')
        record['parts'].append(part)
        record['parts'].sort(key=lambda item: item['depth'])
        record.setdefault('static_overlays', []).append(dict(
            path=str(right / 'static-B10-crossing-native.png'), draw_depth=10))
        plate = Path(repair['output'])
        record.update(right_long_u_stage=str(right), right_long_u_repair=repair)
    record.update(
        ids=[part['id'] for part in record['parts']],
        removed_ids=[part['id'] for part in record['parts']],
        base_stage=str(source), state='stronger-wind-v2-awaiting-user-visual-review',
        wind_policy=str(POLICY), wind_time_offset=policy['time_offset_by_cg'][str(cg)],
        full_preview=str(PREVIEWS / f'CGC{cg}-增强后.mp4'))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(plate, target / 'repaired-plate.png')
    (target / 'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n',
                                       encoding='utf-8')
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cg', type=int, choices=[14, 15])
    args = parser.parse_args()
    for number in ([args.cg] if args.cg else [14, 15]):
        prepare(number)
