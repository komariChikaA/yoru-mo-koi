"""Continuous masks for the existing character arcs, after their draw completes."""
from pathlib import Path
import math
import numpy as np
from PIL import Image

ARCS = [(900,-.62,-2.52,.48,False),(830,-1.20,-1.94,.48,False),
        (860,-2.15,-1.78,.28,False),(760,-1.22,-.86,.28,False),
        (690,-2.35,-1.90,.28,False),(650,-1.18,-.80,.28,False),
        (720,-2.05,-1.68,.28,False),(880,-2.05,-1.88,.18,True),
        (840,-2.18,-1.98,.18,False),(870,-1.15,-.98,.18,True),
        (800,-1.22,-1.02,.18,False),(660,-2.20,-2.02,.18,True),
        (620,-1.12,-.96,.18,True),(600,-1.95,-1.78,.18,False),
        (580,-1.28,-1.12,.18,False)]


def key(radius,start,end,thick,taper):
    return f'{round(radius)}_{round(start*10000)}_{round(end*10000)}_{round(thick*10000)}_{int(taper)}'


def build(out):
    out = Path(out)/'arcs'
    out.mkdir(parents=True,exist_ok=True)
    layout = []
    resolution = 2
    ss = 6
    for radius,start,end,thick,taper in ARCS:
        count = max(2,min(140,round(abs(end-start)*radius/16)))
        step = (end-start)/count
        centers = start+step*(np.arange(count)+.5)
        cx,cy = 320+radius*np.cos(centers),900+radius*np.sin(centers)
        valid = (cy>=-60)&(cy<=520)&(cx>=-180)&(cx<=900)
        valid &= ~((cx>250)&(cx<480)&(cy>95)&(cy<230))
        valid &= ~((cx>230)&(cx<480)&(cy>300)&(cy<420))
        pad = 16
        left,top = math.floor(cx[valid].min())-pad,math.floor(cy[valid].min())-pad
        right,bottom = math.ceil(cx[valid].max())+pad,math.ceil(cy[valid].max())+pad
        width,height = right-left,bottom-top
        xs = (np.arange(width*ss)+.5)/ss+left
        ys = (np.arange(height*ss)+.5)/ss+top
        xx,yy = xs[None,:]-320,ys[:,None]-900
        theta = np.arctan2(yy,xx)
        u = (theta-start)/(end-start)
        index = np.clip(np.floor(u*count).astype(int),0,count-1)
        dy = abs(np.hypot(xx,yy)-radius)
        half_width = (5.2+2.2*(1-math.sqrt(.5)))*thick
        alpha = np.clip(half_width+.5-dy,0,1)
        alpha *= (u>=0)&(u<=1)&valid[index]
        if taper:
            alpha *= .35+.65*index/(count-1)
        name = key(radius,start,end,thick,taper)
        # Keep white RGB under zero alpha so bilinear sampling cannot introduce
        # dark fringes when Storybrew rotates the tinted curve.
        image = Image.new('RGBA',(width*resolution,height*resolution),(255,255,255,255))
        image.putalpha(Image.fromarray(np.round(alpha*255).astype(np.uint8)).resize(
            image.size,Image.Resampling.LANCZOS))
        image.save(out/(name+'.png'))
        layout.append(f'{name} {left+width/2:.3f} {top+height/2:.3f}')
    (out/'layout.txt').write_text('\n'.join(layout)+'\n',encoding='utf-8')
