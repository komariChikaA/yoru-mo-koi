"""Generate Memory's anime profile grid, gold structure and pink/blue cords.

The current design is procedural; earlier Eagle sources stay as provenance.
Only generated assets are installed into the mapset. The CG is never opened.
"""
from pathlib import Path
import argparse
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/memory-editorial'
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')

def build(mapset):
    OUT.mkdir(parents=True, exist_ok=True)
    # One open lattice: nodes do not touch the short line/dot runs.
    size=(1708,960)
    supersample=4
    canvas_size=(854*supersample,480*supersample)
    grid=Image.new('RGBA',canvas_size,(0,0,0,0))
    ink=ImageDraw.Draw(grid)
    def dot(x,y,r,color):
        ink.ellipse(((x-r)*4,(y-r)*4,(x+r)*4,(y+r)*4),fill=color)
    for row,y in enumerate(range(10,480,28)):
        for col,x in enumerate(range(10,854,28)):
            # Muted warm brown anchors; powder-blue interrupted arms.
            dot(x,y,1.0,(167,124,68,115))
            for a,b in [(6,10),(16,20)]:
                ink.line([((x+a)*4,y*4),((x+b)*4,y*4)],
                    fill=(112,176,199,108),width=3)
            for offset in [7,14,21]:
                dot(x,y+offset,.55,(112,176,199,118))
            # Sparse crosses belong to the lattice, never random marks.
            if (col%5,row%4)==(2,1):
                ink.line([((x-2.4)*4,y*4),((x+2.4)*4,y*4)],
                    fill=(222,170,63,140),width=3)
                ink.line([(x*4,(y-2.4)*4),(x*4,(y+2.4)*4)],
                    fill=(222,170,63,140),width=3)
    # Quiet the immediate reading area with a smooth mask, not a column panel.
    yy,xx=np.mgrid[:960,:1708]
    quiet=1-.38*np.exp(-.5*(((xx/2-185)/156)**4+((yy/2-290)/116)**4))
    grid=grid.resize(size,Image.Resampling.LANCZOS)
    alpha=np.asarray(grid.getchannel('A'),dtype=float)
    grid.putalpha(Image.fromarray(np.rint(alpha*quiet).astype('uint8')))
    grid.save(OUT/'profile-grid.png')

    # One antialiased flat disc, tinted and grown by Storybrew. No gradients,
    # surface lighting, liquid shading, photographic texture or baked shadows.
    disc=Image.new('RGBA',(2048,2048),(255,255,255,0))
    ImageDraw.Draw(disc).ellipse((8,8,2040,2040),fill=(255,255,255,255))
    disc.resize((512,512),Image.Resampling.LANCZOS).save(OUT/'background-disc.png')

    # The reference's vertical information column becomes a full-width footer.
    # Its edges extend beyond the screen, so it never reads as a detached card.
    strip_size=(1760,160) # 880x80 screen px: 16.7% of the frame, full-width overscan.
    # A pale flat centre with slim warm-yellow edge rails, not a shaded paper card.
    strip=Image.new('RGBA',strip_size,'#F5D88C')
    strip_ink=ImageDraw.Draw(strip)
    strip_ink.rectangle((0,0,1759,11),fill='#E8BD4A')
    strip_ink.rectangle((0,148,1759,159),fill='#E8BD4A')
    strip_ink.line([(0,1),(1759,1)],fill='#B38B40',width=2)
    strip_ink.line([(0,158),(1759,158)],fill='#B38B40',width=2)
    strip.save(OUT/'section-strip.png')
    source=Image.open(ROOT/'imagetexture_00049.jpg').convert('L')
    source=source.filter(ImageFilter.GaussianBlur(.35))
    # Crop, then use the texture at 120% size, rather than stretching a whole page.
    w,h=1467,133
    x,y=(source.width-w)//2,(source.height-h)//2
    source=source.crop((x,y,x+w,y+h)).resize(strip_size,Image.Resampling.LANCZOS)
    a=np.asarray(source,dtype=float)
    grain=(a-a.mean())*.85 # Neutral mean; modestly lower contrast for flat print.
    # Match the underlying centre/edge colors so the existing paper overlay
    # adds grain without turning the pale centre yellow again.
    rgb=np.clip(np.rint(np.asarray(strip,dtype=float)[:,:,:3]+grain[...,None]),0,255).astype('uint8')
    paper=np.zeros((160,1760,4),dtype='uint8')
    paper[:,:,:3]=rgb
    paper[:,:,3]=255
    paper[:3,:,3]=0
    paper[-3:,:,3]=0 # Both thin structural rules stay crisp.
    Image.fromarray(paper).save(OUT/'section-strip-paper.png')

    # Bell cords: matte dyed fibers, not a shaded cylindrical tube.
    # Keep the 16x96 section sprite contract used by existing animated segments.
    def cord_texture(face_color, radius):
        yy=(np.arange(96,dtype=float)+.5)/8-6
        xx=np.arange(16,dtype=float)[None,:]
        coverage=np.clip((radius+.12-np.abs(yy))/.24,0,1)
        # Restrained diagonal fiber crossings; no central glint, rim or shadow.
        weave=np.sin(2*np.pi*(xx/8+yy[:,None]/1.3))
        counter=np.sin(2*np.pi*(xx/8-yy[:,None]/1.3))
        fibers=3.0*weave+1.5*counter
        rgb=np.clip(np.array(face_color)[None,None,:]+fibers[:,:,None],0,255)
        rgba=np.empty((96,16,4),dtype='uint8')
        rgba[:,:,:3]=np.rint(rgb).astype('uint8')
        rgba[:,:,3]=np.rint(np.broadcast_to(coverage[:,None],(96,16))*255).astype('uint8')
        return Image.fromarray(rgba)
    cord_texture([239,98,143],1.7).save(OUT/'memory-cord.png') # 3.4px
    cord_texture([84,159,200],1.9).save(OUT/'blue-cord.png') # 3.8px
    dest=mapset/'sb/memory-editorial'
    dest.mkdir(parents=True,exist_ok=True)
    for name in ['profile-grid.png','background-disc.png','section-strip.png','section-strip-paper.png','memory-cord.png','blue-cord.png']:
        target=dest/name
        if not target.exists() or (OUT/name).read_bytes()!=target.read_bytes():
            shutil.copyfile(OUT/name,target)
    print('Installed profile grid, full-width local-paper information strip and pink/blue cords')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--mapset',type=Path,default=MAPSET)
    build(p.parse_args().mapset)
