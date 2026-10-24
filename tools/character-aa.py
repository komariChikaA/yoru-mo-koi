"""Character-only card and stroke coverage; no changes to layout or timing."""
from pathlib import Path
import importlib.util
import hashlib
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD_RES = 3
DRAW_RES = 6
PAD = 2  # logical pixels outside the unchanged 120px face
COLORS = {'ivory': '#F7F1E8', 'pink': '#C98F96', 'mustard': '#E3C97E',
          'ink': '#496A78'}


def rgb(key):
    return tuple(bytes.fromhex(COLORS[key][1:]))


def source_design():
    spec = importlib.util.spec_from_file_location('flip_design', ROOT/'tools/build-flip.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text_layout(lines, design):
    # Keep the original font selection and logical text metrics. Render that
    # layout at higher resolution rather than enlarging its old raster.
    draw = ImageDraw.Draw(Image.new('RGB', (120,120)))
    for size in range(28,11,-1):
        font = ImageFont.truetype(design.FONT,size)
        boxes = [draw.textbbox((0,0),line,font=font) for line in lines]
        widths = [b[2]-b[0] for b in boxes]
        heights = [b[3]-b[1] for b in boxes]
        total = sum(heights)+4*(len(lines)-1)
        if max(widths)<=104 and total<=104:
            break
    y = (120-total)/2
    result = []
    for line,b,width,height in zip(lines,boxes,widths,heights):
        result.append((line,(120-width)/2-b[0],y-b[1]))
        y += height+4
    return size,result


def cards(out):
    design = source_design()
    dest = Path(out)/'flip'
    dest.mkdir(parents=True,exist_ok=True)
    ss = DRAW_RES
    size = (120+2*PAD)*ss
    def point(x,y): return ((x+PAD)*ss,(y+PAD)*ss)
    for index in range(-1,len(design.FLIPS)):
        if index<0:
            fill,deco,lines = 'ivory',None,None
        else:
            _,_,_,old_fill,deco,lines,_ = design.FLIPS[index]
            fill = 'pink' if old_fill==design.BLUE else 'mustard' if old_fill==design.YELLOW else 'ivory'
        im = Image.new('RGB',(size,size),rgb(fill))
        draw = ImageDraw.Draw(im)
        ink = rgb('ink')
        if deco=='dots':
            for y in range(28,100,22):
                for x in range(28,100,22):
                    # Original integer ellipse occupies seven logical pixels.
                    draw.ellipse((*point(x-3,y-3),*point(x+4,y+4)),fill=ink)
        elif deco=='slash':
            for i in range(-1,6):
                x=16+i*22
                draw.line((*point(x,102),*point(x+36,18)),fill=ink,width=3*ss)
        elif deco=='star':
            vertices=[]
            for i in range(8):
                angle=-math.pi/2+i*math.pi/4
                radius=28 if i%2==0 else 28*.4
                vertices.append(point(60+radius*math.cos(angle),60+radius*math.sin(angle)))
            draw.polygon(vertices,fill=ink)
        if lines:
            font_size,layout=text_layout(lines,design)
            font=ImageFont.truetype(design.FONT,font_size*ss)
            for text,x,y in layout:
                draw.text(point(x,y),text,font=font,fill=ink)
        # A one-screen-pixel coverage ramp straddles the original perimeter.
        # RGB is extended into the transparent padding to avoid dark fringes.
        coords=(np.arange(size)+.5)/ss-PAD
        coverage=np.clip(np.minimum(coords+.5,120.5-coords),0,1)
        alpha=np.round(255*coverage[:,None]*coverage[None,:]).astype(np.uint8)
        output_size=((120+2*PAD)*CARD_RES,)*2
        rgba=im.resize(output_size,Image.Resampling.LANCZOS).convert('RGBA')
        rgba.putalpha(Image.fromarray(alpha).resize(output_size,Image.Resampling.LANCZOS))
        name='paper.png' if index<0 else f'b{index:02}.png'
        rgba.save(dest/name)


def strokes(out):
    # Separate profiles keep the original visible widths while giving each
    # width a full screen-pixel of edge coverage, including the slim strokes.
    resolution=2
    height=24  # Slim strokes need enough transparent sampling room as well.
    yy=(np.arange(height*resolution)+.5)/resolution-height/2
    for thick in (.48,.28,.18):
        half_width=(5.2+2.2*(1-math.sqrt(.5)))*thick
        alpha=np.clip(half_width+.5-np.abs(yy*thick),0,1)
        data=np.full((height*resolution,64*resolution,4),255,np.uint8)
        data[...,3]=np.round(alpha[:,None]*255).astype(np.uint8)
        Image.fromarray(data).save(Path(out)/f'arc-stroke-{round(thick*10000)}.png')


def build(out):
    cards(out)
    strokes(out)


def manifest(out):
    out=Path(out)
    path=out/'manifest.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    textures=list((out/'flip').glob('*.png'))+list((out/'arcs').glob('*.png'))+list(out.glob('arc-stroke-*.png'))
    records=[]
    for p in sorted(textures):
        image=Image.open(p).convert('RGBA')
        relative=p.relative_to(out).as_posix()
        scale=1/CARD_RES if relative.startswith('flip/') else .5
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        records.append(dict(file=relative,size=list(image.size),scale=scale,sha256=digest))
        for source in data.get('assets',[]):
            if source['file']==relative:
                source['size']=list(image.size)
                source['output_sha256']=digest
                source['output_alpha_sha256']=hashlib.sha256(np.array(image)[...,3].tobytes()).hexdigest()
    data['antialias']=dict(card_face_pixels=120,card_padding_pixels=PAD,
                          textures=records,rgba_bytes=sum(r['size'][0]*r['size'][1]*4 for r in records))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    import argparse,shutil
    parser=argparse.ArgumentParser()
    parser.add_argument('--mapset',type=Path,required=True)
    args=parser.parse_args()
    out=ROOT/'assets/character-palette'
    build(out)
    spec=importlib.util.spec_from_file_location('arcs',ROOT/'tools/character-arcs.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(out)
    manifest(out)
    for p in list((out/'flip').glob('*.png'))+list((out/'arcs').glob('*'))+list(out.glob('arc-stroke-*.png'))+[out/'manifest.json']:
        target=args.mapset/'sb/character-palette'/p.relative_to(out)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target)
    print('Installed 3x padded cards and 2x coverage arcs/strokes')
