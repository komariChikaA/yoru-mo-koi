"""Prepare native sunset motes and static-character exclusion mattes."""
from pathlib import Path
import json
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('${GAME_ROOT}/解包/其他图片/粒子')
ASSETS = ROOT / 'godot/chorus-four/assets/sunset-particles'
RECORD = ROOT / 'assets/chorus-four/particles.json'
HALO_SOURCE = SOURCE.parents[1] / 'CG/CGC14_a.png'
HALO_CROPS = {'bright': (229, 141, 277, 189), 'defocus': (448, 280, 496, 328)}


def native_halos():
    """Separate the two requested baked CG highlights from their local ground."""
    source = Image.open(HALO_SOURCE).convert('RGB')
    records = []
    for name, box in HALO_CROPS.items():
        patch = np.asarray(source.crop(box), dtype=np.float64) / 255.0
        h, w = patch.shape[:2]
        y, x = np.mgrid[-1:1:complex(h), -1:1:complex(w)]
        basis = np.stack([np.ones_like(x), x, y, x*y], axis=-1)
        ring = (np.abs(x) > .76) | (np.abs(y) > .76)
        coefficients = np.linalg.lstsq(basis[ring], patch[ring], rcond=None)[0]
        ground = np.clip(basis @ coefficients, 0.0, 0.99)
        delta = patch - ground
        luminance = delta @ np.array([.2126, .7152, .0722])
        _, labels = cv2.connectedComponents((luminance > .008).astype(np.uint8))
        center = luminance[14:34, 14:34]
        cy, cx = np.unravel_index(center.argmax(), center.shape)
        component = labels[cy+14, cx+14]
        support = (labels == component) if component else np.zeros_like(labels, dtype=bool)
        alpha = np.clip(np.max(delta / np.maximum(1.0-ground, .01), axis=2), 0.0, 1.0)
        foreground = np.clip(ground + delta / np.maximum(alpha[..., None], 1e-6), 0.0, 1.0)
        # Exclude the surrounding rock texture outside the actual CG glow.
        yy, xx = np.mgrid[:h, :w]
        radius = np.sqrt((xx-(cx+14))**2 + (yy-(cy+14))**2)
        inner, outer = (13.0, 20.0) if name == 'bright' else (11.0, 17.0)
        edge = np.clip((outer-radius)/(outer-inner), 0.0, 1.0)
        edge = edge*edge*(3.0-2.0*edge)
        alpha *= support * np.clip((luminance-.008)/.014, 0.0, 1.0) * edge
        rgba = np.uint8(np.rint(np.dstack([foreground, alpha])*255))
        rgba[rgba[..., 3] == 0, :3] = 0
        texture = Image.new('RGBA', (w+16, h+16))
        texture.paste(Image.fromarray(rgba), (8, 8))
        target = ASSETS / f'native-halo-{name}.png'
        texture.save(target)
        records.append(dict(source=str(HALO_SOURCE), crop=list(box), target=str(target.relative_to(ROOT)),
            treatment='Actual CG highlight RGB/shape; local bilinear ground separation, connected highlight alpha, transparent 8px padding',
            size=list(texture.size), max_alpha=int(rgba[..., 3].max())))
    return records

# Protect the solid head, body, limbs and firm upper hair. Loose animated
# clusters render above the motes using their own native alpha.
POLYGONS = {
    14: [
        [(1465,155),(1520,85),(1610,35),(1730,35),(1835,95),(1900,180),
         (1915,285),(1890,360),(1790,450),(1650,510),(1520,510),
         (1445,440),(1440,340)],
        [(1220,245),(1320,245),(1430,320),(1505,395),(1560,490),
         (1500,635),(1390,745),(1275,855),(1190,1040),(1060,1080),
         (835,1080),(740,1015),(605,900),(570,775),(520,675),
         (575,555),(605,415),(690,305),(790,345),(940,320),(1020,325)],
        [(615,520),(785,615),(800,745),(625,905),(360,1080),
         (150,1080),(365,805),(485,650)],
        [(740,785),(915,955),(865,1080),(385,1080),(595,930)],
        [(1430,190),(1500,270),(1450,360),(1250,340),(1060,305),
         (920,255),(1040,210),(1230,190)],
    ],
    15: [
        [(540,280),(565,180),(640,85),(730,5),(1095,0),(1235,90),
         (1310,200),(1380,330),(1370,460),(1310,600),(1210,675),
         (1050,705),(855,675),(680,590),(560,465),(525,365)],
        [(0,300),(155,350),(270,440),(345,500),(425,485),(495,515),
         (610,590),(760,650),(870,720),(1110,735),(1290,660),
         (1395,555),(1510,535),(1635,555),(1680,630),(1630,715),
         (1680,795),(1800,850),(1850,965),(1905,1080),(955,1080),
         (900,960),(825,875),(750,795),(590,775),(475,755),(350,715),
         (230,735),(105,740),(90,715),(260,670),(150,665),(70,650),(30,620),(0,550)],
        [(1320,290),(1430,305),(1540,350),(1610,400),(1640,450),
         (1680,500),(1635,520),(1550,505),(1475,520),(1390,475)],
    ],
}


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    sources = []
    for suffix, name in [('small', '雪球小.png'), ('medium', '雪球中.png'), ('large', '雪球大.png')]:
        target = ASSETS / f'mote-{suffix}.png'
        shutil.copy2(SOURCE / name, target)
        image = Image.open(target)
        sources.append(dict(source=str(SOURCE / name), target=str(target.relative_to(ROOT)),
                            size=list(image.size), treatment='Original RGBA unchanged; warm tint at runtime'))
    halos = native_halos()
    for cg, polygons in POLYGONS.items():
        mask = Image.new('L', (1920, 1080))
        draw = ImageDraw.Draw(mask)
        for polygon in polygons:
            draw.polygon(polygon, fill=255)
        # Keep the complete solid core at 255, soften only outside its edge.
        mask = mask.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(2.0))
        mask.save(ASSETS / f'CGC{cg}-exclusion.png')
    record = dict(sources=sources, native_halos=halos, canvas=[1920,1080],
                  contour_definition='tools/prepare-chorus-four-particles.py:POLYGONS',
                  exclusion='White blocks background motes; native moving hair renders above. '
                            'Static contour expanded 12px, outer feather sigma2; per-fragment shader clipping.',
                  runtime='godot/chorus-four/sunset-particles.gd',
                  placement='Each CG SubViewport, repaired plate < motes < original eyes and moving hair',
                  mood='Actual bright and defocused highlights extracted from the CG sunset background',
                  eagle_search='Searched local Eagle particles/light keywords; selected matching unpacked native sprites')
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Prepared native sunset motes and two character exclusion mattes.')


if __name__ == '__main__':
    prepare()
