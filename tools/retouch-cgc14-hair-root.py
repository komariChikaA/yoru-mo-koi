"""Reconnect the short exposed lower-hair crossing after CGC14 F01 removal.

The generated plate moved a visible lower highlight and Poisson smeared colour
from the supported foreground edge. Retain the actual lower hair outside the
hole, sample its orange shading, and continue its two fine contours underneath
the foreground crossing. This touches only the authored small root region.
Run after prepare-layered-hair.py compose; production assets are not loaded.
"""
import argparse
import importlib.util
from pathlib import Path
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def main(stage):
    stage = Path(stage)
    spec = importlib.util.spec_from_file_location('layered_hair', ROOT/'tools/prepare-layered-hair.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    record = helper.load(stage/'stage.json')
    assert record['cg'] == 14 and record['ids'] == ['CGC14_F01_FREE_END']
    before = np.array(Image.open(stage/'before.png').convert('RGB'))
    composited = np.array(Image.open(stage/'composited-plate.png').convert('RGB'))
    part = np.array(Image.open(stage/'CGC14_F01_FREE_END-mask.png'))
    # Keep this tiny join independent of the long free section or the scalp.
    region_points = [(1577,480),(1605,480),(1630,510),(1620,564),
        (1568,564),(1570,535),(1574,515),(1575,497)]
    region_image = Image.new('L', (1920,1080))
    ImageDraw.Draw(region_image).polygon(region_points, fill=255)
    region = helper.clip_supported_side(np.array(region_image), record['parts'][0])
    hole = cv2.dilate(np.uint8(part > 6)*255, np.ones((7,7), np.uint8))
    # Clear the obsolete crossing shadow as well as the foreground silhouette.
    crossing = Image.new('L', (1920,1080))
    crossing_points = [(1575,495),(1600,505),(1596,516),(1586,530),
        (1575,545),(1568,549),(1568,530)]
    ImageDraw.Draw(crossing).polygon(crossing_points, fill=255)
    hole = np.maximum(hole, np.array(crossing))
    hole[region == 0] = 0
    samples = [(1592,523),(1598,522),(1604,520),(1610,515),(1590,534)]
    coordinates = np.array([[x-1590, y-520, 1] for x,y in samples])
    colours = np.array([before[y,x] for x,y in samples])
    coefficients = np.linalg.lstsq(coordinates, colours, rcond=None)[0]
    yy, xx = np.mgrid[:1080,:1920]
    colour_field = np.clip(np.stack([xx-1590,yy-520,np.ones_like(xx)],axis=-1)@coefficients,0,255)
    alpha = np.array(Image.fromarray(hole).filter(ImageFilter.GaussianBlur(.55)))/255
    alpha[hole == 0] = 0
    lower = np.uint8(np.clip(before*(1-alpha[...,None])+colour_field*alpha[...,None],0,255))
    contours = [
        [(1566,540),(1574,530),(1582,520),(1590,510)],
        [(1570,546),(1579,533),(1589,520),(1598,508)],
    ]
    ink = Image.new('RGBA', (1920*4,1080*4))
    draw = ImageDraw.Draw(ink)
    for contour in contours:
        a,b,c,d = np.array(contour, dtype=float)
        points = []
        for t in np.linspace(0,1,120):
            u = 1-t
            points.append(tuple(4*(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d)))
        draw.line(points, fill=(164,67,60,255), width=5)
    ink = ink.resize((1920,1080), Image.Resampling.LANCZOS)
    ink_alpha = np.array(ink.getchannel('A'))
    ink_alpha[hole == 0] = 0
    ink.putalpha(Image.fromarray(ink_alpha))
    lower = np.array(Image.alpha_composite(Image.fromarray(lower).convert('RGBA'), ink).convert('RGB'))
    alpha = np.array(Image.fromarray(region).filter(ImageFilter.GaussianBlur(.55)))/255
    alpha[region == 0] = 0
    repaired = np.uint8(np.clip(composited*(1-alpha[...,None])+lower*alpha[...,None],0,255))
    Image.fromarray(region).save(stage/'root-retouch-region.png')
    Image.fromarray(hole).save(stage/'root-retouch-hole.png')
    Image.fromarray(repaired).save(stage/'repaired-plate.png')
    composite_mask = np.maximum(np.array(Image.open(stage/'composite-mask.png')), region)
    Image.fromarray(composite_mask).save(stage/'composite-mask.png')
    record.update(state='retouched_awaiting_motion_review',
        root_retouch=dict(command='python -X utf8 tools/retouch-cgc14-hair-root.py --stage STAGE',
            region=region_points, crossing_shadow=crossing_points, colour_samples=samples,
            colour_coefficients=coefficients.tolist(), continued_lower_contours=contours,
            note='Original visible lower hair is restored; only hidden crossing shading and contour continuation are painted.'),
        outside_edit_max_rgb=int(np.abs(before.astype(int)-repaired.astype(int))[
            np.array(Image.open(stage/'allowed-edit.png')) == 0].max()),
        outside_composite_mask_max_rgb=int(np.abs(before.astype(int)-repaired.astype(int))[
            composite_mask == 0].max()))
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    helper.save_review(stage, record, before, repaired, np.array(Image.open(stage/'allowed-edit.png')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    main(parser.parse_args().stage)
