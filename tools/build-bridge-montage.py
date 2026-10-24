"""Direct drum cuts, blurred complete falling CG and four rescue-hand frames.

The supplied game art is unchanged. Complete hand pictures use native hard
cuts; saved image edits are never rerun by this builder. --preview renders the same tracks with the existing chorus.
"""
from pathlib import Path
import argparse
import bisect
import csv
import json
import math
import re
import shutil
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
OUT = ROOT / 'assets/bridge-montage'
BRIDGE = ROOT / 'godot/kobe-map/assets/bridge'
REVIEW = ROOT / '_preview/bridge-montage'
SIZE = (1920, 1080)
# Spectral-flux transients in audio-balanced.mp3. Eighth-note drum hits,
# rather than quarter-note beats: each sunset scene covers two actual hits.
HITS = [50530, 50739, 50939, 51153, 51348, 51547, 51762]
# These configurable defaults are stored in Bridge.cs and shared with the montage build.
CUT_NAMES = ['DrumCut1Ms', 'DrumCut2Ms', 'DrumCut3Ms', 'DrumFallCutMs']
bridge_code = (ROOT/'Bridge.cs').read_text(encoding='utf-8-sig')
CUTS = [int(re.search(r'\b'+name+r'\s*=\s*(\d+)\s*;', bridge_code).group(1)) for name in CUT_NAMES]
if not 48200 < CUTS[0] < CUTS[1] < CUTS[2] < CUTS[3] < 52200:
    raise ValueError('Bridge drum cuts must be increasing between 48200 and 52200ms')
START, FALL, REACH, GRAB, FOCUS, END = CUTS[0], CUTS[3], 52200, 52590, 52700, 53260
sprites, commands = [], []
SCRIPT = GAME/'解包/剧本/补丁scn/03_恋ルート06.ks.scn'
INTERTITLE_FONT = Path('C:/Windows/Fonts/yuminl.ttf')
# Each image/card pair shares its interval equally. With the current 521ms
# shot-entry cadence, visible cuts alternate 260/261ms through the montage.
INTERTITLES = [
    dict(start=(CUTS[0]+CUTS[1])//2, end=CUTS[1], text='居場所が、ない。',
         source_text_1based=448, kind='narration summary',
         original='わたしの居場所は、どこにもない……！'),
    dict(start=(CUTS[1]+CUTS[2])//2, end=CUTS[2], text='……地面が、ない。',
         source_text_1based=463, kind='exact narration', original='……地面が、ない。'),
    dict(start=(CUTS[2]+FALL)//2, end=FALL, text='落ちていく────',
         source_text_1based=499, kind='narration excerpt',
         original='見上げた空に、落ちていく────'),
    dict(start=(FALL+REACH)//2, end=REACH, text='つかんでくれた手。',
         source_text_1based=468, kind='narration summary',
         original='もがくように手を伸ばしたら、誰かがつかんでくれたのだ。'),
]


def save(name, image):
    image.save(OUT / name, compress_level=3)
    return name


def sprite(name):
    ident = len(sprites)
    sprites.append((ident, name))
    return ident


def command(ident, a, b, p0, p1=None, alpha=1, alpha1=None):
    p1 = p0 if p1 is None else p1
    commands.append((ident, a, b, *p0[:2], *p1[:2], *p0[2:4], *p1[2:4],
                     p0[4], p1[4], alpha, alpha if alpha1 is None else alpha1))


def smooth(q):
    return q*q*(3-2*q)


def progress(t, a, b):
    return smooth(min(1, max(0, (t-a)/(b-a))))


def track(name, a, b, pose, opacity=lambda t: 1):
    ident = sprite(name)
    times = sorted(set([a, b, *range(a, b, 16),
                        *[t for t in [REACH, GRAB, FOCUS] if a < t < b]]))
    for t0, t1 in zip(times, times[1:]):
        command(ident, t0, t1, pose(t0), pose(t1), opacity(t0), opacity(t1))
    return ident


def intertitles():
    """Native dark plates, thin Mincho and restrained moving film dust."""
    rng = np.random.default_rng(1306)
    save('intertitle-black.png', Image.new('RGBA', (2048, 1152), (7, 15, 14, 255)))
    # Actual-size grain overhangs the viewport; particles do not smear the bars.
    grain = np.zeros((1152, 2048, 4), dtype=np.uint8)
    grain[..., :3] = (170, 180, 164)
    grain[..., 3] = rng.integers(0, 12, grain.shape[:2], dtype=np.uint8)
    save('intertitle-grain.png', Image.fromarray(grain))
    dot = Image.new('RGBA', (16, 16)); pen = ImageDraw.Draw(dot)
    pen.ellipse((6, 6, 9, 9), fill=(218, 227, 209, 210))
    save('intertitle-dust.png', dot.filter(ImageFilter.GaussianBlur(.35)))
    scratch = Image.new('RGBA', (48, 24)); pen = ImageDraw.Draw(scratch)
    pen.line([(8, 17), (18, 12), (23, 13), (34, 7)], fill=(198, 208, 190, 130), width=1)
    save('intertitle-scratch.png', scratch)
    halo = Image.new('RGBA', (48, 48)); ImageDraw.Draw(halo).ellipse((18, 18, 30, 30), fill=(191, 209, 182, 45))
    save('intertitle-soft-dust.png', halo.filter(ImageFilter.GaussianBlur(5)))
    font = ImageFont.truetype(str(INTERTITLE_FONT), 48)
    for ci, card in enumerate(INTERTITLES, 1):
        a, b = card['start'], card['end']
        command(sprite('intertitle-black.png'), a, b, (960, 540, 1, 1, 0))
        command(sprite('intertitle-grain.png'), a, b, (946, 531, 1, 1, 0), (976, 546, 1, 1, 0))
        # Each card owns its particles: there are no held sprites in shot gaps.
        for i in range(100):
            x, y = rng.uniform(16, 1904), rng.uniform(118, 962)
            scale = rng.uniform(.45, 1.0)
            rotation = rng.uniform(-.7, .7)
            name = 'intertitle-dust.png'
            if i >= 80:
                name = 'intertitle-scratch.png' if i < 92 else 'intertitle-soft-dust.png'
                scale = rng.uniform(.6, 1.35)
            dx, dy = rng.uniform(-23, 23), rng.uniform(-17, 22)
            command(sprite(name), a, b, (x, y, scale, scale, rotation),
                    (x+dx, y+dy, scale, scale, rotation+.04),
                    alpha=float(rng.uniform(.3, .85)), alpha1=float(rng.uniform(.25, .75)))
        canvas = Image.new('RGBA', (1000, 150)); pen = ImageDraw.Draw(canvas)
        text = card['text']; widths = [font.getlength(ch) for ch in text]
        x = (1000-sum(widths)-3*(len(text)-1))/2
        for ch, width in zip(text, widths):
            pen.text((x, 72), ch, font=font, anchor='lm', fill=(237, 237, 225, 255))
            x += width+3
        filename = save(f'intertitle-{ci}.png', canvas)
        # Hard arrival, tiny continuous push; no animation delaying legibility.
        command(sprite(filename), a, b, (960, 577, 1, 1, 0), (960, 575, 1.006, 1.006, 0))


def colored_grip(image, source):
    """Keep the saved drawing; tint skin and paper with a light watercolor wash."""
    w, h = image.size
    # Follow the actual ink outline, so the color wash does not leave bands
    # beside fingers or wrists. This is a color mask, not puppet cutouts.
    gray = cv2.cvtColor(np.asarray(source.convert('RGB')),cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray,(3,3),.8)
    edges = cv2.Canny(gray,25,50)
    edges = cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    edges = cv2.dilate(edges,np.ones((3,3),np.uint8))
    area = (edges==0).astype('uint8')*255
    sh,sw = area.shape
    for x,y in [(int(sw*.60),int(sh*.10)),(int(sw*.06),int(sh*.74))]:
        cv2.floodFill(area,None,(x,y),100)
    _, labels, stats, _ = cv2.connectedComponentsWithStats((area!=100).astype('uint8'))
    skin_id = 1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    mask = Image.fromarray((labels==skin_id).astype('uint8')*255)
    mask = mask.resize((w,h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
    skin = np.asarray(mask, dtype=np.float32)[...,None]/255
    data = np.asarray(image.convert('RGBA'), dtype=np.float32)
    rgb = data[...,:3]; shade = np.clip((255-rgb.mean(axis=2,keepdims=True))/150,0,1)
    yy,xx = np.indices((h,w),dtype=np.float32)
    mint = np.exp(-(((xx-w*.16)/(w*.55))**2+((yy-h*.75)/(h*.65))**2))
    blue = np.exp(-(((xx-w*.91)/(w*.45))**2+((yy-h*.16)/(h*.60))**2))
    paper = np.array([255,255,252],dtype=np.float32)-shade*np.array([89,94,80])
    paper -= mint[...,None]*np.array([21,2,7])+blue[...,None]*np.array([20,13,0])
    flesh = np.array([255,226,211],dtype=np.float32)-shade*np.array([75,116,107])
    data[...,:3] = np.clip(paper*(1-skin)+flesh*skin,0,255)
    return Image.fromarray(data.astype(np.uint8))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    # Native-size opaque bars avoid filtering a one-pixel texture into a
    # transparent gradient. Overhang the frame on the outer three edges.
    save('letterbox.png', Image.new('RGBA', (2048, 128), (0, 0, 0, 255)))
    names = ['山のふもと_夕.png', '秘密基地の前_立ち入り禁止_夕.png', '崖の手前_夕.png']
    focus_layers = []
    for i, name in enumerate(names):
        scene = Image.open(GAME/'解包/场景'/name).convert('RGBA').resize(SIZE, Image.Resampling.LANCZOS)
        filename = save(f'sunset-{i+1}.png', scene.filter(ImageFilter.GaussianBlur(3.0)))
        soft = save(f'sunset-{i+1}-defocus.png', scene.filter(ImageFilter.GaussianBlur(14.0)))
        focus_layers.append((soft, CUTS[i], lambda t: (960,540,1,1,0)))
        # Shot boundaries remain hard cuts; only focus changes inside a shot.
        command(sprite(filename), CUTS[i], CUTS[i+1], (960, 540, 1, 1, 0))

    def illustration(path, radius):
        image = Image.open(path).convert('RGBA').resize(SIZE, Image.Resampling.LANCZOS)
        paper = Image.new('RGBA', SIZE, (255, 250, 235, 255))
        return Image.alpha_composite(paper, image).filter(ImageFilter.GaussianBlur(radius))

    fall_art = ROOT/'output/imagegen/CGC13-fall-memory-v1.png'
    save('CGC13-fall-memory.png', illustration(fall_art, 1.4))
    soft = save('CGC13-fall-defocus.png', illustration(fall_art, 8.0))
    def fall_pose(t):
        q = (t-FALL)/(REACH-FALL)
        z = 1.13+.23*q*q
        return (960+25*q*q, 540+95*q*q, z, z, math.radians(2+5*q*q))
    # The falling CG stays complete and separate from the hand sequence.
    track('CGC13-fall-memory.png', FALL, REACH, fall_pose)
    focus_layers.append((soft, FALL, fall_pose))

    hand_cuts = [REACH, 52330, 52460, GRAB, END]
    hand_sources = []
    for i, (a, b) in enumerate(zip(hand_cuts, hand_cuts[1:]), 1):
        path = ROOT/f'output/imagegen/Rescue-hand-cut-{i}-v1.png'
        hand_sources.append(str(path))
        filename = save(f'hand-cut-{i}.png', illustration(path, 1.6))
        if i < 4:
            command(sprite(filename), a, b, (960, 540, 1, 1, 0))
        else:
            # Hold the clear final grip into 今, with a restrained whole-frame push.
            track(filename, a, b, lambda t: (960, 540,
                  1+.02*progress(t, GRAB, END), 1+.02*progress(t, GRAB, END), 0))

    # Four short focus pulls, followed by 90ms of stable final clarity.
    # Same-pose Gaussian layers blend over the opaque clearer illustration.
    for filename, a, pose in focus_layers:
        track(filename, a, a+170, pose, lambda t, a=a: 1-progress(t,a,a+170))

    grip_source = ROOT/'output/imagegen/Rescue-hand-cut-4-v1.png'
    color = save('hand-cut-4-color.png', colored_grip(illustration(grip_source,1.6),Image.open(grip_source)))
    hand_pose = lambda t: (960,540,1+.02*progress(t,GRAB,END),1+.02*progress(t,GRAB,END),0)
    track(color, FOCUS, END, hand_pose, lambda t: progress(t,FOCUS,FOCUS+150))
    save('ima-hand-flash.png', Image.new('RGBA',(2048,1152),(255,255,243,255)))
    track('ima-hand-flash.png', FOCUS, FOCUS+160, lambda t: (960,540,1,1,0),
          lambda t: .56*(1-progress(t,FOCUS,FOCUS+160)))

    intertitles()
    # The preceding sky already has 108px bars. Continue the same bars over
    # every sunset/CG cut and underneath the unchanged 今/sky transition.
    for y in [44, 1036]:
        command(sprite('letterbox.png'), START, END, (960, y, 1, 1, 0))

    with (OUT/'sprites.tsv').open('w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter='\t').writerows(sprites)
    with (OUT/'commands.tsv').open('w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter='\t').writerows(commands)
    (OUT/'cut-times.tsv').write_text('\t'.join(map(str, CUTS))+'\n', encoding='utf-8')
    (OUT/'sources.json').write_text(json.dumps(dict(
        source_cg=str(GAME/'解包/CG/CGC13.png'),
        style_reference=str(ROOT/'output/imagegen/CGC13-memory-sunset-v1.png'),
        image_edit_mode='bundled imagegen CLI edit; gpt-image-2; high; existing custom provider',
        fall_art=str(fall_art), character_cutouts_in_sunset=False, fall_cg_segmented=False,
        backgrounds=[str(GAME/'解包/场景'/n) for n in names],
        detected_drum_hits_ms=HITS, scene_cuts_ms=CUTS, fall_ms=FALL,
        timing_source='Bridge.cs configurable defaults; even image/intertitle cadence',
        reach_ms=REACH, grip_ms=GRAB, hand_focus_ms=FOCUS, end_ms=END,
        transition='direct hard cuts, no squeeze or pulse', subtitles=False,
        intertitles=dict(script=str(SCRIPT), scene='*シナリオ',
            index_convention='1-based scenes[1].texts position in decoded PSB; not file line numbers',
            cards=INTERTITLES, font=str(INTERTITLE_FONT), font_px=48, letter_spacing_px=3,
            particle_sprites_per_card=100, treatment='near-black green, moving grain, dust and scratches',
            render='native sprite tracks; text-only cards between images'),
        letterbox=dict(start=START, end=END, top_px=108, bottom_px=108,
            texture='letterbox.png', texture_size_px=[2048, 128], scale=1,
            horizontal_overhang_px=64, outer_vertical_overhang_px=20),
        gaussian_blur_px=dict(sunsets=3.0, fall=1.4, hands=1.6),
        focus_pull=dict(sunsets_blur_px=[14.0,3.0],fall_blur_px=[8.0,1.4],
            transition_ms=170,clear_hold_ms=90,easing='smoothstep',
            rendering='same-pose native Gaussian texture layers; continuous opacity'),
        handshake=dict(whole_frames=4, cuts_ms=hand_cuts, sources=hand_sources,
            prompts=[f'hand-cut-{i}-prompt.txt' for i in range(1, 5)],
            actions=['reach', 'approach', 'contact', 'secure rescue grip'],
            segmented=False, final_push=1.02,
            color_start_ms=FOCUS,color_duration_ms=150,flash_duration_ms=160,
            treatment='saved drawing retained; peach skin and mint/sky watercolor paper'),
        audio='audio-balanced.mp3'), ensure_ascii=False, indent=2), encoding='utf-8')
    target = MAPSET/'sb/bridge-montage'; target.mkdir(parents=True, exist_ok=True)
    godot_target = ROOT/'godot/kobe-map/assets/bridge-montage'; godot_target.mkdir(parents=True, exist_ok=True)
    for p in OUT.iterdir():
        if p.is_file():
            shutil.copy2(p, target/p.name)
            shutil.copy2(p, godot_target/p.name)
    print(f'Built {len(sprites)} native sprites / {len(commands)} intervals; {target}')


def load_tracks(folder):
    rows=np.loadtxt(folder/'commands.tsv',delimiter='\t')
    entries=[]
    for line in (folder/'sprites.tsv').read_text(encoding='utf-8').splitlines():
        ident,name=line.split('\t')
        track=rows[rows[:,0]==int(ident)].copy()
        im=cv2.imdecode(np.fromfile(folder/name,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
        if im.shape[2]==3: im=cv2.cvtColor(im,cv2.COLOR_BGR2BGRA)
        if im.shape[:2]==(1,1):
            im=np.tile(im,(8,8,1));track[:,7:11]/=8
        alpha=im[...,3:4].astype('float32')/255
        entries.append((np.concatenate([im[...,:3]*alpha,alpha],axis=2),track,track[:,1].tolist()))
    return entries


def composite(frame,entries,t):
    for image,track,starts in entries:
        i=bisect.bisect_right(starts,t+1e-6)-1
        if i<0: continue
        r=track[i]
        if t>=r[2]-1e-6: continue
        q=(t-r[1])/(r[2]-r[1])
        x,y=r[3:5]*(1-q)+r[5:7]*q
        sx,sy=r[7:9]*(1-q)+r[9:11]*q
        angle=r[11]*(1-q)+r[12]*q; alpha=r[13]*(1-q)+r[14]*q
        if alpha<.001: continue
        c,s=math.cos(angle),math.sin(angle); h,w=image.shape[:2]
        matrix=np.array([[c*sx,-s*sy,x-c*sx*w/2+s*sy*h/2],
            [s*sx,c*sy,y-s*sx*w/2-c*sy*h/2]],np.float32)
        corners=np.array([[0,0,1],[w,0,1],[w,h,1],[0,h,1]])@matrix.T
        x0,y0=np.maximum(0,np.floor(corners.min(axis=0))-1).astype(int)
        x1,y1=np.minimum(SIZE,np.ceil(corners.max(axis=0))+1).astype(int)
        if x1<=x0 or y1<=y0: continue
        matrix[:,2]-=(x0,y0)
        warped=cv2.warpAffine(image,matrix,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR)
        region=frame[y0:y1,x0:x1]; region*=1-warped[...,3:4]*alpha;region+=warped[...,:3]*alpha


def montage_lyric_tracks():
    result=[]
    for line in (BRIDGE/'lyrics-motion.tsv').read_text(encoding='utf-8').splitlines():
        f=line.split('\t'); a,b=int(f[0]),int(f[1])
        if a<START: continue
        im=cv2.imdecode(np.fromfile(BRIDGE/f[2],dtype=np.uint8),cv2.IMREAD_UNCHANGED)
        alpha=im[...,3:4].astype('float32')/255
        image=np.concatenate([im[...,:3]*alpha,alpha],axis=2)
        rows=[]
        def state(t):
            leave=float(f[9]); q=max(0,(t-(b-leave))/leave) if leave else 0
            y=float(f[7])+float(f[11])*q**3;scale=1+(float(f[13])-1)*q**3
            opacity=min(1,(b-t)/int(f[4])) if int(f[4]) else 1
            return float(f[6]),y,scale,scale,0,max(0,opacity)
        ts=[*range(a,b,16),b]
        for t0,t1 in zip(ts,ts[1:]):
            p0,p1=state(t0),state(t1)
            rows.append((0,t0,t1,*p0[:2],*p1[:2],*p0[2:4],*p1[2:4],p0[4],p1[4],p0[5],p1[5]))
        rows=np.array(rows);result.append((image,rows,rows[:,1].tolist()))
    return result


def render(start=49.5,end=59.5,fps=60):
    cv2.setNumThreads(4); REVIEW.mkdir(parents=True,exist_ok=True)
    entries=load_tracks(OUT)+montage_lyric_tracks()+load_tracks(ROOT/'assets/chorus-gate')
    # The unchanged early sky and its native lyric are taken from the actual
    # Storybrew render, so the review uses the deployed effect before montage.
    path=REVIEW/'Bridge-Direct-Cuts-Hand-Frames-49.5-59.5-song.mp4'
    count=round((end-start)*fps)
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','bgr24',
        '-s','1920x1080','-r',str(fps),'-i','-','-ss',str(start),'-i',str(MAPSET/'audio-balanced.mp3'),
        '-map','0:v','-map','1:a','-frames:v',str(count),'-t',str(end-start),'-c:v','libx264',
        '-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
        '-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
    stills=[50550,51000,51450,51770,51980,52220,52400,52590,52700,52900,53100,53150,53500,55600]
    for n in range(count):
        t=(start+n/fps)*1000
        frame=np.zeros((1080,1920,3),np.float32)
        if t<START:
            # Exact cached native render at 16ms, resized for the preview.
            native=ROOT/'_preview/bridge-montage/native'/f't{49500+round((t-49500)/16)*16:06d}.png'
            if native.exists():
                frame=cv2.imdecode(np.fromfile(native,dtype=np.uint8),cv2.IMREAD_COLOR)
                frame=cv2.resize(frame,SIZE).astype(np.float32)
            else:
                raise FileNotFoundError(native)
        composite(frame,entries,t)
        frame=np.clip(frame,0,255).astype('uint8'); proc.stdin.write(frame.tobytes())
        if any(abs(t-s)<8.4 for s in stills):
            cv2.imencode('.png',frame)[1].tofile(REVIEW/f't{round(t):06d}.png')
        if n%fps==0: print(f'rendered {n}/{count}',flush=True)
    proc.stdin.close()
    if proc.wait(): raise RuntimeError('FFmpeg failed')
    print(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');parser.add_argument('--render-only',action='store_true')
    args=parser.parse_args()
    if not args.render_only: build()
    if args.preview or args.render_only: render()
