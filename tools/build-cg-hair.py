"""Build independent free-hair layers and locally repaired CG plates.

Contours and bone paths are editable in hair-regions.json. Original CGs
and generated textures stay local. Repairs are pixel inpainting for the small
pilot movement, not newly painted production background art.
"""
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "godot" / "cg-puppet"
ASSETS = PROJECT / "assets"
OUTPUT = ROOT / "_preview" / "cg-puppet" / "hair-layers"


def contour(path):
    """Sample the manually traced M/L/C/Z outline in original-image pixels."""
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", path)
    points, index, current = [], 0, None
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command in ("M", "L"):
            current = np.array([float(tokens[index]), float(tokens[index + 1])])
            index += 2
            points.append(current)
        elif command == "C":
            values = np.array(tokens[index:index + 6], dtype=float).reshape(3, 2)
            index += 6
            start = current
            for t in np.linspace(0, 1, 40)[1:]:
                points.append((1-t)**3*start + 3*(1-t)**2*t*values[0]
                              + 3*(1-t)*t*t*values[1] + t**3*values[2])
            current = values[2]
        elif command != "Z":
            raise ValueError(command)
    return np.round(points).astype(np.int32)


def select(rgb, definition):
    scope = np.zeros(rgb.shape[:2], np.uint8)
    cv2.fillPoly(scope, [contour(definition["outline"])], 255)
    for path in definition.get("exclude", []):
        cv2.fillPoly(scope, [contour(path)], 0)
    if definition.get("refine"):
        # A close, manually bounded trimap keeps the original dark outline and
        # separates the red background between fine branches of golden hair.
        scope = cv2.dilate(scope, np.ones((15,15),np.uint8))
        r,g,b = rgb.astype(np.float32).transpose(2,0,1)
        labels = np.zeros(scope.shape,np.uint8)
        labels[scope > 0] = cv2.GC_PR_BGD
        labels[(scope > 0) & (g > b+14) & (g > r*.4)] = cv2.GC_PR_FGD
        labels[(scope > 0) & (g > b+22) & (g > r*.53) & (g > 90)] = cv2.GC_FGD
        labels[(scope > 0) & (g < r*.47) & (g < b+24)] = cv2.GC_BGD
        cv2.setRNGSeed(15)
        cv2.grabCut(rgb,labels,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),5,cv2.GC_INIT_WITH_MASK)
        scope = np.uint8((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD))*255
        count, components, stats, _ = cv2.connectedComponentsWithStats(scope)
        for component in range(1,count):
            if stats[component,cv2.CC_STAT_AREA] < 40:
                scope[components == component] = 0
        for path in definition.get("details", []):
            # Hand-traced thin strands are authoritative: their dark edges can
            # share the red background's hue and must not be discarded.
            cv2.fillPoly(scope,[contour(path)],255)
        scope = cv2.dilate(scope,np.ones((3,3),np.uint8))
    return scope


def repaint(rgb, mask, definition):
    """Continue local color and clean texture, without borrowing hair pigment."""
    repair = definition["repair"]
    ys,xs = np.where(mask > 0)
    samples = np.array(repair["samples"],dtype=float)
    colors = np.array([np.median(rgb[int(y)-3:int(y)+4,int(x)-3:int(x)+4].reshape(-1,3),axis=0)
                       for x,y in samples])
    weights = 1.0/((xs[:,None]-samples[:,0])**2+(ys[:,None]-samples[:,1])**2+900)
    field = weights @ colors / weights.sum(axis=1)[:,None]
    if repair.get("patch"):
        xlo,xhi = max(0,xs.min()-25),min(rgb.shape[1],xs.max()+26)
        ylo,yhi = max(0,ys.min()-25),min(rgb.shape[0],ys.max()+26)
        local = rgb[ylo:yhi,xlo:xhi].astype(np.float32)
        r,g,b = local.transpose(2,0,1)
        known_background = (g < r*.47) & (g < b+24)
        unknown = ~known_background | (mask[ylo:yhi,xlo:xhi] > 0)
        local[unknown] = colors.mean(axis=0)
        local[ys-ylo,xs-xlo] = field
        # Only genuine red background supplies boundary colors. The adjacent
        # fixed hair/sleeve cannot seed pale stripes into the hidden plate.
        unknown[[0,-1],:] = False
        unknown[:,[0,-1]] = False
        kernel = np.float32([[0,.25,0],[.25,0,.25],[0,.25,0]])
        for iteration in range(1800):
            average = cv2.filter2D(local,-1,kernel)
            difference = np.max(np.abs(average[unknown]-local[unknown]))
            local[unknown] = average[unknown]
            if difference < .02:
                break
        field = local[ys-ylo,xs-xlo]
        x0,y0,x1,y1 = repair["patch"]
        patch = rgb[y0:y1,x0:x1].astype(np.float32)
        # Keep the donor's actual fine mottling; match its broad lighting to the
        # surrounding red background instead of smearing pale hair over it.
        detail = patch-cv2.GaussianBlur(patch,(0,0),12)
        def mirrored(values, length):
            values = np.mod(values,2*(length-1))
            return np.minimum(values,2*(length-1)-values).astype(int)
        field += detail[mirrored(ys-y0,len(patch)),mirrored(xs-x0,patch.shape[1])]*.7
    plate = rgb.copy()
    plate[ys,xs] = np.uint8(np.clip(np.round(field),0,255))
    return plate


def pin_coverage(shape, part):
    yy,xx = np.mgrid[:shape[0],:shape[1]]
    coverage = np.ones(shape,np.float32)
    for key, point in [("root_pin",part["chain"][0]),("tip_pin",part["chain"][-1])]:
        if key not in part:
            continue
        start,end = part[key]
        t = np.clip((np.hypot(xx-point[0],yy-point[1])-start)/(end-start),0,1)
        coverage *= t*t*(3-2*t)
    return coverage


def build(families=None):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    definitions = json.loads((PROJECT / "hair-regions.json").read_text(encoding="utf-8"))
    if families is not None:
        definitions = {family: definitions[family] for family in families}
    rig_path = PROJECT / 'hair-rigs.json'
    manifest = json.loads(rig_path.read_text(encoding='utf-8')) if families is not None and rig_path.exists() else {}
    reports = []
    for family, regions in definitions.items():
        shot = "CGC14_a" if family == "CGC14" else family
        rgb = np.array(Image.open(ASSETS / f"{shot}.png").convert("RGB"))
        directory = ASSETS / family
        masks = [np.uint8(np.round(select(rgb,part)*pin_coverage(rgb.shape[:2],part))) for part in regions]
        hard = np.maximum.reduce(masks)
        alpha_union = cv2.GaussianBlur(hard, (3,3), .45)
        removed = np.uint8(alpha_union > 0) * 255
        for part in regions:
            if part.get("repair",{}).get("outline"):
                cv2.fillPoly(removed,[contour(part["repair"]["outline"])],255)
        repaired = cv2.inpaint(rgb, removed, 5, cv2.INPAINT_TELEA)
        for part, mask in zip(regions,masks):
            if part.get("repair"):
                erase = cv2.dilate(mask,np.ones((7,7),np.uint8))
                if part["repair"].get("outline"):
                    cv2.fillPoly(erase,[contour(part["repair"]["outline"])],255)
                painted = repaint(rgb,erase,part)
                repaired[erase > 0] = painted[erase > 0]
        repaired[removed == 0] = rgb[removed == 0]
        # Keep the original joins under fully fixed mesh caps. A partial-alpha
        # rectangular cut otherwise leaves a dark seam at the root or sleeve.
        yy,xx = np.mgrid[:rgb.shape[0],:rgb.shape[1]]
        for part in regions:
            for key, point in [("root_pin",part["chain"][0]),("tip_pin",part["chain"][-1])]:
                if key in part:
                    fixed = np.hypot(xx-point[0],yy-point[1]) <= part[key][1]+2
                    repaired[fixed] = rgb[fixed]
        combined = np.zeros((*rgb.shape[:2], 4), np.uint8)
        layers = []
        for index, (part, mask) in enumerate(zip(regions, masks)):
            alpha = cv2.GaussianBlur(mask, (3,3), .45)
            a = alpha.astype(np.float32)[...,None] / 255
            foreground = (rgb.astype(float) - (1-a)*repaired) / np.maximum(a, 1/255)
            foreground = np.uint8(np.clip(np.round(foreground), 0, 255))
            rgba = np.dstack([foreground, alpha])
            rgba[alpha == 0, :3] = 0
            Image.fromarray(rgba).save(directory / f"hair-{index}.png")
            Image.fromarray(mask).save(directory / f"hair-selection-{index}.png")
            occupied = alpha > 0
            combined[occupied] = rgba[occupied]
            ys, xs = np.where(occupied)
            layers.append(dict(name=part["name"], texture=f"assets/{family}/hair-{index}.png",
                               bounds=[int(xs.min())-4, int(ys.min())-4, int(xs.max())+5, int(ys.max())+5],
                               chain=part["chain"], sway=part.get("sway", 4),
                               pin_tip=part.get("pin_tip", False),
                               phase=part.get("phase", 0), stiffness=part.get("stiffness", 4.0),
                               damping=part.get("damping", .83), mass=part.get("mass", .75),
                               shadow=part.get("shadow"),root_pin=part.get("root_pin"),tip_pin=part.get("tip_pin")))
            if part.get("shadow"):
                shadow = cv2.GaussianBlur(alpha,(0,0),part["shadow"].get("softness",2))
                Image.fromarray(shadow).save(directory / f"hair-shadow-{index}.png")
                receiver = np.zeros(mask.shape,np.uint8)
                cv2.fillPoly(receiver,[contour(part["shadow"]["receiver"])],255)
                Image.fromarray(receiver).save(directory / f"hair-receiver-{index}.png")
        Image.fromarray(combined).save(directory / "hair.png")
        Image.fromarray(hard).save(directory / "hair-mask.png")
        manifest[family] = layers
        variants = ["CGC14_a","CGC14_b","CGC14_c"] if family == "CGC14" else [family]
        for variant in variants:
            # Source CGs have a one-pixel translucent canvas edge. Preserve it
            # instead of making the entire plate opaque during RGB repair.
            plate = np.array(Image.open(ASSETS / f"{variant}.png").convert("RGBA"))
            plate[removed > 0,:3] = repaired[removed > 0]
            Image.fromarray(plate).save(ASSETS / f"{variant}-plate.png")
        dark = Image.new("RGBA", (1920,1080), (26,31,40,255))
        dark.alpha_composite(Image.fromarray(combined))
        dark.convert("RGB").resize((1280,720)).save(OUTPUT / f"{family}-hair-dark.jpg", quality=95)
        Image.fromarray(repaired).resize((1280,720)).save(OUTPUT / f"{family}-repaired-plate.jpg", quality=95)
        overlay = rgb.copy()
        overlay[hard > 0] = np.uint8(rgb[hard > 0]*.45 + np.array([0,255,200])*.55)
        Image.fromarray(overlay).resize((1280,720)).save(OUTPUT / f"{family}-selection.jpg", quality=95)
        reports.append(dict(family=family, layers=len(layers), hair_pixels=int(np.count_nonzero(hard))))
        print(f"HAIR_LAYER {family}: {len(layers)} layers, {np.count_nonzero(hard)} pixels", flush=True)
    (PROJECT / "hair-rigs.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    (OUTPUT / "layers.json").write_text(json.dumps(reports, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    build()
