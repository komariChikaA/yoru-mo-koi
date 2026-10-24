"""Draw the existing circular shelf in its semantic palette, with coverage AA.

The geometry matches the current 4901×2737 shelf. No inverse RGB classification:
mixed edge pixels are created after assigning the correct material colors.
"""
import math
import numpy as np
from PIL import Image

CREST_Y = 400.0
R_OUT = 1600.0
R_IN = R_OUT - 460.0
PIVOT_X, PIVOT_Y = 320.0, 2000.0
HALF = math.radians(96.0)
TH0, TH1 = -math.pi/2-HALF, -math.pi/2+HALF
OUT_SCALE = 1.5
SAMPLES = 3


def bounds():
    xs, ys = [], []
    for a in np.linspace(TH0, TH1, 81):
        for r in (R_IN-10, R_OUT+12):
            xs.append(PIVOT_X+r*math.cos(a))
            ys.append(PIVOT_Y+r*math.sin(a))
    return min(xs)-22, min(ys)-22, max(xs)+22, max(ys)+22


def records(bottom, phase, height_scale, palette):
    phrase = [(18,10,0,0),(22,14,1,1),(15,8,2,0),(20,16,3,0),
              (17,11,4,1),(14,7,5,0),(24,13,6,0),(19,9,7,1)]
    colors = [palette[k] for k in ['ink','pink','mustard','mist','ivory','mist','blue','wood']]
    theta, i, recs = TH0+.035, 0, []
    while theta < TH1-.035:
        height, thick, color_i, mark = phrase[(i+phase)%8]
        height *= height_scale
        top = bottom+height
        center = theta+thick*.5/top
        recs.append((bottom,top,thick*.5/bottom,thick*.5/top,center,mark,height,thick))
        theta += (thick+1.15)/((top+bottom)*.5)
        i += 1
    a = np.array(recs,np.float32)
    color = np.array([colors[phrase[(j+phase)%8][2]] for j in range(i)],np.float32)
    return a, color


def paint_books(rgb, radius, angle, row, palette):
    recs, colors = row
    centers = recs[:,4]
    selected = (radius > recs[0,0]-1.6) & (radius < recs[:,1].max()+1.6)
    if not np.any(selected):
        return
    rr, aa = radius[selected], angle[selected]
    j = np.clip(np.searchsorted(centers,aa),1,len(centers)-1)
    use = np.where(np.abs(aa-centers[j-1]) <= np.abs(aa-centers[j]),j-1,j)
    rb,rt,da0,da1,center,mark,height,thick = recs[use].T
    dang = np.abs(aa-center)
    cols = rgb[selected]
    def half_at(top,bottom,factor):
        t = np.clip((rr-bottom)/np.maximum(top-bottom,.001),0,1)
        return (da0+(da1-da0)*t)*factor
    def fill(top,bottom,half,color,enabled=True):
        distance = np.minimum(np.minimum(top-rr,rr-bottom),(half-dang)*rr)
        coverage = np.clip(.5+distance*OUT_SCALE*SAMPLES,0,1)
        coverage = np.where(enabled,coverage,0)[:,None]
        cols[:] = cols*(1-coverage)+color*coverage
    fill(rt,rb,half_at(rt,rb,1),colors[use])
    page = np.minimum(2.6,height*.16)
    # Retain the old page cap coordinates, including its tapered angular span.
    fill(rt,rt-page,half_at(rt,rt-page,.98),palette['ivory'])
    top, bot = rt-page-1, rb+height*.18
    factor = np.maximum(1.7,thick*.16)/thick
    fill(top,bot,half_at(top,bot,factor),palette['dark'],mark==0)
    top = rt-page-1.2
    bot = top-np.maximum(3.2,height*.22)
    fill(top,bot,half_at(top,bot,.46),palette['ivory'],mark==1)
    rgb[selected] = cols


def render(palette, expected_size):
    palette = {k:np.array(tuple(bytes.fromhex(v[1:])),np.float32) for k,v in palette.items()}
    left,top,right,bottom = bounds()
    width,height = round((right-left)*OUT_SCALE),round((bottom-top)*OUT_SCALE)
    assert (width,height) == expected_size, 'Shelf geometry differs from source'
    rows = [records(R_OUT-27.2,0,.86,palette),records(R_OUT-51.6,3,.72,palette)]
    output = Image.new('RGBA',(width,height))
    xs = (np.arange(width*SAMPLES,dtype=np.float32)+.5)/(OUT_SCALE*SAMPLES)+left
    # Chunking limits temporary memory; every output pixel has nine samples.
    for y in range(0,height,32):
        count = min(32,height-y)
        ys = (np.arange(y*SAMPLES,(y+count)*SAMPLES,dtype=np.float32)+.5)/(OUT_SCALE*SAMPLES)+top
        dy,dx = ys[:,None]-PIVOT_Y,xs[None,:]-PIVOT_X
        radius = np.hypot(dx,dy)
        angle = np.arctan2(dy,dx)
        delta = (angle+np.pi/2+np.pi)%(2*np.pi)-np.pi
        inside = np.minimum(np.minimum(R_OUT-radius,radius-R_IN),
                            (HALF-np.abs(delta))*np.maximum(radius,1))
        alpha = np.clip(.5+inside*OUT_SCALE*SAMPLES,0,1)
        rgb = np.empty((*radius.shape,3),np.float32)
        rgb[:] = palette['wood']
        # Same radial bands and order as the existing shelf, now supersampled.
        rgb[(radius<R_OUT-33.6)&(radius>R_OUT-52.2)] = palette['dark']
        rgb[(radius<R_OUT-5.2)&(radius>R_OUT-27.4)] = palette['dark']
        rgb[(radius<R_OUT-28)&(radius>R_OUT-32.2)] = palette['cream']
        rgb[(radius<R_OUT-28)&(radius>R_OUT-29.1)] = palette['ivory']
        rgb[radius>R_OUT-5.4] = palette['ivory']
        rgb[radius>R_OUT-4.2] = palette['cream']
        rgb[radius>R_OUT-1.5] = palette['dark']
        rgb[radius<R_IN+3.2] = palette['cream']
        rgb[radius<R_IN+1.6] = palette['dark']
        for row in rows:
            paint_books(rgb,radius,angle,row,palette)
        tile = np.empty((*radius.shape,4),np.uint8)
        tile[...,:3] = np.round(rgb).astype(np.uint8)
        tile[...,3] = np.round(alpha*255).astype(np.uint8)
        output.paste(Image.fromarray(tile).resize((width,count),Image.Resampling.BOX),(0,y))
    return np.array(output)
