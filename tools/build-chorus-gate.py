"""Build the 52.7–59.5s school-gate chorus and its shared sprite tracks.

Game art stays local. Storybrew and the 1080p review read the same linear
tracks; the final camera and lyric reveals deliberately hold at 12fps.
"""
from pathlib import Path
import argparse
import bisect
import csv
import importlib.util
import json
import math
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
OUT = ROOT / 'assets/chorus-gate'
REVIEW = ROOT / '_preview/chorus'
START, REVEAL, SLOW, MOTTO, LIGHT, SETTLE, END = 52700, 53150, 56400, 56950, 57700, 58250, 59500
COLLISION, GATE_REVEAL, SKY_END = 53400, 55550, 55790
# Finish the orbit after it has faded, so the crossfade retains forward motion.
ORBIT_END = SKY_END + 400
CHARACTER_SWEEP_START, CHARACTER_REVEAL_END, CHARACTER_MASK_FRAMES = 55670, 56200, 32
SUPPORT_SWEEP_START, SUPPORT_REVEAL_END, SUPPORT_MASK_FRAMES = LIGHT+167, LIGHT+750, 7
HOLD_DEPTH_GAIN = 1.30
sprites, commands = [], []
FONT_SOURCES = json.loads((OUT / 'fonts.json').read_text(encoding='utf-8'))


def emit(name, image):
    image.save(OUT / name, compress_level=3)
    return name


def warm(image, background=False, lit=False):
    data = np.array(image.convert('RGBA'), dtype=np.float32)
    rgb = data[..., :3]
    # Clear daylight first; the last lyric changes the scene to bright warm-white light.
    gray = rgb.mean(axis=2, keepdims=True)
    rgb = gray + (rgb-gray) * (.94 if background else .98)
    rgb = rgb * np.array([1.06, 1.045, 1.005] if lit else [1.015, 1.025, 1.035])
    rgb += [17, 12, 7] if lit else [8, 8, 8]
    data[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(data.astype(np.uint8))


def glow(image, radius=9, strength=.28):
    data = np.array(image)
    luminance = data[..., :3].max(axis=2)
    alpha = np.clip((luminance.astype(float)-175)/80, 0, 1) * data[..., 3] * strength
    halo = Image.new('RGBA', image.size, (255, 239, 198, 0))
    halo.putalpha(Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius)))
    # Soft light spreads beyond the alpha silhouette without replacing detail.
    return Image.alpha_composite(halo, image)


def lettering(text, size, name, role='japanese', tracking=0):
    font_path = FONT_SOURCES[role]['filePath']
    font = ImageFont.truetype(font_path, size)
    box = font.getbbox(text)
    if tracking:
        width = sum(font.getlength(ch) for ch in text) + tracking*(len(text)-1)
        box = (box[0], box[1], math.ceil(width), box[3])
    image = Image.new('RGBA', (box[2]-box[0]+48, box[3]-box[1]+48))
    pen = ImageDraw.Draw(image)
    if tracking:
        x = 24-box[0]
        for char in text:
            pen.text((x, 24-box[1]), char, font=font, fill=(255, 253, 238))
            x += font.getlength(char)+tracking
    else:
        pen.text((24-box[0], 24-box[1]), text, font=font, fill=(255, 253, 238))
    # A diffuse, low-opacity shadow keeps fine strokes legible without thickening them.
    shadow = Image.new('RGBA', image.size, (68, 45, 26, 0))
    shadow.putalpha(image.getchannel('A').filter(ImageFilter.MaxFilter(5))
                    .filter(ImageFilter.GaussianBlur(1.8)).point(lambda v: round(v*.65)))
    return emit(name, Image.alpha_composite(shadow, image))


def sprite(file):
    ident = len(sprites)
    sprites.append((ident, file))
    return ident


def command(ident, start, end, p0, p1=None, a0=1, a1=None):
    # pose: x, y, scaleX, scaleY, radians; alpha is independent of camera.
    commands.append((ident, start, end, *p0[:2], *(p1 or p0)[:2],
                     *p0[2:4], *(p1 or p0)[2:4], p0[4], (p1 or p0)[4],
                     a0, a0 if a1 is None else a1))


def ease(q):
    return q*q*(3-2*q)


def curve(q, mode):
    if mode == 'out-drift': return .75*(1-(1-q)**3)+.25*q
    if mode == 'out-cubic': return 1-(1-q)**3
    if mode == 'out-quart': return 1-(1-q)**4
    if mode == 'in-out-sine': return (1-math.cos(math.pi*q))/2
    if mode == 'out-sine': return math.sin(math.pi*q/2)
    return ease(q)


KEYS = [
    (START, 0, 1.45, 240, 240),
    (REVEAL, -30, 1.78, 240, 240),
    (GATE_REVEAL, -6, 1.10, 960, 580),
    (SLOW, 3, 1.00, 960, 610),
    (MOTTO, 0, 1.00, 960, 610),
    (LIGHT, -12, 1.36, 960, 490),
    (END, 4, 1.08, 960, 560),
]
CAMERA_CURVES = [
    ('out-sine', 'out-cubic', 'out-cubic'),
    ('smooth', 'out-cubic', 'out-cubic'),
    ('out-cubic', 'out-cubic', 'out-cubic'),
    ('in-out-sine', 'in-out-sine', 'in-out-sine'),
    ('out-sine', 'out-cubic', 'out-cubic'),
    ('out-drift', 'out-drift', 'out-drift'),
]

LYRIC_PATHS = {
    # Screen-space anchors preserve reading; small offsets still follow the camera.
    'love': [(REVEAL, 470, 215, .89, -3), (53400, 500, 210, .92, -2),
             (54400, 470, 218, .92, 2), (55500, 490, 210, .92, -2),
             (MOTTO, 485, 210, .92, -2)],
    'begin': [(54050, 1100, 910, .96, 3), (54350, 1020, 885, 1.00, 0),
              (55150, 990, 880, 1.02, -2), (56000, 1040, 885, 1.01, 1),
              (MOTTO, 1020, 880, 1.00, 0)],
}


def lyric_local(t, path):
    for left, right in zip(path, path[1:]):
        if t <= right[0]:
            q = curve(np.clip((t-left[0])/(right[0]-left[0]), 0, 1), 'out-cubic')
            return tuple(a+(b-a)*q for a, b in zip(left[1:], right[1:]))
    return path[-1][1:]


def readable_lyric_pose(t, path):
    x, y, size, tilt = lyric_local(t, path)
    angle, zoom, _, _ = camera(t)
    rad = math.radians(angle)
    # Keep lettering upright and inside the frame while responding to scene motion.
    x += 32*math.sin(rad)
    y += 14*math.sin(rad)
    size *= 1+.025*(zoom-1)
    tilt += 5*math.sin(rad)
    return (x, y, size, size, math.radians(tilt))


def camera(t):
    value = KEYS[-1][1:]
    for index, (left, right) in enumerate(zip(KEYS, KEYS[1:])):
        if t <= right[0]:
            q = np.clip((t-left[0])/(right[0]-left[0]), 0, 1)
            modes = CAMERA_CURVES[index]
            progress = [curve(q, modes[0]), curve(q, modes[1]), curve(q, modes[2]), curve(q, modes[2])]
            value = tuple(a+(b-a)*p for a, b, p in zip(left[1:], right[1:], progress))
            break
    if t >= MOTTO:
        angle,zoom,cx,cy = value
        # Zoom is inverse virtual camera distance. Increase Z displacement
        # from the 1.0-distance starting pose, rather than scaling the picture.
        distance = 1 + HOLD_DEPTH_GAIN*(1/zoom-1)
        value = (angle,1/distance,cx,cy)
    return value


def pose(t, x, y, scale=1):
    angle, zoom, cx, cy = camera(t)
    rad = math.radians(angle)
    dx, dy = (x-cx)*zoom, (y-cy)*zoom
    return (960+dx*math.cos(rad)-dy*math.sin(rad),
            540+dx*math.sin(rad)+dy*math.cos(rad), scale*zoom, scale*zoom, rad)


def times(start, end):
    result = [start]
    while result[-1] < end:
        now = result[-1]
        if now < MOTTO:
            next_time = min(now+25, MOTTO, end)
        else:
            index = math.floor((now-MOTTO)*12/1000)+1
            if round(MOTTO+index*1000/12) <= now:
                index += 1
            next_time = min(round(MOTTO+index*1000/12), end)
        result.append(next_time)
    # Include exact key cuts before beginning the hold portion.
    return sorted(set(result + [k[0] for k in KEYS if start < k[0] < min(end, MOTTO)]))


def tracked(file, x, y, scale=1, start=REVEAL, end=END, alpha=lambda t: 1, tilt=0, local_path=None, visible_from=None):
    ident = sprite(file)
    samples = times(start, end)
    if visible_from is not None:
        # Preserve the established sampling grid after the short masked entry.
        samples = sorted(set([visible_from]+[t for t in samples if t>visible_from]))
    if local_path:
        samples = sorted(set(samples + [key[0] for key in local_path if start < key[0] < end]))
    def state(t):
        if local_path: return readable_lyric_pose(t, local_path)
        value = pose(t, x, y, scale)
        return (*value[:4], value[4]+math.radians(tilt))
    for a, b in zip(samples, samples[1:]):
        p0 = state(a)
        # Hold the entire scene (including its aim point and focal distance).
        p1 = p0 if a >= MOTTO else state(b)
        command(ident, a, b, p0, p1, alpha(a), alpha(a) if a >= MOTTO else alpha(b))
    return ident


def fixed(file, start, end, x=960, y=540, scale=1, a=1):
    ident = sprite(file)
    command(ident, start, end, (x, y, scale, scale, 0), a0=a)
    return ident


def character_reveal(image, name, x, y, color, onset=GATE_REVEAL,
                     sweep_start=CHARACTER_SWEEP_START, finish=CHARACTER_REVEAL_END,
                     frame_count=CHARACTER_MASK_FRAMES):
    """Alpha-clipped colour silhouette, then a diagonal white/colour wipe.

    Short native sprites share the exact character registration and camera;
    only their masks change. Ren finishes at 56.200s; the supporting cast
    enters on 照らしてくれよ and follows the existing 12fps hold grid.
    """
    alpha = image.getchannel('A')
    body = Image.new('RGBA', image.size, (*color, 255)); body.putalpha(alpha)
    edge = Image.new('RGBA', image.size, (255, 252, 235, 255))
    edge.putalpha(alpha.filter(ImageFilter.MaxFilter(5)))
    shadow = Image.new('RGBA', image.size, (*tuple(round(v*.42) for v in color), 0))
    offset = Image.new('L', image.size); offset.paste(alpha, (12, 10))
    shadow.putalpha(offset.point(lambda v: round(v*.72)))
    silhouette = Image.alpha_composite(shadow, Image.alpha_composite(edge, body))
    tracked(emit(name+'-silhouette.png', silhouette), x, y,
            start=onset, end=sweep_start,
            alpha=lambda t: min(1,(t-onset)/60))
    yy, xx = np.indices((image.height, image.width), dtype=np.float32)
    diagonal = xx+.28*yy
    low, high = diagonal.min()-110, diagonal.max()+110
    for i in range(frame_count):
        # Midpoint masks at Ren's smooth entry or the supporting 12fps entry.
        q = (i+.5)/frame_count
        front = low+(high-low)*curve(q, 'in-out-sine')
        original_mask = np.clip((front-diagonal-22)/8, 0, 1)
        base = np.array(silhouette, dtype=np.float32)
        original = np.array(image, dtype=np.float32)
        base = base*(1-original_mask[..., None])+original*original_mask[..., None]
        band = np.clip(1-np.abs(diagonal-front)/80,0,1)
        white = np.clip(1-np.abs(diagonal-front)/22,0,1)
        # White core, saturated character-colour shoulder, clipped to alpha.
        band_rgb = np.array(color)*(1-white[...,None])+np.array([255,255,248])*white[...,None]
        coverage = band[...,None]*(np.array(alpha)[...,None]/255)
        base[...,:3] = base[...,:3]*(1-coverage)+band_rgb*coverage
        a = round(sweep_start+(finish-sweep_start)*i/frame_count)
        b = round(sweep_start+(finish-sweep_start)*(i+1)/frame_count)
        tracked(emit(f'{name}-wipe-{i:02d}.png', Image.fromarray(np.uint8(np.clip(base,0,255)))),
                x,y,start=a,end=b)
    # Small colour sparks travel with the scene, below the lyric layer.
    rng = np.random.default_rng(sum(map(ord,name)))
    for kind in ['spark','star']:
        particle = Image.new('RGBA',(40,40))
        pen=ImageDraw.Draw(particle)
        if kind=='spark': pen.ellipse((15,15,25,25),fill=(*color,255))
        else: pen.polygon([(20,2),(24,16),(38,20),(24,24),(20,38),(16,24),(2,20),(16,16)],fill=(255,255,240,255))
        emit(f'{name}-reveal-{kind}.png',particle)
    for i in range(12):
        ident=sprite(f'{name}-reveal-'+('star' if i%4==0 else 'spark')+'.png')
        start=sweep_start+round(i*(finish-sweep_start-150)/11)
        end=min(finish+40,start+190)
        px=x+float(rng.uniform(-image.width*.42,image.width*.42))
        py=y+float(rng.uniform(-image.height*.42,-image.height*.08))
        dx,dy=float(rng.uniform(-130,130)),float(rng.uniform(-100,30))
        samples=sorted(set([*range(start,end,16),end]))
        for a,b in zip(samples,samples[1:]):
            def state(t):
                q=(t-start)/(end-start); p=curve(q,'out-cubic')
                return pose(t,px+dx*p,py+dy*p,.7*(1-.65*q)), min(1,q*4)*(1-q)
            p0,a0=state(a);p1,a1=state(b)
            command(ident,a,b,p0,p1,a0,a1)
    return finish


def screen_motion(file, start, end, initial, final, peak=1, mode='out-cubic'):
    ident = sprite(file)
    samples = times(start, end)
    for a, b in zip(samples, samples[1:]):
        def state(t):
            q = (t-start)/(end-start)
            p = curve(q, mode)
            value = tuple(x+(y-x)*p for x,y in zip(initial,final))
            opacity = peak*min(1,q*5)*min(1,(1-q)*4)
            return value, opacity
        p0, a0 = state(a)
        p1, a1 = state(b)
        if a >= MOTTO: p1, a1 = p0, a0
        command(ident,a,b,p0,p1,a0,a1)
    return ident


def decorations(onset, center, radius=150, count=4):
    # Screen-space punctuation clusters around the words, clear of faces.
    for index in range(count):
        angle = math.radians(35+index*97)
        distance = radius*(.80+.12*(index%3))
        x, y = center[0]+math.cos(angle)*distance, center[1]+math.sin(angle)*distance*.58
        filename = 'star.png' if index%2 else 'bubble.png'
        size = .27 if index%2 else .38
        start = onset+index*35
        end = min(start+480, END)
        screen_motion(filename, start, end, (x,y,size*.5,size*.5,-.15),
                      (x+math.cos(angle)*35,y-32,size,size,.20), peak=.68)


def reveal_from_center(image, filename, start, end, steps=6, x=960, y=540):
    for index in range(steps+1):
        part = image.copy()
        mask = Image.new('L', image.size)
        half = image.width/2*index/steps
        if index:
            ImageDraw.Draw(mask).rectangle((image.width/2-half,0,image.width/2+half,image.height),fill=255)
        part.putalpha(Image.fromarray(np.minimum(np.array(image.getchannel('A')),np.array(mask))))
        file = emit(f'{filename}-{index}.png',part)
        fixed(file, round(start+index*1000/12),
              end if index==steps else round(start+(index+1)*1000/12), x=x, y=y)


def bell_cutouts():
    path = GAME/'解包/其他图片/铃铛/カラーベルＥＤ恋.png'
    original = np.array(Image.open(path).convert('RGBA'))
    reference = np.array(Image.open(GAME/'解包/其他图片/铃铛/カラーベルＥＤ姫色.png').convert('RGBA'))
    # The unpacked pink highlight has lost only alpha; its original RGB is intact.
    repair = (original[250:700, 350:850, 3] == 0) & (reference[250:700, 350:850, 3] > 0)
    original[250:700, 350:850, 3][repair] = reference[250:700, 350:850, 3][repair]
    shapes = {
        'bell-blue': [(0,40),(315,40),(375,110),(475,135),(480,210),(382,270),(430,360),(400,490),(0,490)],
        'bell-ren': [(486,256),(446,289),(448,326),(410,345),(380,378),(352,446),
                     (365,532),(398,594),(453,653),(550,695),(670,686),(714,704),
                     (780,675),(805,579),(785,485),(741,408),(835,373),(850,341),
                     (827,307),(770,330),(670,285),(580,250)],
    }
    anchors={}
    for name, polygon in shapes.items():
        mask = Image.new('L', (original.shape[1], original.shape[0]))
        ImageDraw.Draw(mask).polygon(polygon, fill=255)
        data = original.copy()
        data[...,3] = np.minimum(data[...,3], np.array(mask))
        rgb=data[...,:3].astype(int)
        gold = (rgb[...,1] > rgb[...,2]+8) & (rgb[...,0] > rgb[...,1]+5)
        data[...,3][gold] = 0  # Detach the original golden cord; it is animated in XYZ below.
        if name=='bell-blue': data[...,3][rgb[...,0]>rgb[...,2]+10]=0
        count,labels,stats,_=cv2.connectedComponentsWithStats((data[...,3]>0).astype(np.uint8))
        main=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
        data[...,3][labels!=main]=0  # Remove detached neighboring-bell and cord fragments.
        image = Image.fromarray(data)
        box=image.getbbox()
        eyelet=(414,158) if name=='bell-blue' else (768,363)
        anchors[name]=[eyelet[0]-(box[0]+box[2])/2,eyelet[1]-(box[1]+box[3])/2]
        image = image.crop(box)
        padded = Image.new('RGBA', (image.width+32, image.height+32))
        padded.alpha_composite(image, (16,16))
        emit(name+'.png',glow(padded,6,.16))
    return dict(source=str(path), alpha_reference='カラーベルＥＤ姫色.png',
                alpha_repaired_pixels=int(repair.sum()), cuts=shapes,eyelet_offsets=anchors)


def intro_camera_at(q):
    retreat = ease(q)
    return 1250+8250*retreat, math.radians(-3+5*retreat), 0, -100*retreat


def project_with_camera(camera, point):
    # Same +Z-away perspective convention as scriptslibrary/Pseudo3D.Camera.
    distance,yaw,cx,cy = camera
    dx,dy,dz = point[0]-cx,point[1]-cy,point[2]+distance
    x = math.cos(yaw)*dx-math.sin(yaw)*dz
    z = math.sin(yaw)*dx+math.cos(yaw)*dz
    factor = 1150/z
    return (960+x*factor,540+dy*factor,factor,z-distance*math.cos(yaw))


ORBIT_SETTINGS = [dict(sweep=345,radius=450,outer_gain=180,height=.62,offset=-70),
                  dict(sweep=328,radius=430,outer_gain=160,height=.65,offset=50)]


def orbit_xyz(q, which):
    p=ease(q)
    cfg=ORBIT_SETTINGS[which]
    angle=(math.pi if which==0 else 0)+math.radians(cfg['sweep'])*p
    radius=115+cfg['radius']*(1-(1-p)**3)
    radius+=cfg['outer_gain']*ease(np.clip((p-.38)/.62,0,1))
    side=-1 if which==0 else 1
    initial=project_with_camera(intro_camera_at(0),(side*125,0,0))
    cx=(initial[0]-side*115)*(1-p)+(960+cfg['offset'])*p
    x,y=cx+radius*math.cos(angle),540+radius*cfg['height']*math.sin(angle)
    distance,yaw,_,cy=intro_camera_at(q)
    z=distance*math.cos(yaw)+side*125*math.sin(yaw)*(1-p)+distance*.55*math.sin(angle)+1800*p**4
    # Author a round projected arc, then unproject it into actual XYZ depth.
    # Bell scale, cloud parallax, retained trails and occlusion use that depth.
    u,v=(x-960)*z/1150,(y-540)*z/1150
    return np.array([math.cos(yaw)*u+math.sin(yaw)*z,
                     v+cy,-math.sin(yaw)*u+math.cos(yaw)*z-distance])


# Coordinate camera and circular route by screen travel, avoiding rapid bursts
# when perspective brings either bell close. The curve has no joined segments.
ORBIT_PARAMS=np.linspace(0,1,1025)
_orbit_xy=np.array([[project_with_camera(intro_camera_at(q),orbit_xyz(q,i))[:2]
                    for i in range(2)] for q in ORBIT_PARAMS])
_orbit_steps=np.sqrt((np.linalg.norm(np.diff(_orbit_xy,axis=0),axis=2)**2).mean(axis=1))
ORBIT_ARC=np.concatenate([[0],np.cumsum(_orbit_steps)])
ORBIT_ARC/=ORBIT_ARC[-1]


def intro_progress(t):
    q=np.clip((t-COLLISION)/(ORBIT_END-COLLISION),0,1)
    return float(np.interp(ease(q),ORBIT_ARC,ORBIT_PARAMS))


def intro_camera(t):
    return intro_camera_at(intro_progress(t))


def project_intro(t, point):
    return project_with_camera(intro_camera(t),point)


def bell_xyz(t, which):
    side = -1 if which==0 else 1
    if t <= COLLISION:
        p = curve(np.clip((t-REVEAL)/(COLLISION-REVEAL),0,1),'out-cubic')
        return np.array([side*(640-515*p),side*(100-100*p),side*140*(1-p)])
    return orbit_xyz(intro_progress(t),which)


def intro_alpha(t):
    return min(1,max(0,(t-REVEAL)/110))*max(0,min(1,(SKY_END-t)/(SKY_END-GATE_REVEAL)))


def depth_visibility(t, depth, front, strength=1):
    alpha=intro_alpha(t)*strength
    blend=ease(np.clip((160-depth)/320,0,1))
    # Front/back copies overlap during a depth crossing. Compensate the back
    # opacity so the opaque body does not blink darker during that handoff.
    return alpha*blend if front else alpha*(1-blend)/max(1e-6,1-alpha*blend)


def bell_billboard(t, which):
    x,y,f,_=project_intro(t,bell_xyz(t,which))
    sec=max(0,(t-COLLISION)/1000)
    recoil=math.sin(sec*28)*math.exp(-sec*7)
    yaw=.30*math.sin(sec*3+which)
    return (x,y,.67*f*math.cos(yaw),.67*f,
            math.radians((-1 if which==0 else 1)*10)+.12*recoil+.08*math.sin(sec*3))


def bell_eyelet_xyz(t, which, offsets):
    # Unproject the actual card eyelet at the bell's depth, so retained cord
    # points stay in world space after the bell and camera have moved on.
    px,py,sx,sy,roll=bell_billboard(t,which)
    ex,ey=offsets['bell-blue' if which==0 else 'bell-ren']
    u=px+math.cos(roll)*ex*sx-math.sin(roll)*ey*sy
    v=py+math.sin(roll)*ex*sx+math.cos(roll)*ey*sy
    distance,yaw,cx,cy=intro_camera(t)
    factor=project_intro(t,bell_xyz(t,which))[2]
    x,z=(u-960)/factor,1150/factor
    return np.array([math.cos(yaw)*x+math.sin(yaw)*z+cx,
                     (v-540)/factor+cy,-math.sin(yaw)*x+math.cos(yaw)*z-distance])


def build_clouds(sky):
    # Reuse the game's wispy cloud texture, with soft alpha rather than rectangles.
    boxes=[(1150,590,1780,850),(1340,390,1920,650),(200,690,1100,970)]
    for i,box in enumerate(boxes):
        patch=np.array(sky.crop(box),dtype=np.float32)
        h,w=patch.shape[:2]
        yy,xx=np.mgrid[-1:1:complex(h),-1:1:complex(w)]
        feather=np.clip((1-xx*xx-yy*yy)*3,0,1)
        whiteness=np.clip((patch[...,0]-patch[...,2]*.68-25)/48,0,1)
        patch[...,:3]=[244,250,255]
        patch[...,3]=whiteness*feather*215
        emit(f'intro-cloud-{i}.png',Image.fromarray(patch.astype(np.uint8)))
    rng=np.random.default_rng(119)
    # A broad, flattened distant bank establishes a horizon. Near wisps
    # retreat faster and reveal scattered fragments across the expanded space.
    clouds=[(np.array([x,530,1900]),2.8,.50) for x in range(-7200,7201,1800)]
    clouds += [(rng.uniform([-3500,-1450,-200],[3500,1300,1800]),
                rng.uniform(.25,1.1),rng.uniform(.24,.55)) for _ in range(25)]
    for i,(origin,size,alpha) in enumerate(clouds):
        def state(t,origin=origin,size=size,i=i):
            p=origin+np.array([(t-REVEAL)*.009,0,0])
            x,y,f,_=project_intro(t,p)
            return x,y,size*f,size*f*(.44 if i<9 else .8),0
        sampled(f'intro-cloud-{i%3}.png',REVEAL,SKY_END,state,
                lambda t,alpha=alpha:intro_alpha(t)*alpha)


def sampled(file, start, end, state, opacity=lambda t:1, cuts=()):
    ident = sprite(file)
    ts = sorted(t for t in set(list(range(start,min(end,COLLISION),8))
                +list(range(max(start,COLLISION),end,16))+[end,COLLISION,GATE_REVEAL]+list(cuts))
                if start<=t<=end)
    for a,b in zip(ts,ts[1:]):
        p0,p1=state(a),state(b)
        delta=math.atan2(math.sin(p1[4]-p0[4]),math.cos(p1[4]-p0[4]))
        p1=(*p1[:4],p0[4]+delta)
        command(ident,a,b,p0,p1,opacity(a),opacity(b))
    return ident


def build_bell_intro():
    bell_sources = bell_cutouts()
    sky = Image.open(GAME/'解包/场景/空_昼.png').convert('RGBA')
    emit('sky-day.png',sky)
    sampled('sky-day.png',REVEAL,SKY_END,
            lambda t:(960,500+40*intro_progress(t),
                      1.18-.16*intro_progress(t),
                      1.18-.16*intro_progress(t),0),intro_alpha)
    build_clouds(sky)
    # Original game petals, distributed in depth rather than one flat overlay.
    sheet = Image.open(GAME/'解包/其他图片/粒子/花びら_連番４列_fl32.png').convert('RGBA')
    for i in range(4): emit(f'intro-petal-{i}.png',sheet.crop((i*32,0,(i+1)*32,32)))
    rng = np.random.default_rng(117)
    far_rng = np.random.default_rng(118)
    for i in range(76):
        if i<28:
            origin = rng.uniform([-2600,-1400,-180],[2600,1100,1400])
            velocity = rng.uniform([20,45,-20],[100,140,20])
            size = rng.uniform(.6,1.8)
        else:
            # A broad world-space field enters from the edges during retreat.
            # Stratification keeps the far view populated across all quadrants.
            j=i-28
            origin=np.array([-11200+(j%8+.5)*2800,-6600+(j//8+.5)*2200,
                             far_rng.uniform(900,2600)])
            origin+=far_rng.uniform([-600,-420,0],[600,420,0])
            velocity=far_rng.uniform([15,35,-15],[85,110,15])
            size=far_rng.uniform(2.1,3.8)
        def state(t,origin=origin,velocity=velocity,size=size,i=i):
            sec=(t-REVEAL)/1000
            x,y,f,_=project_intro(t,origin+velocity*sec)
            return (x,y,f*size,f*size*(.45+.55*abs(math.cos(sec*2+i))),sec*.7+i)
        sampled(f'intro-petal-{i%4}.png',REVEAL,SKY_END,state,
                lambda t,i=i:intro_alpha(t)*(.48 if i<18 else .80))
    # Two layered fibers: front/back copies switch by projected depth at crossings.
    for which,tone in enumerate([(157,182,230),(247,173,193)]):
        fiber=Image.new('RGBA',(16,12))
        d=ImageDraw.Draw(fiber)
        d.rectangle((0,3,15,8),fill=(*tone,235))
        d.line((0,4,15,4),fill=(255,241,201,240),width=1)
        emit(f'intro-cord-{which}.png',fiber)
    for front in [False,True]:
        for which in range(2):
            for seg in range(128):
                born=round(REVEAL+(SKY_END-REVEAL)*seg/128)
                reached=round(REVEAL+(SKY_END-REVEAL)*(seg+1)/128)
                approach = reached <= COLLISION
                # The incoming straight tail is transient. Retaining it after
                # contact left two detached bars while the bells orbited away.
                # Split the crossing segment at contact: only the circular
                # route belongs to the persistent world-space trail.
                if born < COLLISION < reached:
                    born = COLLISION
                end = COLLISION+60 if approach else SKY_END
                a=bell_eyelet_xyz(born,which,bell_sources['eyelet_offsets'])
                def geometry(t,which=which,a=a,reached=reached):
                    b=bell_eyelet_xyz(min(t,reached),which,bell_sources['eyelet_offsets'])
                    pa=project_intro(t,a);pb=project_intro(t,b)
                    dx,dy=pb[0]-pa[0],pb[1]-pa[1]
                    return ((pa[0]+pb[0])/2,(pa[1]+pb[1])/2,(math.hypot(dx,dy)+2)/16,
                            max(.38,(pa[2]+pb[2])*.52),math.atan2(dy,dx)),(pa[3]+pb[3])/2
                sampled(f'intro-cord-{which}.png',born,end,
                        lambda t,g=geometry:g(t)[0],
                        lambda t,g=geometry,front=front,approach=approach:
                            depth_visibility(t,g(t)[1],front,.95)*
                            (np.clip((COLLISION+60-t)/60,0,1) if approach else 1),
                        cuts=(reached,COLLISION))
        for which,name in enumerate(['bell-blue.png','bell-ren.png']):
            def bell_alpha(t,which=which,front=front):
                depth=project_intro(t,bell_xyz(t,which))[3]
                distance=intro_camera(t)[0]
                air=1-.22*np.clip(depth/(distance*.65),0,1)
                return depth_visibility(t,depth,front,air)
            sampled(name,REVEAL,SKY_END,lambda t,which=which:bell_billboard(t,which),
                    bell_alpha)
    # Denser, broader wisps retain the traveled path in world space. Their
    # long axis follows the projected tangent so the cloud trail reads as a line.
    trace_count=64
    for which in range(2):
        for i in range(trace_count):
            born=round(COLLISION+80+i*(SKY_END-COLLISION-160)/(trace_count-1))
            p=bell_eyelet_xyz(born,which,bell_sources['eyelet_offsets'])
            tangent=bell_eyelet_xyz(born+24,which,bell_sources['eyelet_offsets'])
            def state(t,p=p,tangent=tangent,i=i,born=born):
                x,y,f,_=project_intro(t,p)
                nx,ny,_,_=project_intro(t,tangent)
                size=max(.035,(.24+.14*ease(min(1,(t-born)/440)))*f)
                return x,y,size,size*.74,math.atan2(ny-y,nx-x)
            sampled(f'intro-cloud-{i%3}.png',born,SKY_END,state,
                    lambda t,born=born:intro_alpha(t)*min(.78,(t-born)/160*.78))
    # Contact ring and small sparks make the collision visible without a full-screen spin.
    screen_motion('intro-inner.png',COLLISION,COLLISION+320,
                  (960,540,.24,.24,0),(960,540,.88,.88,0),peak=.78)
    decorations(COLLISION,(960,540),radius=145,count=4)
    return dict(**bell_sources,sky=str(GAME/'解包/场景/空_昼.png'),
                petals=str(GAME/'解包/其他图片/粒子/花びら_連番４列_fl32.png'),
                collision=COLLISION,end=SKY_END,orbit_end=ORBIT_END,projection=dict(focal=1150,distance=[1250,9500],yaw=[-3,2]),
                cord_segments_per_bell=128,route_shape='continuous tilted circular arcs',orbit_settings=ORBIT_SETTINGS,
                approach_cord_end=COLLISION+60,retained_cord_start=COLLISION,
                route_interpolation='analytic circle with shared projected arc-length timing',
                intro_sample_ms=16,collision_approach_sample_ms=8,depth_sine_ratio=.55,terminal_depth=1800,
                depth_layer_blend='opacity-compensated crossing over 320 world units',
                retained_world_path=True,cloud_layers=34,cloud_traces=trace_count*2,
                cloud_trail=dict(scale=[.24,.38],min_screen_scale=.035,opacity=.78,attack_ms=160,tangent_aligned=True),
                depth_switching=True,petal_count=76,far_petals=48,
                far_petal_field=dict(x=[-11200,11200],y=[-6600,6600],z=[900,2600],grid=[8,6]))


def build_center_burst():
    # Native BG Scale/Fade and Particles Move/Rotate/Fade primitives, emitted
    # through the same track reader as the scene. No rendered effect footage.
    charge, burst, finish = 55960, 56120, 56900
    emit('burst-glow.png',Image.open(MAPSET/'sb/lighting-fx/soft_glow_round.png').convert('RGBA'))
    emit('burst-star.png',Image.open(MAPSET/'sb/star-w.png').convert('RGBA'))
    ring=Image.new('RGBA',(1024,1024))
    ImageDraw.Draw(ring).ellipse((8,8,1015,1015),outline=(255,253,243,245),width=3)
    emit('burst-ring.png',ring)
    dot=Image.new('RGBA',(24,24))
    ImageDraw.Draw(dot).ellipse((5,5,18,18),fill=(255,253,243,255))
    emit('burst-dot.png',dot.filter(ImageFilter.GaussianBlur(.7)))
    # The small round light is visible on its own before any particles spawn.
    def core(t):
        if t<=burst:
            q=curve((t-charge)/(burst-charge),'out-sine')
            return (960,540,.06+.24*q,.06+.24*q,0)
        q=curve((t-burst)/340,'out-cubic')
        return (960,540,.30+1.15*q,.30+1.15*q,0)
    def core_alpha(t):
        if t<=burst: return .86*curve((t-charge)/(burst-charge),'out-sine')
        return .86*(1-(t-burst)/340)**2
    sampled('burst-glow.png',charge,burst+340,core,core_alpha,cuts=(burst,))
    # Both rings leave the same center together; different durations produce
    # visibly different expansion speeds, rather than a delayed duplicate.
    ring_durations=[440,880]
    for duration,peak in zip(ring_durations,[.76,.62]):
        start=charge;end=charge+duration;diameter=2100
        def state(t,start=start,end=end,diameter=diameter):
            q=curve((t-start)/(end-start),'out-cubic')
            size=(26+(diameter-26)*q)/1008
            return (960,540,size,size,0)
        def alpha(t,start=start,end=end,peak=peak):
            return peak*min(1,(t-start)/90)*(1-(t-start)/(end-start))**.65
        sampled('burst-ring.png',start,end,state,alpha)
    rng=np.random.default_rng(116564)
    # Stratified angles give a full radial burst without a regular spoke pattern.
    for i in range(60):
        angle=2*math.pi*(i+rng.uniform(-.38,.38))/60
        start=burst;end=finish-int(rng.integers(0,130))
        radius=rng.uniform(510,1120);origin=np.zeros(2)
        if i%10==0:
            # Keep the large sparkles visible into the slowdown instead of
            # sending them off the top/bottom before the camera settles.
            radius*=.58
            angle+=.38
        direction=np.array([math.cos(angle),math.sin(angle)])
        if i%10==0:
            file='star.png';sx=sy=rng.uniform(.85,1.25);roll=rng.uniform(-.3,.3)
        elif i%5==0:
            file='burst-star.png';sx=sy=rng.uniform(.075,.12);roll=angle
        elif i%3==0:
            file='burst-dot.png';sx=sy=rng.uniform(.35,.65);roll=0
        else:
            file='white.png';sx=rng.uniform(22,46);sy=rng.uniform(2.5,4);roll=angle
        peak=rng.uniform(.78,1)
        def state(t,start=start,end=end,radius=radius,origin=origin,direction=direction,sx=sx,sy=sy,roll=roll):
            q=(t-start)/(end-start);p=curve(q,'out-cubic')
            xy=np.array([960,540])+origin+direction*radius*p
            size=1-.58*q
            return (*xy,sx*size,sy*size,roll)
        def alpha(t,start=start,end=end,peak=peak):
            q=(t-start)/(end-start)
            return peak*min(1,(t-start)/22)*min(1,(1-q)/.52)
        sampled(file,start,end,state,alpha,cuts=(start+22,round(start+(end-start)*.48)))
    return dict(charge=charge,burst=burst,end=finish,center=[960,540],particles=60,
                rings=2,ring_durations_ms=ring_durations,synchronized_source=True,
                rendering='native sprite Scale/Move/Rotate/Fade tracks',
                star_source='sb/star-w.png (Particles.cs)',glow_source='sb/lighting-fx/soft_glow_round.png',
                order='circular light, expanding rings, radial particles; beneath lyrics')


def build_bright_ima():
    """Bright mint/gold intro, with a quiet cool edge on the white hand art."""
    lettering('今',142,'ima.png')
    styles = [('intro-inner.png',440,7,(255,208,104)),
              ('intro-outer.png',940,2,(100,213,211)),
              ('ima.png',None,None,(39,181,176))]
    for name,diameter,stroke,color in styles:
        if diameter:
            ink=Image.new('RGBA',(diameter+32,diameter+32))
            ImageDraw.Draw(ink).ellipse((16,16,diameter+15,diameter+15),outline=(*color,255),width=stroke)
        else:
            alpha=Image.open(OUT/name).convert('RGBA').getchannel('A')
            ink=Image.new('RGBA',alpha.size,(*color,255));ink.putalpha(alpha)
        edge=Image.new('RGBA',ink.size,(46,110,128,0))
        edge.putalpha(ink.getchannel('A').filter(ImageFilter.MaxFilter(3))
                      .filter(ImageFilter.GaussianBlur(1.5)).point(lambda a: round(a*.32)))
        emit(name,Image.alpha_composite(edge,ink))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    emit('black.png', Image.new('RGBA', (1, 1), (0, 0, 0, 255)))
    emit('white.png', Image.new('RGBA', (1, 1), (255, 247, 225, 255)))
    for name, diameter, stroke in [('intro-inner.png', 440, 7), ('intro-outer.png', 940, 2)]:
        image = Image.new('RGBA', (diameter+32,diameter+32))
        ImageDraw.Draw(image).ellipse((16,16,diameter+15,diameter+15),outline=(255,252,233),width=stroke)
        emit(name,image)
    bubble = Image.new('RGBA',(100,100))
    pen = ImageDraw.Draw(bubble)
    pen.ellipse((15,15,84,84),outline=(255,249,218,230),width=2)
    pen.arc((23,23,76,76),205,260,fill=(255,255,246,210),width=2)
    emit('bubble.png',bubble)
    star = Image.new('RGBA',(100,100))
    ImageDraw.Draw(star).polygon([(50,7),(58,42),(93,50),(58,58),(50,93),(42,58),(7,50),(42,42)],
                                fill=(255,246,213,240))
    emit('star.png',star)
    fixed_id = sprite('black.png')
    # The memory bridge now covers the lead-in and 今. Black backing begins
    # only when the existing bell/sky reveal takes over.
    command(fixed_id, REVEAL+110, END, (960, 540, 1920, 1080, 0))

    intro_sources = build_bell_intro()

    def group_alpha(t): return min(1,max(0,(t-GATE_REVEAL)/220))
    def lighting(t): return min(1,max(0,(t-LIGHT)/250))
    for lit in [False,True]:
        gate = warm(Image.open(GAME / '解包/场景/学校の校門前_昼.png'), True,lit=lit)
        gate = gate.filter(ImageFilter.GaussianBlur(2.8))
        arr = np.array(gate.convert('RGB'), dtype=np.float32)
        yy, xx = np.indices(arr.shape[:2], dtype=np.float32)
        light = np.exp(-(((xx-340)/1080)**2+((yy-130)/780)**2))
        arr = np.clip(arr + light[..., None]*np.array([24,22,18] if lit else [8,9,10]), 0, 255).astype(np.uint8)
        extended = cv2.copyMakeBorder(arr, 1460, 1460, 1040, 1040, cv2.BORDER_REFLECT_101)
        gate = Image.fromarray(extended).convert('RGBA')
        name='gate-light' if lit else 'gate'
        emit(name+'.png', gate)
        emit(name+'-defocus.png',gate.filter(ImageFilter.GaussianBlur(13)))
    tracked('gate.png', 960, 540,start=GATE_REVEAL,alpha=group_alpha)
    def defocus(t):
        if t < MOTTO: return 0
        if t < LIGHT: return min(.85, (t-MOTTO)/180*.85)
        return max(0, .85-(t-LIGHT)/300*.85)
    tracked('gate-defocus.png', 960, 540,start=GATE_REVEAL,alpha=lambda t:group_alpha(t)*defocus(t))
    tracked('gate-light.png',960,540,start=LIGHT,alpha=lighting)
    tracked('gate-light-defocus.png',960,540,start=LIGHT,alpha=lambda t:lighting(t)*defocus(t))

    sys.path.insert(0, str(GAME / '立绘合成器'))
    spec = importlib.util.spec_from_file_location('gate_compositor', GAME / '立绘合成器/server.py')
    composer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composer)
    composer.load_catalog()
    cast = [('雲', 'kumo', 350, 1120), ('姫色', 'hiiro', 650, 1180),
            ('かもめ', 'kamome', 1280, 1160), ('紫織', 'shiori', 1570, 1150),
            ('恋', 'ren', 960, 1400)]
    sources = []
    # Corresponding heroine bell, the other bell in each ED pair is blue.
    bell_colors = {'雲': (226,228,222), '姫色': (240,71,79),
                   'かもめ': (62,64,62), '紫織': (145,88,194), '恋': (242,139,180)}
    for character, name, x, height in cast:
        key = (character, character+'１', '0')
        info = composer.POSES[key]
        selected = []
        for group in info['groups']:
            desired = '制服' if group['name'] == '服装' else ('微笑' if character == '雲' else '平常')
            layer = next((l for l in group['layers'] if l['name'] == desired), None)
            selected.append(layer['id'] if layer else group['default'])
        image, _, missing = composer.compose(key, selected)
        if missing: raise RuntimeError((character, missing))
        image = image.resize((round(image.width*height/image.height), height), Image.Resampling.LANCZOS)
        supporting = character != '恋'
        onset = LIGHT if supporting else GATE_REVEAL
        sweep_start = SUPPORT_SWEEP_START if supporting else CHARACTER_SWEEP_START
        finish = SUPPORT_REVEAL_END if supporting else CHARACTER_REVEAL_END
        frame_count = SUPPORT_MASK_FRAMES if supporting else CHARACTER_MASK_FRAMES
        for lit in [False,True]:
            padded = Image.new('RGBA', (image.width+72, image.height+72))
            padded.alpha_composite(warm(image,lit=lit), (36, 36))
            filename=name+('-light' if lit else '')+'.png'
            artwork=glow(padded,strength=.24 if lit else .12)
            emit(filename,artwork)
            if lit == supporting:
                character_reveal(artwork,name,x,1500-height/2,bell_colors[character],
                                 onset,sweep_start,finish,frame_count)
            tracked(filename,x,1500-height/2,start=LIGHT if lit else GATE_REVEAL,
                    visible_from=finish if supporting or not lit else None,
                    alpha=lighting if lit else (lambda t:1))
        sources.append(dict(character=character, pose=key[1], layers=selected,
                            x=x, foot_y=1500, visible_height=height,
                            reveal_start=onset,reveal_sweep_start=sweep_start,
                            reveal_finish=finish,reveal_mask_frames=frame_count,
                            reveal_color=bell_colors[character],
                            bell_source=str(GAME/('解包/其他图片/铃铛/カラーベルＥＤ'+character+'.png'))))
    scene_top=len(sprites)
    center_burst = build_center_burst()

    # Reference-style concentric rings on black, then the warm scene reveal.
    screen_motion('intro-inner.png',START,REVEAL,(960,540,.78,.78,0),(960,540,1.06,1.06,0))
    screen_motion('intro-outer.png',START+25,REVEAL+100,(960,540,.75,.75,0),(960,540,1.20,1.20,0),peak=.82)
    build_bright_ima()
    screen_motion('ima.png',START+25,REVEAL,(960,557,.90,.90,0),(960,540,1.03,1.03,0))

    lettering('I Love You',212,'love.png',role='latin')
    lettering('で始まる僕らを',90,'begin.png',tracking=7)
    full=Image.open(OUT/'begin.png').convert('RGBA')
    font=ImageFont.truetype(FONT_SOURCES['japanese']['filePath'],90)
    cut=round(24+sum(font.getlength(c) for c in 'で始まる')+7*4)
    for name,left,right in [('begin-prefix',0,cut),('begin-bokura',cut,full.width)]:
        part=full.copy();mask=Image.new('L',full.size)
        ImageDraw.Draw(mask).rectangle((left,0,right-1,full.height),fill=255)
        part.putalpha(Image.fromarray(np.minimum(np.array(full.getchannel('A')),np.array(mask))))
        emit(name+'.png',part)
    tracked('love.png',440,300,start=REVEAL,end=MOTTO,local_path=LYRIC_PATHS['love'],
            alpha=lambda t:min(1,max(0,(t-REVEAL)/160)))
    tracked('begin-prefix.png',1020,975,start=54050,end=MOTTO,local_path=LYRIC_PATHS['begin'],
            alpha=lambda t:min(1,max(0,(t-54050)/120)))
    tracked('begin-bokura.png',1020,975,start=GATE_REVEAL,end=MOTTO,local_path=LYRIC_PATHS['begin'],
            alpha=lambda t:min(1,max(0,(t-GATE_REVEAL)/120)))
    decorations(REVEAL+120,(550,350),radius=240,count=3)
    decorations(54100,(1070,915),radius=240,count=3)

    lettering('もっと',170,'motto.png',role='handwriting',tracking=10)
    reveal_from_center(Image.open(OUT/'motto.png'),'motto-reveal',MOTTO,LIGHT,steps=6,y=600)
    decorations(MOTTO+83,(960,600),radius=220,count=4)

    lettering('照らしてくれよ',98,'light-lyric.png',tracking=8)
    fixed('light-lyric.png', LIGHT, END, y=820)
    decorations(LIGHT+83,(960,820),radius=430,count=4)
    border = Image.new('RGBA', (1050, 160))
    pen = ImageDraw.Draw(border)
    pen.rectangle((3,3,1046,156),fill=(64,42,26,32),outline=(255,251,226,235),width=2)
    pen.rectangle((11,11,1038,148),outline=(255,241,192,120),width=1)
    # The words arrive first; the fine frame draws outward 250ms later.
    emit('lyric-frame.png', border)
    first = len(sprites)
    reveal_from_center(border,'frame-reveal',LIGHT+250,END,steps=4,y=820)
    frames = sprites[first:]
    del sprites[first:]
    text_index = next(i for i,item in enumerate(sprites) if item[1]=='light-lyric.png')
    sprites[text_index:text_index] = frames

    # Warm white reveal and a second single flash on the final pull-back.
    for onset, duration, peak in [(GATE_REVEAL, 220, .24), (LIGHT, 250, .34)]:
        ident = sprite('white.png')
        p = (960, 540, 1920, 1080, 0)
        if onset >= MOTTO:
            for a, b in zip(times(onset, onset+duration), times(onset, onset+duration)[1:]):
                command(ident, a, b, p, a0=peak*(1-(a-onset)/duration))
        else:
            command(ident, onset, onset+duration, p, a0=peak, a1=0)
        # Flash the scenery; keep the words clear above it.
        item = sprites.pop()
        sprites.insert(scene_top, item)

    with (OUT / 'sprites.tsv').open('w', newline='', encoding='utf-8') as stream:
        csv.writer(stream, delimiter='\t').writerows(sprites)
    with (OUT / 'commands.tsv').open('w', newline='', encoding='utf-8') as stream:
        csv.writer(stream, delimiter='\t').writerows(commands)
    (OUT / 'sources.json').write_text(json.dumps(dict(
        gate=str(GAME/'解包/场景/学校の校門前_昼.png'), compositor=str(GAME/'立绘合成器/server.py'),
        cast=sources, camera_keys=KEYS,camera_curves=CAMERA_CURVES,lyric_paths=LYRIC_PATHS,
        lyric_space='screen anchors with camera-driven 32px/14px drift and 5deg tilt',
        intro_25d=intro_sources,gate_reveal=GATE_REVEAL,
        ima_palette=dict(text_rgb=[39,181,176],inner_ring_rgb=[255,208,104],
            outer_ring_rgb=[100,213,211],style='bright mint/gold with subtle cool edge'),
        center_burst=center_burst,
        character_reveal=dict(start=GATE_REVEAL,sweep_start=CHARACTER_SWEEP_START,
            finish=CHARACTER_REVEAL_END,particle_end=CHARACTER_REVEAL_END+40,
            style='solid silhouette with shadow and fine light edge; diagonal white + bell-colour wipe',
            native_mask_frames=CHARACTER_MASK_FRAMES,particles_per_character=12,
            lyric_target='Ren finishes between ら and を; others enter at 照らしてくれよ',
            supporting_cast=dict(start=LIGHT,sweep_start=SUPPORT_SWEEP_START,
                finish=SUPPORT_REVEAL_END,particle_end=SUPPORT_REVEAL_END+40,
                native_mask_frames=SUPPORT_MASK_FRAMES,hold_fps=12)),
        lighting_change=dict(start=LIGHT,end=LIGHT+250,from_grade='bright neutral daylight',to_grade='warm white highlight'),
        hold_fps=12,hold_depth_gain=HOLD_DEPTH_GAIN,
        hold_depth_range=[MOTTO,END],fonts=FONT_SOURCES,
        frame_reveal_start=LIGHT+250,
        lyrics=[['今', START+25, REVEAL], ['I Love You', REVEAL, MOTTO],
                ['で始まる', 54050, MOTTO], ['僕らを',GATE_REVEAL,MOTTO], ['もっと', MOTTO, LIGHT],
                ['照らしてくれよ', LIGHT, END]], audio='audio-balanced.mp3'),
        ensure_ascii=False, indent=2), encoding='utf-8')
    target = MAPSET / 'sb/chorus-gate'
    target.mkdir(parents=True, exist_ok=True)
    for file in OUT.iterdir():
        if file.is_file(): shutil.copy2(file, target/file.name)
    print(f'Built {len(sprites)} sprites, {len(commands)} commands; installed {target}')


def render(start=52.0, end=59.5, fps=60):
    cv2.setNumThreads(4)
    REVIEW.mkdir(parents=True, exist_ok=True)
    entries = []
    rows = np.loadtxt(OUT / 'commands.tsv', delimiter='\t')
    for line in (OUT / 'sprites.tsv').read_text(encoding='utf-8').splitlines():
        ident, file = line.split('\t')
        image = cv2.imdecode(np.fromfile(OUT/file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        track = rows[rows[:, 0] == int(ident)]
        if image.shape[0] == 1 and image.shape[1] == 1:
            image = np.tile(image, (8, 8, 1))
            track = track.copy()
            track[:, 7:11] /= 8
        a = image[..., 3:4].astype(np.float32)/255
        premult = np.concatenate([image[..., :3]*a, a], axis=2)
        entries.append((premult, track, track[:, 1].tolist()))
    path = REVIEW / 'Chorus-Z-Boost-52.0-59.5-song.mp4'
    frames = round((end-start)*fps)
    proc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', '1920x1080', '-r', str(fps), '-i', '-', '-ss', str(start),
        '-i', str(MAPSET/'audio-balanced.mp3'), '-map', '0:v', '-map', '1:a',
        '-frames:v', str(frames), '-t', str(end-start), '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)
    stills = {round((t-start)*fps): t for t in [52.7, 53.05, 53.35, 54.7, 56.4, 56.8, 57.2, 57.6, 57.85, 58.3, 59.4]}
    for n in range(frames):
        t = (start+n/fps)*1000
        frame = np.zeros((1080, 1920, 3), np.float32)
        for image, track, starts in entries:
            index = bisect.bisect_right(starts, t+1e-6)-1
            if index < 0: continue
            row = track[index]
            if t >= row[2]-1e-6: continue
            q = (t-row[1])/(row[2]-row[1])
            x, y = row[3:5]*(1-q)+row[5:7]*q
            sx, sy = row[7:9]*(1-q)+row[9:11]*q
            angle = row[11]*(1-q)+row[12]*q
            alpha = row[13]*(1-q)+row[14]*q
            if alpha < .001: continue
            c, s = math.cos(angle), math.sin(angle)
            ih, iw = image.shape[:2]
            matrix = np.array([[c*sx, -s*sy, x-c*sx*iw/2+s*sy*ih/2],
                               [s*sx, c*sy, y-s*sx*iw/2-c*sy*ih/2]], np.float32)
            # Premultiply before interpolation to keep transparent edges clean.
            corners = np.array([[0, 0, 1], [iw, 0, 1], [0, ih, 1], [iw, ih, 1]]) @ matrix.T
            x0, y0 = np.maximum(0, np.floor(corners.min(axis=0))-1).astype(int)
            x1, y1 = np.minimum([1920, 1080], np.ceil(corners.max(axis=0))+1).astype(int)
            if x1 <= x0 or y1 <= y0: continue
            matrix[:, 2] -= (x0, y0)
            warped = cv2.warpAffine(image, matrix, (x1-x0, y1-y0), flags=cv2.INTER_LINEAR)
            opacity = warped[..., 3:4]*alpha
            region = frame[y0:y1, x0:x1]
            region *= 1-opacity
            region += warped[..., :3]*alpha
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        proc.stdin.write(frame.tobytes())
        if n in stills:
            cv2.imencode('.png', frame)[1].tofile(REVIEW/f't{round(stills[n]*1000):06d}.png')
        if n % fps == 0: print(f'rendered {n}/{frames}', flush=True)
    proc.stdin.close()
    if proc.wait() != 0: raise RuntimeError('FFmpeg encode failed')
    print(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--render-only', action='store_true')
    args = parser.parse_args()
    if not args.render_only: build()
    if args.preview or args.render_only: render()
