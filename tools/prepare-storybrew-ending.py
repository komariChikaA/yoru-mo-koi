"""Prepare individual masked cards and filtered panels for native Storybrew tracks.

No full information-page movie/frames are generated. The retained 3D cinematic
is the only full-frame sequence; all page transforms/visibility belong to C#.
"""
from pathlib import Path
import argparse, json, math, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'godot/chorus-five'
SETTINGS=json.loads((PROJECT/'ending.json').read_text(encoding='utf8'))
PORTRAITS=json.loads((PROJECT/'assets/ending/portraits.json').read_text(encoding='utf8'))
MEDIA=Path('../../工作文件夹/output/CGC16_scene5')
DEFAULT_MAPSET=Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
R=114.0
SIZE=272
SS=2
CARD_ANGLE_STEP=.25

def soft(p):
    p=np.clip(p,0,1)
    return p*p*p*(p*(p*6-15)+10)

def colour(hexcode):return np.array([int(hexcode[i:i+2],16)/255 for i in (0,2,4)],np.float32)

def portrait_field(row,ink,size,uv,sampling=SS):
    image=Image.open(PROJECT/row['texture'].removeprefix('res://')).convert('RGBA')
    factor=size*sampling/image.width
    canvas=Image.new('RGBA',(SIZE*sampling,SIZE*sampling),'white')
    scaled=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.LANCZOS)
    origin=(round(SIZE*sampling/2-size*sampling*uv[0]),round(SIZE*sampling/2-size*sampling*uv[1]))
    canvas.alpha_composite(scaled,origin)
    rgb=np.asarray(canvas,dtype=np.float32)[:,:,:3]/255
    lum=rgb@np.array([.2126,.7152,.0722],np.float32)
    pale=ink+(1-ink)*.72
    blend=soft((lum-.60)/.02)[...,None]
    plate=ink+(pale-ink)*blend
    white=soft((lum-.77)/.02)[...,None]
    return plate+(1-plate)*white

def card_image(plate,ink,angle,curved=1.0,actual_radius=R,outline=False,output_factor=1):
    sampling=plate.shape[0]/SIZE
    q=(np.arange(plate.shape[0],dtype=np.float32)+.5)/sampling-SIZE/2
    x,y=np.meshgrid(q,q)
    ca,sa=math.cos(angle),math.sin(angle)
    lx=(ca*x+sa*y)/R/.78
    ly=(-sa*x+ca*y)/R
    dist=np.full_like(x,-10)
    for j in range(3):
        a=math.pi/2+j*math.tau/3
        dist=np.maximum(dist,np.sqrt((lx-math.cos(a))**2+(ly-math.sin(a))**2)-math.sqrt(3))
    dist*=R*.78
    if curved<1:
        # Fixed camera at the end of the live CG, 8.2 source metres high.
        rect=np.maximum(np.abs(x+.00731707317*R)-.8231707317*R,
                        np.abs(y+.03658536585*R)-.6219512195*R)
        dist=rect+(dist-rect)*curved
    aa=R/actual_radius*.8
    coverage=1-soft((dist+aa)/(2*aa))
    if outline:
        coverage=1-soft((np.abs(dist)-.6*R/actual_radius)/(.9*R/actual_radius))
        rgb=np.broadcast_to(ink,plate.shape)
    else:
        rim=soft((dist+4.2*R/actual_radius)/(1.2*R/actual_radius))[...,None]
        rgb=plate+(ink-plate)*rim
    pixels=np.concatenate([np.clip(rgb,0,1),coverage[...,None]],axis=2)
    return Image.fromarray(np.uint8(np.clip(pixels,0,1)*255+.5),'RGBA').resize((SIZE*output_factor,SIZE*output_factor),Image.Resampling.LANCZOS)

def cards(out,morph_only=False,regular_only=False):
    for i,row in ([] if morph_only else enumerate(PORTRAITS)):
        ink=colour(SETTINGS['palette'][i])
        ratio=190/row['card_face_ratio']*.4/R
        plate=portrait_field(row,ink,ratio*R,row['card_face_uv'])
        def prepare_angle(index):
            card_image(plate,ink,math.radians(index*CARD_ANGLE_STEP)).save(out/f'card-fine-{i}-{index:04}.png')
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(prepare_angle,range(round(360/CARD_ANGLE_STEP))))
        print('Prepared upright masked portrait '+row['name'],flush=True)
    if regular_only:return
    row=PORTRAITS[0];ink=colour(SETTINGS['palette'][0])
    live_size=600*1080/820
    for i in range(101):
        p=i/100;t=SETTINGS['transfer_start']+p*(SETTINGS['transfer_end']-SETTINGS['transfer_start'])
        k=float(soft(p));scale=1+(.4-1)*k
        radius=(360+(285-360)*k)*scale
        size=(live_size+(570-live_size)*k)*scale
        uv=np.array(row['face_uv'])+(np.array(row['card_face_uv'])-row['face_uv'])*k
        curved=float(soft((t-SETTINGS['morph_start'])/(SETTINGS['morph_end']-SETTINGS['morph_start'])))
        plate=portrait_field(row,ink,size/radius*R,uv,SS*3)
        card_image(plate,ink,-math.pi/2,curved,radius,output_factor=3).save(out/f'morph-{i:03}.png')
        card_image(plate,ink,-math.pi/2,curved,radius,True,3).save(out/f'echo-{i:03}.png')

def paper(out):
    x,y=np.meshgrid(np.arange(1920,dtype=np.float32)+.5,np.arange(1080,dtype=np.float32)+.5)
    gx=(x+y)*.707107;gy=(-x+y)*.707107
    dots=1-soft((np.hypot(gx%26-13,gy%26-13)-.35)/.6)
    mx=(x+np.floor(y/235)*83)%305-152.5;my=y%235-117.5
    petals=6+2*np.cos(np.arctan2(my,mx)*5)
    flower=1-soft((np.hypot(mx,my)-petals+.7)/1.4)
    base=np.array([1,.997,.989]);accent=np.array([.95,.72,.77])
    rgb=base+(accent-base)*(dots*.055+flower*.045)[...,None]
    Image.fromarray(np.uint8(rgb*255+.5)).save(out/'paper.png')
    Image.new('RGBA',(1,1),'white').save(out/'pixel.png')

def scene_filtered(image,blur):
    original=np.asarray(image,dtype=np.float32)/255
    soft_image=np.asarray(image.filter(ImageFilter.GaussianBlur(8+32*blur)),dtype=np.float32)/255
    a=original+(soft_image-original)*(.78+.22*blur)
    a*=1.15*np.array([1.04275,1.01235,.95725],np.float32)
    a+=np.array([.012,.007,.001],np.float32)*.95
    bright=np.maximum(np.asarray(image.filter(ImageFilter.GaussianBlur(24+20*blur)),dtype=np.float32)/255-.55,0)
    a+=bright*.72
    h,w=a.shape[:2]
    xx,yy=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h))
    sunlight=np.exp(-(((xx-.12)*.8)**2+(yy-.02)**2)*3.2)*.070*.95
    a=a+(np.array([1,.985,.95])-a)*sunlight[...,None]
    a=a+(np.array([1,.985,.97])-a)*(.045*.95)
    edge=soft((np.hypot((xx-.5)*1.1,yy-.5)-.36)/.4)*.025
    return Image.fromarray(np.uint8(np.clip(a*(1-edge[...,None]),0,1)*255+.5))

def panel(image,mask):
    result=ImageOps.fit(image,(1050,650),method=Image.Resampling.LANCZOS).convert('RGBA')
    result.putalpha(mask)
    return result

def scenes(out):
    # Only the panel's filter/mask is rasterized; its placement and timing are SB.
    sources=[Image.open(PROJECT/f'assets/ending/memory-{i}.png').convert('RGB') for i in range(3)]
    mask=Image.new('L',(2100,1300));ImageDraw.Draw(mask).rounded_rectangle((0,0,2099,1299),radius=68,fill=255)
    mask=mask.resize((1050,650),Image.Resampling.LANCZOS)
    focused=[panel(scene_filtered(s,0),mask) for s in sources]
    for i,img in enumerate(focused):img.save(out/f'scene-{i}.png')
    xx,yy=np.meshgrid((np.arange(1050)+.5)/1050,(np.arange(650)+.5)/650)
    sweep=(xx+.30*yy)/1.30
    for i in range(31):
        p=i/30;k=p**3*(35-p*(105-p*(126-p*(70-15*p))))
        alpha=(1-soft((sweep-(k*1.04-.02)+.006)/.012))*np.asarray(mask)/255
        img=focused[0].copy();img.putalpha(Image.fromarray(np.uint8(alpha*255+.5)))
        img.save(out/f'scene-enter-{i:02}.png')
    cache={}
    for pair in range(3):
        for i in range(31):
            p=float(soft(i/30));blur=math.sin(p*math.pi)
            for n in [pair,(pair+1)%3]:
                if (n,i) not in cache:cache[n,i]=scene_filtered(sources[n],blur)
            img=Image.blend(cache[pair,i],cache[(pair+1)%3,i],p)
            panel(img,mask).save(out/f'scene-swap-{pair}-{i:02}.png')
        print('Prepared filtered scene transition '+str(pair),flush=True)
    border=Image.new('RGBA',(2108,1308));d=ImageDraw.Draw(border)
    d.rounded_rectangle((3,3,2104,1304),radius=72,outline=(206,170,176,125),width=3)
    border.resize((1054,654),Image.Resampling.LANCZOS).save(out/'scene-border.png')

def footer(out):
    font=Path('C:/Windows/Fonts/YuGothR.ttc')
    if not font.exists():font=Path('C:/Windows/Fonts/msyh.ttc')
    rows=[('TOOLS','Storybrew  ·  Godot',27,500),('GAME',SETTINGS['game_title'],29,500),('MAD',SETTINGS['work_title'],31,480)]
    manifest=[]
    for i,(label,text,size,width) in enumerate(rows):
        canvas=Image.new('RGBA',(width*2,180));d=ImageDraw.Draw(canvas)
        for title,y,fs,c in [(label,0,16,'#b59b9e'),(text,33,size,'#796468')]:
            d.text((0,y*2),title,font=ImageFont.truetype(str(font),fs*2),fill=c,anchor='lt')
        canvas=canvas.resize((width,90),Image.Resampling.LANCZOS)
        canvas.save(out/f'footer-{i}.png')
        for j in range(0,width,16):
            piece=canvas.crop((j,0,min(j+16,width),90))
            if not piece.getchannel('A').getbbox():continue
            filename=f'footer-{i}-{j:03}.png';piece.save(out/filename)
            manifest.append(f'{i}\t{j}\t{piece.width}\t{width}\t{filename}')
    (out/'footer.tsv').write_text('\n'.join(manifest)+'\n',encoding='utf8')

def cinematic(out):
    target=out/'cinematic';target.mkdir(exist_ok=True)
    source=MEDIA/'第五分镜至结尾-78.000-111.622-三连起音重打点.mp4'
    end=SETTINGS['capture_end'];start=79.1
    count=math.ceil((end-start)*24)
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start-78),'-i',str(source),'-vf','fps=24,scale=960:540:flags=lanczos','-frames:v',str(count),str(target/'frame-%04d.jpg')],check=True)
    records=[]
    for i in range(count):
        records.append(f'cinematic/frame-{i+1:04}.jpg\t{(start+i/24)*1000:.6f}\t{min(end,start+(i+1)/24)*1000:.6f}')
    (out/'cinematic.tsv').write_text('\n'.join(records)+'\n',encoding='utf8')

def titles(out):
    # Render the fixed code-native title art, including the current subtitle,
    # instead of copying old movie captures with stale lettering baked in.
    godot=Path('D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe')
    # The exporter loads imported textures. Refresh modified glyph PNGs first;
    # running a script alone can otherwise keep their previous cached masks.
    subprocess.run([str(godot),'--headless','--editor','--import','--path',str(PROJECT)],check=True)
    subprocess.run([str(godot),'--path',str(PROJECT),'--script',
        'res://export-ending-titles.gd','--','--out='+str(out)],check=True)
    shutil.copy2(PROJECT/'assets/ending-title/feng-logo.png',out/'feng.png')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapset',type=Path,default=DEFAULT_MAPSET)
    parser.add_argument('--only',choices=['cards','regular-cards','morph','scenes','footer','cinematic','titles','all'],default='all')
    args=parser.parse_args();out=args.mapset/'sb/ending';out.mkdir(parents=True,exist_ok=True)
    if args.only=='morph':cards(out,True)
    if args.only=='regular-cards':cards(out,regular_only=True)
    for name,fn in [('cards',cards),('scenes',scenes),('footer',footer),('cinematic',cinematic),('titles',titles)]:
        if args.only in ('all',name):fn(out)
    paper(out)
    (out/'sources.json').write_text(json.dumps(dict(backend='Storybrew native sprites',
        settings=str(PROJECT/'ending.json'),portraits=PORTRAITS,card_angle_step_degrees=CARD_ANGLE_STEP,
        face_rotation_degrees=0,cinematic_end=SETTINGS['capture_end'],
        page_full_frame_sequence=False,filter_panel_sequence=True,
        title_source=str(PROJECT/'ending-title.gd'),title_subtitle=SETTINGS['game_title']),ensure_ascii=False,indent=2),encoding='utf8')
    print('Ready: '+str(out),flush=True)

if __name__=='__main__':main()
