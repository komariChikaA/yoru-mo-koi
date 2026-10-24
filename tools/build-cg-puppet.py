"""Build local CG puppet controls. Original game pictures stay out of Git.

This pilot uses weighted local image deformation, not a fully separated rig.
Edit godot/cg-puppet/rigs.json, then rerun to update influence masks.
"""
import argparse
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
from PIL import Image, ImageDraw

WORKSPACE = Path(__file__).resolve().parents[1]
PROJECT = WORKSPACE / "godot" / "cg-puppet"
DEFAULT_SOURCE = Path("${GAME_ROOT}/解包/CG")
SIZE = (1920, 1080)


def pin(name, center, radius, move, angle=0, phase=0, polygon=None, pivot=None, frequency=1):
    return dict(name=name, center=center, radius=radius, move=move, angle=angle,
                phase=phase, polygon=polygon, pivot=pivot or center, frequency=frequency)


def default_rigs():
    rigs = {
        "CGC14": {
            "pins": [
                pin("head", [1660, 245], [315, 280], [1.4, 1], .16,
                    polygon=[[1470,55],[1760,20],[1890,105],[1880,350],[1690,450],[1435,385]], pivot=[1565,435]),
                pin("upper_hair", [1020, 160], [470, 195], [-1.2, 7], phase=.5,
                    polygon=[[645,65],[1150,15],[1465,65],[1500,195],[1290,280],[750,340],[620,240]]),
                pin("middle_hair", [1010, 303], [380, 130], [-2, 5], phase=.9,
                    polygon=[[660,230],[1080,160],[1475,230],[1365,307],[1150,335],[920,345],[815,390],[660,320]]),
                pin("right_hair", [1732, 625], [140, 340], [6, 2], phase=.65,
                    polygon=[[1830,335],[1780,480],[1790,635],[1740,850],[1625,910],[1540,885],[1670,735],[1710,520]]),
                pin("lower_hair", [1335, 925], [310, 110], [-2, 7], phase=1.1,
                    polygon=[[1060,925],[1160,852],[1535,835],[1750,860],[1670,970],[1500,1025],[1140,1030]]),
                pin("brow_left", [1570, 184], [58, 21], [.2, -1.5], phase=.2),
                pin("brow_right", [1710, 291], [54, 20], [.2, -1.5], phase=.2),
                pin("hand", [1370, 398], [90, 75], [1.2, -2.4], .32, .35,
                    polygon=[[1280,360],[1370,340],[1450,364],[1455,407],[1390,448],[1300,435]], pivot=[1270,420]),
                pin("sleeve", [1190, 402], [220, 107], [1.0, -1.8], .12, .35,
                    polygon=[[1020,340],[1220,300],[1330,342],[1335,447],[1120,470],[960,436]], pivot=[1040,400]),
                pin("clothing", [1260, 550], [255, 160], [-.5, 1.5], phase=0, frequency=2,
                    polygon=[[1065,425],[1420,433],[1480,525],[1310,720],[1060,647],[995,552]]),
                pin("pendant", [937, 620], [78, 85], [2.5, .8], .45, .8, pivot=[1120,530]),
                pin("cuff", [930, 783], [145, 155], [1, 1.3], phase=.4,
                    polygon=[[880,705],[1030,735],[1075,790],[995,916],[890,896],[815,815]]),
            ],
        },
        "CGC15_c": {
            "pins": [
                pin("head", [1015, 462], [365, 300], [1.2, 1.3], .12,
                    polygon=[[668,268],[790,174],[1115,189],[1240,344],[1330,592],[1255,696],[1140,754],[902,674],[730,548]], pivot=[1250,700]),
                pin("right_hair", [1500, 215], [350, 125], [2, 6], phase=.5,
                    polygon=[[1180,135],[1420,80],[1660,120],[1770,195],[1750,330],[1870,448],[1740,360],[1680,263],[1390,306],[1210,254]]),
                pin("hair_tips", [1690, 335], [190, 155], [5, 3], phase=.95,
                    polygon=[[1460,205],[1730,165],[1820,282],[1800,350],[1900,460],[1770,427],[1710,320],[1540,335]]),
                pin("left_hair", [765, 906], [150, 170], [5, 1], phase=.8,
                    polygon=[[622,738],[750,720],[800,855],[876,960],[838,1040],[738,1060],[656,1000],[641,840]]),
                pin("front_hair", [1043, 855], [150, 205], [3, 2.5], phase=.45,
                    polygon=[[875,695],[970,676],[1100,781],[1215,1080],[1020,1080],[1010,923],[930,810]]),
                pin("brow_left", [894, 423], [68, 25], [-.4, -1.6], phase=.2),
                pin("brow_right", [1054, 261], [66, 24], [-.4, -1.6], phase=.2),
                pin("reaching_hand", [160, 550], [295, 240], [3, -3], .32, .25,
                    polygon=[[0,328],[130,371],[234,419],[315,492],[365,578],[326,652],[239,735],[127,757],[63,700],[0,595]], pivot=[363,622]),
                pin("reaching_sleeve", [510, 631], [360, 167], [1.5, -2.5], .16, .25,
                    polygon=[[292,496],[402,478],[672,541],[826,631],[873,748],[657,787],[431,744],[305,675]], pivot=[845,696]),
                pin("shoulder", [1410, 471], [235, 167], [-.6, 1.3], phase=0, frequency=2,
                    polygon=[[1240,327],[1392,309],[1645,421],[1610,528],[1482,600],[1300,528]]),
                pin("necklace", [1426, 787], [68, 88], [2.3, 1], .35, .65, pivot=[1400,696]),
                pin("back_hand", [1640, 471], [69, 80], [1.8, 1], .3, .55,
                    polygon=[[1595,420],[1632,398],[1700,459],[1685,531],[1648,514],[1595,485]]),
            ],
        },
        "CGC16": {
            "pins": [
                pin("head", [858, 221], [232, 242], [1.3, .9], .15,
                    polygon=[[680,31],[908,6],[1057,86],[1093,259],[1030,360],[959,428],[790,427],[665,276]], pivot=[965,407]),
                pin("right_hair", [1274, 501], [195, 240], [5, 2.5], phase=.65,
                    polygon=[[1090,268],[1305,289],[1380,374],[1430,495],[1477,585],[1422,705],[1370,728],[1294,558],[1180,514]]),
                pin("upper_hair", [1167, 253], [198, 107], [2, 4], phase=.35,
                    polygon=[[1021,96],[1125,149],[1264,236],[1350,289],[1350,343],[1215,305],[1090,246]]),
                pin("left_hair", [674, 512], [116, 174], [-4, 2.5], phase=.5,
                    polygon=[[654,346],[736,370],[795,445],[747,541],[698,598],[595,621],[590,485]]),
                pin("lower_hair", [711, 853], [134, 200], [-3, 4], phase=.9,
                    polygon=[[615,708],[712,707],[802,823],[820,962],[750,1060],[700,966],[662,928],[608,816]]),
                pin("brow_left", [791, 227], [45, 20], [.2, -1.1], phase=.1),
                pin("brow_right", [916, 166], [59, 20], [.2, -1.1], phase=.1),
                pin("open_hand", [573, 658], [128, 78], [2.0, -3.2], .55, .3,
                    polygon=[[475,617],[539,597],[575,592],[623,621],[665,639],[697,680],[640,716],[568,701],[504,665]], pivot=[675,702]),
                pin("forearm", [758, 780], [140, 145], [1.2, -1.8], .18, .3,
                    polygon=[[676,660],[744,663],[830,734],[880,821],[815,888],[742,843],[685,775],[629,733]], pivot=[839,842]),
                pin("uniform", [1114, 714], [195, 211], [.6, 1.1], phase=0, frequency=2,
                    polygon=[[975,530],[1221,507],[1282,613],[1270,846],[1155,926],[960,839],[958,665]]),
                pin("ribbon", [1007, 442], [110, 77], [1.5, 1], .45, .6, pivot=[1000,430]),
                pin("right_cuff", [1367, 860], [112, 138], [1.2, .8], phase=.4,
                    polygon=[[1305,747],[1380,771],[1450,929],[1349,1005],[1295,870]]),
            ],
        },
    }
    return rigs


def influence(control, xx, yy):
    cx, cy = control["center"]
    rx, ry = control["radius"]
    distance = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    u = np.clip((distance - 0.12) / 0.88, 0, 1)
    weight = 1 - u * u * (3 - 2 * u)
    if control.get("polygon"):
        shape = np.zeros((SIZE[1], SIZE[0]), np.uint8)
        cv2.fillPoly(shape, [np.array(control["polygon"], np.int32)], 255)
        # Blur inside the shape only: no influence leaks outside the selected part.
        edge_distance = cv2.distanceTransform(shape, cv2.DIST_L2, 5)
        feather = np.clip(edge_distance / 12, 0, 1)
        feather = feather * feather * (3 - 2 * feather)
        weight *= feather
    return np.uint8(np.round(weight * 255))


def build(source):
    assets = PROJECT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    rig_path = PROJECT / "rigs.json"
    if not rig_path.exists():
        rig_path.write_text(json.dumps(default_rigs(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rigs = json.loads(rig_path.read_text(encoding="utf-8"))
    names = ["CGC14_a", "CGC14_b", "CGC14_c", "CGC15_c", "CGC16"]
    for name in names:
        path = source / (name + ".png")
        with Image.open(path) as image:
            if image.size != SIZE:
                raise ValueError(f"Expected {SIZE}, got {image.size}: {path}")
        shutil.copyfile(path, assets / path.name)
    yy, xx = np.mgrid[:SIZE[1], :SIZE[0]].astype(np.float32)
    previews = WORKSPACE / "_preview" / "cg-puppet"
    previews.mkdir(parents=True, exist_ok=True)
    for family, rig in rigs.items():
        directory = assets / family
        directory.mkdir(exist_ok=True)
        weights = [influence(control, xx, yy) for control in rig["pins"]]
        if len(weights) != 12:
            raise ValueError("Each pilot rig has exactly 12 editable control slots")
        for atlas in range(4):
            Image.fromarray(np.stack(weights[atlas * 3:atlas * 3 + 3], axis=-1)).save(directory / f"weights{atlas}.png")
        base_name = "CGC14_a" if family == "CGC14" else family
        base = np.array(Image.open(assets / (base_name + ".png")).convert("RGB"))
        overview = Image.fromarray(base)
        draw = ImageDraw.Draw(overview)
        for control in rig["pins"]:
            cx, cy = control["center"]
            if control.get("polygon"):
                draw.line([tuple(p) for p in control["polygon"]] + [tuple(control["polygon"][0])], fill=(0, 235, 195), width=2)
            draw.ellipse((cx-6, cy-6, cx+6, cy+6), fill=(0, 255, 195))
            draw.text((cx+9, cy-12), control["name"], fill=(0, 20, 30), stroke_width=1, stroke_fill=(255,255,255))
        overview.resize((1280,720), Image.Resampling.LANCZOS).save(previews / f"{family}-controls.jpg", quality=93)
        print(f"BUILT {family}: {len(weights)} controls; build eyelids with build-cg-eyes.py")
    print(f"Godot project: {PROJECT / 'project.godot'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    build(args.source)
