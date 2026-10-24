"""One neutral supplied paper, modest contrast increase, no dirt or warm tint."""
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTRAST = .65 * 1.15
BACKGROUND_OPACITY, SPARSE_OPACITY, MEMORY_OPACITY = .10, .12, .13

def stock():
    source = Image.open(ROOT / 'imagetexture_00049.jpg').convert('L')
    a = np.asarray(source.filter(ImageFilter.GaussianBlur(.45)), dtype=float)
    # Same neutral mean and clean limits as before; 15% more texture contrast.
    paper = Image.fromarray(np.clip(242 + (a-a.mean()) * CONTRAST, 208, 252).astype('uint8')).convert('RGB')
    scale = max(854/paper.width, 480/paper.height)
    paper = paper.resize((round(paper.width*scale), round(paper.height*scale)), Image.Resampling.LANCZOS)
    x,y = (paper.width-854)//2, (paper.height-480)//2
    return paper.crop((x,y,x+854,y+480))

def enlarged():
    return stock().resize((1025,576), Image.Resampling.LANCZOS)

def opening_stock(base):
    # Grain-only composite preserves the approved yellow. The identical 16px
    # tile covers the static page and every shrinking cell; no handoff seam.
    a = np.asarray(enlarged(), dtype=float)[240:256,480:496]
    rgb = np.clip(np.rint(np.array(base)+(a-a.mean())*SPARSE_OPACITY),0,255).astype('uint8')
    tile = Image.fromarray(rgb)
    page = Image.new('RGB',(864,480))
    for y in range(0,480,16):
        for x in range(0,864,16): page.paste(tile,(x,y))
    return tile,page
