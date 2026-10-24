"""Isolated prepared contour for the long right U lock and its own free tips.

Never writes production stages, shared traces, or runtime definitions.
"""
from pathlib import Path
import importlib.util
import json
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / 'godot/chorus-four/hair-redo/CGC14-right-followup.json'
spec = importlib.util.spec_from_file_location('layered_hair', ROOT / 'tools/prepare-layered-hair.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def main():
    record = json.loads(DEFINITION.read_text(encoding='utf-8'))
    out = Path(record['output']); out.mkdir(parents=True, exist_ok=True)
    prior = Path(record['prior'])
    stage = json.loads((prior / 'stage.json').read_text(encoding='utf-8'))
    base = Image.open(prior / 'repaired-plate.png').convert('RGB')
    native_b10 = Image.new('RGBA', base.size)
    if record['replaces']:
        b10 = next(p for p in stage['parts'] if p['id'] == record['replaces'][0])
        native_b10 = Image.open(b10['native_texture']).convert('RGBA')
    source = base.convert('RGBA'); source.alpha_composite(native_b10)
    part = record['part']
    part.setdefault('outline', part['outlines'][0])
    new_mask = helper.clip_supported_side(np.array(helper.part_mask(part)), part)
    b10_overlay_alpha = np.array(helper.contour_mask(record['b10_static_overlay_outline']))
    # The stable foreground stays above the new U lock. Continue only its
    # hidden fine ink, using native ink colour; visible pixels remain untouched.
    hidden_join = np.minimum(np.array(helper.contour_mask(record['hidden_fine_join'])),
                             b10_overlay_alpha)
    hidden_join[new_mask > 6] = 0
    rgba = np.array(source)
    native_ink = np.array(base)[843, 1460]
    rgba[hidden_join > 0, :3] = native_ink
    source = Image.fromarray(rgba)
    new_mask = np.maximum(new_mask, hidden_join)
    # Supersampled intersecting contours can leave isolated subpixel flecks.
    # Remove only tiny disconnected alpha islands, never an attached fine tip.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(np.uint8(new_mask > 8), 8)
    for component in range(1, n):
        if stats[component, cv2.CC_STAT_AREA] < 4:
            new_mask[labels == component] = 0
    native_mask = np.maximum(new_mask, np.array(native_b10.getchannel('A')))
    cutout = source.copy(); cutout.putalpha(Image.fromarray(native_mask))
    if '--native-only' in sys.argv:
        # Refresh the authored native contour without replacing the generated
        # stage record, hidden plate, or its API alignment evidence.
        cutout.save(out / f'{part["id"]}-native-v2.png')
        Image.fromarray(native_mask).save(out / f'{part["id"]}-mask-v2.png')
        (out / 'native-part-definition-v2.json').write_text(
            json.dumps(part, ensure_ascii=False, indent=2), encoding='utf-8')
        print(out / f'{part["id"]}-native-v2.png')
        return
    cutout.save(out / 'right-long-u-native-draft.png')
    Image.fromarray(native_mask).save(out / 'right-long-u-mask-draft.png')
    cutout.save(out / f'{part["id"]}-native.png')
    Image.fromarray(native_mask).save(out / f'{part["id"]}-mask.png')
    stable = base.convert('RGBA'); stable.putalpha(Image.fromarray(b10_overlay_alpha))
    stable.save(out / 'static-B10-crossing-native.png')
    # Existing B10 hidden paint is already present in the final prior.
    edit = cv2.dilate(np.uint8(new_mask > 6) * 255, np.ones((9, 9), np.uint8))
    edit = helper.clip_supported_side(edit, part)
    protected_b10 = cv2.dilate(np.uint8(np.array(native_b10.getchannel('A')) > 6) * 255,
                              np.ones((9, 9), np.uint8))
    edit[protected_b10 > 0] = 0
    protected_crossing = cv2.dilate(np.uint8(b10_overlay_alpha > 6)*255,
                                   np.ones((5, 5), np.uint8))
    edit[protected_crossing > 0] = 0
    Image.fromarray(edit).save(out / 'new-hidden-edit-only.png')
    Image.fromarray(edit).save(out / 'allowed-edit.png')
    base.save(out / 'prior-final-plate.png')
    base.save(out / 'before.png')
    box = [896, 56, 1920, 1080]
    base.crop(tuple(box)).save(out / 'edit-input.png')
    api_mask = Image.new('RGBA', (1024, 1024), 'white')
    api_mask.putalpha(Image.fromarray(255-edit).crop(tuple(box)))
    api_mask.save(out / 'edit-mask.png')
    removed = np.array(base).copy(); removed[edit > 0] = (105, 110, 117)
    Image.fromarray(removed).save(out / 'hidden-area-needed-draft.png')
    # Whole image context plus a close contour view, with support and existing tip.
    original = Image.open(record['original']).convert('RGBA')
    tint = Image.new('RGBA', original.size, (30, 210, 255, 0))
    tint.putalpha(Image.fromarray(np.uint8(native_mask.astype(float) * .32)))
    overlay = Image.alpha_composite(original, tint)
    d = ImageDraw.Draw(overlay)
    contours, _ = cv2.findContours(np.uint8(native_mask > 90), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        pts = [tuple(map(int, p)) for p in contour[:, 0]]
        if len(pts) > 2: d.line(pts + pts[:1], fill='#22e5ff', width=2)
    a, b = part['fixed_transition']['cut_line']
    d.line([tuple(a), tuple(b)], fill='#ffdb24', width=5)
    cx, cy = part['support_point']; d.ellipse((cx-7, cy-7, cx+7, cy+7), fill='#ffdb24')
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 24)
    d.text((1290, 490), '固定横截面；上游保持静态', font=font, fill='#ffdb24', stroke_width=2, stroke_fill='#243039')
    d.text((1320, 972), 'U簇自身自由尾；B10前层排除', font=font, fill='#22e5ff', stroke_width=2, stroke_fill='#243039')
    overlay.convert('RGB').save(out / 'selection-full-draft.png')
    crop = (1060, 480, 1815, 990)
    grey = Image.new('RGBA', original.size, '#686d74'); grey.alpha_composite(cutout)
    top = 44; w, h = 1133, 765
    sheet = Image.new('RGB', (w*2, h+top), '#202831'); sd = ImageDraw.Draw(sheet)
    sheet.paste(overlay.convert('RGB').crop(crop).resize((w,h)), (0,top))
    sheet.paste(grey.convert('RGB').crop(crop).resize((w,h)), (w,top))
    sd.text((12,8), '独立草案：整簇选区与固定支点（不是最终轮廓验收）', font=font, fill='white')
    sd.text((w+12,8), '最终prior原生可见像素；前层遮住的部分尚未补全', font=font, fill='white')
    sheet.save(out / 'selection-and-native-draft.png')
    edge_crop = (1350, 535, 1785, 970)
    edge_sheet = Image.new('RGB', (1305*2, 1305+top), '#202831')
    edge_sheet.paste(overlay.convert('RGB').crop(edge_crop).resize((1305,1305)), (0,top))
    edge_sheet.paste(grey.convert('RGB').crop(edge_crop).resize((1305,1305)), (1305,top))
    ed = ImageDraw.Draw(edge_sheet)
    ed.text((12,8), '最终API前边界检查：青色=单簇，黄色=完整固定横截面', font=font, fill='white')
    ed.text((1317,8), '原生灰底；仅B10下方隐藏微线补接，非可见像素重绘', font=font, fill='white')
    edge_sheet.save(out / 'native-edge-check.png')
    record['native_texture'] = str(out / 'right-long-u-native-draft.png')
    record['notes'] += ['仅生成选区草案与真实原生 cutout，尚未隐藏面补绘、GPU形变或视觉验收。']
    (out / 'draft-record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    overlays = list(stage.get('static_overlays', []))
    overlays.append(dict(path=str(out/'static-B10-crossing-native.png'), draw_depth=10))
    part['native_texture'] = str(out/f'{part["id"]}-native.png')
    part['ready_for_extract'] = True
    prepared = dict(cg=14, input=str(prior/'repaired-plate.png'),
        base_stage=str(prior), ids=[part['id']], parts=[part],
        removed_ids=list(stage['removed_ids'])+[part['id']], static_overlays=overlays,
        crop=box, request_size=[1024,1024], state='awaiting_generated_hidden_plate',
        native_visible_pixels='source prior unchanged',
        hidden_join_pixels=int(np.count_nonzero(hidden_join)),
        static_foreground='B10 crossing overlay depth10 above U depth20; existing B10 moving tip stays independent',
        edit_protects_b10=True,
        notes='Independent prepared stage only. No shared production changes or GPU acceptance.')
    (out/'stage.json').write_text(json.dumps(prepared,ensure_ascii=False,indent=2),encoding='utf-8')
    prompt = '''Use case: precise-object-edit. Make ONE static hidden plate for an anime hair puppet.
The input is the FINAL previously repaired production plate. Remove ONLY the single loose right-hand U-shaped hair cluster within the transparent mask: its lower vertical section beginning at the authored support cross-section at native y=550, its complete lower U bend, its own tapered loose tips, and its same-cluster fine loop. Do not follow the hair upward to the scalp.
Continue the actual surfaces behind the removed hair: the warm textured pink-orange sunset background where no hair is behind, and the already visible deeper brown/golden vertical hair strand wherever it passes behind the U bend. Keep that deeper strand's existing direction, shading and thin outlines continuous. Preserve existing prior repairs; do not invent extra locks or replace a deeper hair strand with background.
The opaque protected B10 white-golden crossing strip is a separate static foreground. Preserve it exactly, including its position, visible pixels and boundaries; it must not be removed or redesigned. Its existing independent free tip is already removed in this input and must stay removed. The lower independent R01 tip is already removed as well; preserve that existing hidden background.
Firm hair above native y=550 is protected and static. Preserve ALL unmasked pixels: face, eyes, skin, mouth, clothes, stable hair, other repaired areas, coordinates, native linework and composition. No animation frames, expression edits, camera changes, added strands, text or border. This is only a static hidden surface reconstruction.'''
    (out/'prompt.txt').write_text(prompt,encoding='utf-8')
    checks = dict(native_visible_rgb_max_difference=int(np.max(np.abs(
        np.array(cutout)[:,:,:3].astype(int)[(native_mask>6)&(hidden_join==0)]-
        np.array(base).astype(int)[(native_mask>6)&(hidden_join==0)]))),
        hidden_join_pixels=int(np.count_nonzero(hidden_join)),
        edit_overlap_protected_b10=int(np.count_nonzero((edit>0)&(protected_crossing>0))),
        edit_above_root=int(np.count_nonzero(edit[:550])),
        scalp_or_firm_upstream_selected=int(np.count_nonzero(native_mask[:550])))
    (out/'native-preparation-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(out / 'selection-and-native-draft.png')


if __name__ == '__main__':
    main()
