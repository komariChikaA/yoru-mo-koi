"""Build flat printing inputs and the faint shadow of a plain photograph.

The reusable C# RotaryPrintReveal generates radial occluders on demand in the
mapset. These inputs contain no fragments of the CG and no line drawings.
"""
from pathlib import Path
import argparse
import shutil
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/memory-print'
W, H, SS = 640, 403, 3


def illustration(details=False):
    im = Image.new('RGB', (W*SS, H*SS), '#b8c5bf')
    d = ImageDraw.Draw(im)

    def ellipse(box, color):
        d.ellipse([round(v*SS) for v in box], fill=color)

    def shape(points, radius, color):
        vertices = np.array(points, dtype=float)
        path = []
        for i, corner in enumerate(vertices):
            incoming = vertices[i-1]-corner
            outgoing = vertices[(i+1) % len(vertices)]-corner
            a_len, b_len = np.linalg.norm(incoming), np.linalg.norm(outgoing)
            trim = min(radius, a_len*.35, b_len*.35)
            a, b = corner+incoming*trim/a_len, corner+outgoing*trim/b_len
            for t in np.linspace(0,1,13):
                point = (1-t)**2*a + 2*(1-t)*t*corner + t*t*b
                path.append(tuple(np.round(point*SS).astype(int)))
        d.polygon(path, fill=color)

    ellipse((-210,-190,470,345), '#d8dfc7')
    ellipse((-112,-125,112,133), '#92a5a0')
    ellipse((476,-105,826,322), '#92a5a0')
    ellipse((-370,286,1010,1080), '#a8af96')
    shape([(533,218),(600,243),(600,322),(533,333)],14,'#b3a789')
    shape([(121,148),(421,6),(534,153),(534,333),(121,333)],18,'#b3a789')
    if details:
        # Filled local structure and shadow, never diagram-style strokes.
        shape([(121,169),(202,135),(210,333),(121,333)],10,'#9eA184')
        shape([(448,136),(534,161),(534,333),(448,333)],10,'#99947d')
        shape([(47,171),(422,2),(589,205),(574,202),(421,18),(63,178)],7,'#858674')
        shape([(202,111),(523,108),(539,126),(205,128)],8,'#d0c2a3')
        d.rounded_rectangle([357*SS,138*SS,444*SS,333*SS],radius=8*SS,fill='#8c846e')
        d.rounded_rectangle([177*SS,193*SS,198*SS,235*SS],radius=4*SS,fill='#899279')
        shape([(538,222),(619,244),(598,254),(535,235)],5,'#c6b89b')
    # Self-made print masses only. Geometry/alpha and the original CG are untouched.
    im = ImageEnhance.Color(im).enhance(.92)
    im = ImageEnhance.Brightness(im).enhance(1.03)
    return im.resize((W,H),Image.Resampling.LANCZOS).convert('RGBA')


def photo_shadow():
    # Plain 670x424 photo paper is the persistent liquid sprite, not a baked frame.
    # This faint shadow is the only extra layer under it.
    shadow = Image.new('RGBA',(706,460))
    ImageDraw.Draw(shadow).rectangle((18,18,687,441),fill=(57,50,42,65))
    shadow.filter(ImageFilter.GaussianBlur(8)).save(OUT/'photo-shadow.png')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--mapset',type=Path,default=Path(r'E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ'))
    args = p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    illustration().save(OUT/'coarse.png')
    illustration(True).save(OUT/'details.png')
    photo_shadow()
    target = args.mapset/'sb/memory-print'
    target.mkdir(parents=True,exist_ok=True)
    for source in OUT.glob('*.png'): shutil.copyfile(source,target/source.name)
    for name in ('secret-base.png','px.png'):
        destination = args.mapset/'sb'/name
        if not destination.exists():
            shutil.copyfile(ROOT/'graphics/mapset/sb'/name,destination)
    print('Built and installed flat print stages and plain photo shadow')
