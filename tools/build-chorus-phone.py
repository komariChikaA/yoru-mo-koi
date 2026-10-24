"""Prepare selected CC0 room models, local game-derived assets and Storybrew frames."""
from pathlib import Path
import argparse
import bisect
import io
import json
import math
import re
import shutil
import subprocess
import zipfile

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('${GAME_ROOT}/解包')
ASSETS = ROOT / 'godot/chorus-phone/assets'
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
REVIEW = ROOT / '_preview/chorus-photo-phone'
MODEL_PAGE = 'https://dawn-to-dusk-games.itch.io/simple-3d-bedroom-asset-pack-set-1'
PHONE_PAGE = 'https://poly.pizza/m/4DRZmTs3jq'
PHONE_MODEL = 'https://static.poly.pizza/68a8586b-e540-431c-b42e-e3c6bc691e11.glb'
MODELS = ('Bed_01', 'Table_01', 'Chair_03', 'Cupboard_01')
PHOTO_CGS = (
    ('hiiro-01', '姫色', 'CGA01_a.png'),
    ('hiiro-02', '姫色', 'CGA02_a.png'),
    ('hiiro-03', '姫色', 'CGA03_a.png'),
    ('hiiro-04', '姫色', 'CGA04.png'),
    ('hiiro-05', '姫色', 'CGA05.png'),
    ('hiiro-06', '姫色', 'CGA06_a.png'),
    ('shiori-01', '紫織', 'CGB02_a.png'),
    ('shiori-02', '紫織', 'CGB03.png'),
    ('shiori-03', '紫織', 'CGB04.png'),
    ('kumo-01', '雲', 'CGD01_a.png'),
    ('kumo-02', '雲', 'CGD02_a.png'),
    ('kumo-03', '雲', 'CGD04_a.png'),
    ('kumo-04', '雲', 'CGD05_a.png'),
    ('kamome-01', 'かもめ', 'CGE01_a.png'),
    ('kamome-02', 'かもめ', 'CGE02_a.png'),
    ('kamome-03', 'かもめ', 'CGE03_a.png'),
    ('kamome-04', 'かもめ', 'CGE04_a.png'),
)


def download_models():
    # The author's public, zero-price download flow; no account or credentials.
    session = requests.Session()
    def csrf(html):
        return re.search(r'name="csrf_token" value="([^"]+)', html).group(1)
    html = session.get(MODEL_PAGE, timeout=30).text
    result = session.post(MODEL_PAGE + '/download_url',
        data={'csrf_token': csrf(html)}, headers={'Referer': MODEL_PAGE}, timeout=30)
    result.raise_for_status()
    html = session.get(result.json()['url'], timeout=30).text
    result = session.post(MODEL_PAGE + '/file/13871418?source=game_download',
        data={'csrf_token': csrf(html)}, headers={'Referer': MODEL_PAGE}, timeout=30)
    result.raise_for_status()
    response = session.get(result.json()['url'], timeout=60)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    selected = [f'FBX/Furniture/{name}.fbx' for name in MODELS]
    selected.append('Textures/Bedroom_Set_01_Furniture.png')
    for name in selected:
        target = ASSETS / 'bedroom-kit' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(name))
    print('Downloaded selected bedroom meshes and original CC0 atlas')


def prepare_public_phone():
    # Public CC0 model. Preserve the original geometry; recolor its existing palette.
    import struct
    folder = ASSETS/'public-smartphone'
    folder.mkdir(exist_ok=True)
    path = folder/'smartphone.glb'
    if not path.exists():
        response = requests.get(PHONE_MODEL,timeout=45)
        response.raise_for_status()
        path.write_bytes(response.content)
    raw = path.read_bytes()
    length = struct.unpack_from('<I',raw,12)[0]
    doc = json.loads(raw[20:20+length])
    view = doc['bufferViews'][doc['images'][0]['bufferView']]
    offset = 28+length+view.get('byteOffset',0)
    palette = Image.open(io.BytesIO(raw[offset:offset+view['byteLength']])).convert('RGBA')
    colors = np.asarray(palette).copy()
    original = colors[:,:,:3].copy()
    colors[:,:,:3][np.all(original == [19,19,19],axis=2)] = [247,238,227]
    colors[:,:,:3][np.all(original == [26,25,50],axis=2)] = [155,129,166]
    Image.fromarray(colors).save(folder/'reference-colors.png')
    (folder/'LICENSE.txt').write_text('Smartphone by smallbigsquare\nSource: '+PHONE_PAGE+'\nDownload: '+PHONE_MODEL+'\nLicense: CC0 1.0 Universal\nhttps://creativecommons.org/publicdomain/zero/1.0/\nAdaptation: cream front and lavender casing palette; original geometry retained.\n',encoding='utf-8')


def prepare_call_screen():
    # Recompose the supplied portrait into a warm, spacious calling interface.
    width,height,ss = 618,1195,2
    top,bottom = np.array([255,248,240]),np.array([241,232,245])
    q = np.linspace(0,1,height*ss)[:,None,None]
    gradient = np.broadcast_to(top*(1-q)+bottom*q,(height*ss,width*ss,3)).astype('uint8')
    screen = Image.fromarray(gradient)
    draw = ImageDraw.Draw(screen)
    ink = '#665071'
    muted = '#9b819f'
    def coords(values): return tuple(round(v*ss) for v in values)
    def ellipse(bounds,**kwargs): draw.ellipse(coords(bounds),**kwargs)
    def line(points,fill=ink,width=4): draw.line([coords(v) for v in points],fill=fill,width=width*ss,joint='curve')
    def text(x,y,value,size,color=ink,bold=False,anchor='mm'):
        font = ImageFont.truetype('C:/Windows/Fonts/meiryob.ttc' if bold else 'C:/Windows/Fonts/meiryo.ttc',size*ss)
        draw.text(coords((x,y)),value,font=font,fill=color,anchor=anchor)
    text(38,39,'10:24',25,bold=True,anchor='lm')
    text(529,39,'97%',21,anchor='rm')
    draw.rounded_rectangle(coords((546,29,581,47)),radius=4*ss,outline=ink,width=2*ss)
    draw.rectangle(coords((550,33,575,43)),fill=ink)
    draw.rectangle(coords((582,35,585,41)),fill=ink)
    for i in range(4):
        draw.rectangle(coords((417+i*8,43-5*i,422+i*8,47)),fill=ink)
    text(309,128,'通話',31,muted)
    # Source circle is preserved without stretching; larger, higher than the old screenshot layout.
    ellipse((133,201,485,553),fill='#e6d9e9')
    ellipse((145,211,473,539),fill='#fffdf9')
    portrait = Image.open(GAME/'其他图片/效果/恋発信中.png').convert('RGB').crop((784,353,1137,706))
    portrait = portrait.resize((300*ss,300*ss),Image.Resampling.LANCZOS)
    mask = Image.new('L',portrait.size)
    ImageDraw.Draw(mask).ellipse((0,0,mask.width-1,mask.height-1),fill=255)
    screen.paste(portrait,coords((159,225)),mask)
    text(309,610,'恋',66,bold=True)
    text(309,687,'発信中...',33,muted)
    for x in [295,309,323]: ellipse((x-3,732,x+3,738),fill='#c18fa1')
    centres = [124,309,494]
    for x in centres: ellipse((x-53,791,x+53,897),fill='#e5d8eb')
    # Three consistent line icons: mute, speaker and keypad.
    draw.rounded_rectangle(coords((113,817,135,854)),radius=11*ss,outline=ink,width=4*ss)
    draw.arc(coords((105,832,143,866)),0,180,fill=ink,width=4*ss)
    line([(124,866),(124,875)])
    line([(112,875),(136,875)])
    draw.polygon([coords(v) for v in [(282,835),(295,835),(311,823),(311,865),(295,853),(282,853)]],fill=ink)
    draw.arc(coords((299,824,330,864)),-65,65,fill=ink,width=4*ss)
    draw.arc(coords((299,814,342,874)),-65,65,fill=ink,width=4*ss)
    for yy in [826,844,862]:
        for xx in [476,494,512]: ellipse((xx-4,yy-4,xx+4,yy+4),fill=ink)
    for x,label in zip(centres,['ミュート','スピーカー','キーパッド']): text(x,934,label,26)
    # Fully visible independent hang-up control, rather than the source's truncated red row.
    draw.rounded_rectangle(coords((57,1033,561,1141)),radius=54*ss,fill='#d9868d')
    cx,cy = 197,1085
    line([(cx-22,cy+7),(cx-18,cy-5),(cx-10,cy-11),(cx+10,cy-11),(cx+18,cy-5),(cx+22,cy+7)],fill='white',width=6)
    draw.rounded_rectangle(coords((cx-24,cy,cx-13,cy+15)),radius=3*ss,fill='white')
    draw.rounded_rectangle(coords((cx+13,cy,cx+24,cy+15)),radius=3*ss,fill='white')
    text(342,1087,'通話終了',35,'white',bold=True)
    screen = screen.resize((width,height),Image.Resampling.LANCZOS)
    screen.save(ASSETS/'ren-call-screen.png')
    screen.save(REVIEW/'call-screen-cream-lavender.png')


def prepare_mail_screen():
    # Recompose the supplied envelope into a sending interface, matching the call UI proportions.
    width,height,ss = 618,1195,2
    q = np.linspace(0,1,height*ss)[:,None,None]
    gradient = np.broadcast_to(np.array([62,105,160])*(1-q)+np.array([35,63,100])*q,(height*ss,width*ss,3)).astype('uint8')
    screen = Image.fromarray(gradient)
    draw = ImageDraw.Draw(screen)
    def bounds(values): return tuple(round(v*ss) for v in values)
    def text(x,y,value,size,bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/meiryob.ttc' if bold else 'C:/Windows/Fonts/meiryo.ttc',size*ss)
        draw.text(bounds((x,y)),value,font=font,fill='white',anchor='mm')
    text(67,40,'10:24',25)
    text(532,40,'97%',21)
    draw.rounded_rectangle(bounds((564,29,594,47)),radius=4*ss,outline='white',width=2*ss)
    text(309,131,'メール',36)
    envelope = Image.open(GAME/'其他图片/效果/恋メール.png').convert('RGB').crop((785,353,1135,703))
    envelope = envelope.resize((326*ss,326*ss),Image.Resampling.LANCZOS)
    mask = Image.new('L',envelope.size)
    ImageDraw.Draw(mask).ellipse((0,0,mask.width-1,mask.height-1),fill=255)
    screen.paste(envelope,bounds((146,225)),mask)
    text(309,614,'恋',66,bold=True)
    text(309,711,'メールを送信中...',35)
    draw.rounded_rectangle(bounds((59,816,559,950)),radius=25*ss,fill='#244568',outline='#779cc1',width=2*ss)
    text(309,858,'宛先：恋',30)
    text(309,908,'Sending message',24)
    draw.rounded_rectangle(bounds((60,1041,558,1147)),radius=53*ss,fill='#f5f9ff')
    font = ImageFont.truetype('C:/Windows/Fonts/meiryob.ttc',35*ss)
    draw.text(bounds((309,1092)),'送信中',font=font,fill='#3e69a0',anchor='mm')
    screen = screen.resize((width,height),Image.Resampling.LANCZOS)
    screen.save(ASSETS/'ren-mail-screen.png')
    screen.save(REVIEW/'mail-screen-blue.png')


def gate_snapshot():
    """Sample the current ChorusGate tracks at the new scene's exact entry."""
    source = ROOT / 'assets/chorus-gate'
    rows = np.loadtxt(source / 'commands.tsv', delimiter='\t')
    frame = np.zeros((1080, 1920, 3), np.float32)
    for line in (source / 'sprites.tsv').read_text(encoding='utf-8').splitlines():
        ident, filename = line.split('\t')
        track = rows[rows[:, 0] == int(ident)]
        index = bisect.bisect_right(track[:, 1].tolist(), 59200.000001) - 1
        if index < 0 or 59200 >= track[index, 2]:
            continue
        row = track[index]
        q = (59200-row[1])/(row[2]-row[1])
        x, y = row[3:5]*(1-q)+row[5:7]*q
        sx, sy = row[7:9]*(1-q)+row[9:11]*q
        angle = row[11]*(1-q)+row[12]*q
        alpha = row[13]*(1-q)+row[14]*q
        if alpha < .001:
            continue
        im = cv2.imdecode(np.fromfile(source/filename, np.uint8), cv2.IMREAD_UNCHANGED)
        if im.shape[:2] == (1, 1):
            im = np.tile(im, (8, 8, 1))
            sx, sy = sx/8, sy/8
        a = im[..., 3:4].astype(np.float32)/255
        im = np.concatenate([im[..., :3]*a, a], axis=2)
        h, w = im.shape[:2]
        c, s = math.cos(angle), math.sin(angle)
        matrix = np.array([[c*sx,-s*sy,x-c*sx*w/2+s*sy*h/2],
                           [s*sx,c*sy,y-s*sx*w/2-c*sy*h/2]],np.float32)
        corners = np.array([[0,0,1],[w,0,1],[0,h,1],[w,h,1]]) @ matrix.T
        x0,y0 = np.maximum(0,np.floor(corners.min(0))-1).astype(int)
        x1,y1 = np.minimum([1920,1080],np.ceil(corners.max(0))+1).astype(int)
        if x1 <= x0 or y1 <= y0:
            continue
        matrix[:,2] -= (x0,y0)
        warped = cv2.warpAffine(im,matrix,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR)
        region = frame[y0:y1,x0:x1]
        region *= 1-warped[...,3:4]*alpha
        region += warped[...,:3]*alpha
    cv2.imencode('.png',np.clip(frame,0,255).astype(np.uint8))[1].tofile(ASSETS/'gate-snapshot.png')


def prepare_silhouette_call():
    source = ROOT/'output/imagegen/Ren-paper-cup-hand-v8.png'
    image = Image.open(source).convert('RGBA')
    patch = image
    # One coherent generated contour eliminates the old hand/cuff overlay seam.
    simple = Image.new('RGBA',image.size,'white')
    simple.putalpha(image.getchannel('A'))
    # Limit internal linework to the cup, rounded finger group, thumb and one wrist edge.
    marks = Image.new('L',image.size,0)
    ImageDraw.Draw(marks).polygon([(205,398),(278,385),(307,365),(357,356),(397,366),
                                  (414,420),(414,480),(403,504),(417,541),(416,585),
                                  (405,625),(307,610),(280,566),(258,511),(210,507),(205,460)],fill=255)
    solid = Image.new('RGB',image.size,'white')
    solid.paste(patch.convert('RGB'),mask=patch.getchannel('A'))
    quiet = Image.blend(Image.new('RGB',image.size,'white'),solid.filter(ImageFilter.MedianFilter(3)),0.70).convert('RGBA')
    quiet.putalpha(simple.getchannel('A'))
    simple = Image.composite(quiet,simple,marks.filter(ImageFilter.GaussianBlur(2)))
    detail = patch.copy()
    for name,asset in [('simple',simple),('detail',detail)]:
        asset.save(ASSETS/f'ren-paper-cup-{name}.png')
    simple.save(ASSETS/'ren-paper-cup-silhouette.png')
    simple.save(ROOT/'output/imagegen/Ren-paper-cup-final.png')
    shadow = Image.new('RGBA',image.size,(24,48,83,0))
    shadow.putalpha(simple.getchannel('A').filter(ImageFilter.GaussianBlur(5)).point(lambda a:round(a*0.60)))
    shadow.save(ASSETS/'ren-paper-cup-shadow.png')
    return {'source':str(source),'edit_target':'output/imagegen/Ren-paper-cup-before-v8.png',
            'generation':'bundled imagegen CLI masked edit; gpt-image-2; high; natural continuous wrist and plain sleeve',
            'prompt':'assets/chorus-phone/ren-paper-cup-prompt-v8.txt',
            'pose':'forward grip; grouped rounded fingers, short thumb, smooth wrist joining plain sleeve',
            'styles':{'simple':'white upper-body and hand, sparse pale-blue cup/thumb/wrist marks; no outlined cuff band',
                      'detail':'local comparison option only; selected final is simple'},
            'source_size_px':list(image.size),'cup_anchor_source_px':[249,450],
            'framing':'head to waist only; legs never included',
            'postprocess':'v8 coherent alpha, all body linework removed; isolated cup/hand marks 70 percent, median 3px; dark-blue shadow 60 percent, blur 5px, offset [20,16]px'}


def prepare_puppet_entry():
    # Reuse selected local pilot plates; originals/game-derived textures stay local.
    source = ROOT/'godot/cg-puppet/assets'
    target = ASSETS/'puppet'
    target.mkdir(exist_ok=True)
    for name in ['CGC14_a.png', 'CGC14_a-plate.png']:
        if (source/name).exists():
            shutil.copy2(source/name,target/name)
        elif not (target/name).exists():
            raise FileNotFoundError(f'Local CG puppet plate required: {source/name}')
    (target/'CGC14').mkdir(exist_ok=True)
    for name in ['weights0','weights1','weights2','weights3','eye-skin','eye-region',
                 'eye-foreground','upper-lid','lower-lid','eye-curves','eye-ink','hair-0']:
        src, dst = source/'CGC14'/f'{name}.png', target/'CGC14'/f'{name}.png'
        if src.exists():
            shutil.copy2(src,dst)
        elif not dst.exists():
            raise FileNotFoundError(f'Local CG puppet texture required: {src}')


def prepare():
    ASSETS.mkdir(parents=True,exist_ok=True)
    prepare_puppet_entry()
    REVIEW.mkdir(parents=True,exist_ok=True)
    if not (ASSETS/'bedroom-kit/FBX/Furniture/Bed_01.fbx').exists():
        download_models()
    prepare_public_phone()
    gate_snapshot()
    # Four inspected, fully clothed story CGs; rejected Ren CG omitted. Keep source artwork local.
    for actor, _, filename in PHOTO_CGS:
        im = Image.open(GAME/'CG'/filename).convert('RGB')
        ImageOps.fit(im, (1260, 709), method=Image.Resampling.LANCZOS).save(ASSETS/f'photo-{actor}.png')
    prepare_call_screen()
    prepare_mail_screen()
    silhouette_source = prepare_silhouette_call()
    Image.open(GAME/'场景/空_昼.png').save(ASSETS/'window-sky.png')
    a = np.asarray(Image.open(ASSETS/'bedroom-kit/Textures/Bedroom_Set_01_Furniture.png').convert('RGBA')).copy()
    rgb = a[:,:,:3].astype(float)/255
    brown = (rgb[:,:,0]>rgb[:,:,2]*1.25)&(rgb[:,:,0]>.3)
    blue = (rgb[:,:,2]>rgb[:,:,0]*1.1)&(rgb[:,:,2]>.15)
    dark = ~(brown|blue)
    lum = rgb.mean(2)
    for name,wood,cloth,metal in [('bed-atlas',(235,215,178),(250,236,204),(190,172,160)),
                                  ('pink-atlas',(219,171,201),(183,159,199),(188,179,204))]:
        b = a.copy()
        for mask,color in [(brown,wood),(blue,cloth),(dark,metal)]:
            remap = np.array(color)[None,None,:]*(.85+.21*lum[:,:,None])
            b[:,:,:3][mask] = np.clip(remap,0,255).astype('uint8')[mask]
        Image.fromarray(b).save(ASSETS/(name+'.png'))
    (ASSETS/'sources.json').write_text(json.dumps({
        'room_reference':str(GAME/'场景/妹の部屋_昼.png'),
        'room_models':{'author':'Dawn to Dusk Games','page':MODEL_PAGE,'license':'CC0-1.0','selected':MODELS},
        'phone':{'source':PHONE_PAGE,'download':PHONE_MODEL,'author':'smallbigsquare','license':'CC0-1.0',
                 'type':'public non-folding touchscreen smartphone model',
                 'width_m':0.068,'height_m':0.150,'depth_m':0.0098,
                 'adaptation':'Original geometry scaled uniformly; existing palette recolored cream front and lavender side/back, call screen overlaid',
                 'pose':{'type':'floating handheld, without visible hand or support',
                         'pivot_height_m':0.512,'whole_phone_tilt_degrees':30,'vertical_bob_amplitude_m':0,
                         'minimum_table_clearance_m':0.009}},
        'centre_table':{'width_m':1.40,'depth_m':0.90,'top_height_m':0.460,'rug_size_m':[1.93,1.48]},
        'room_layout':{'footprint_m':[4.8,4.8],
                       'furniture_widths_m':{'Bed_01':1.50,'Table_01':2.02,'Chair_03':0.53,'Cupboard_01':1.32},
                       'placement':'Mesh bounds centred and grounded; bed/desk/cupboard against walls',
                       'photo_camera_target':'Near phone, left 45 degrees, camera at desk height (0.837m)',
                       'details':['quilt seams','pillow','bedside drawers','desk hutch and books',
                                  'magazines','pencil holder','clock','desk lamp','drawer chest',
                                  'plant','wall pinboard','calendar','curtain ties','AC vents','rug','ceramic cup']},
        'background_photos':[{'actor':actor,'character':name,'source':str(GAME/'CG'/filename)}
                             for actor,name,filename in PHOTO_CGS],
        'photo_motion_reference':{'source':str(GAME/'视频/video/yumeiro_op.wmv'),'range_seconds':[0,10],
                                  'implementation':'One 3D paper changes both front/reverse to room at the final edge-on pass; outside the paper is plain warm colour with falling CG cards; no distant room or gate image backdrop',
                                  'flash_local_seconds':[[0,0.13],[0.14,0.31]],'cut_under_second_flash_seconds':0.23,
                                  'centre_roll_degrees':20,'centre_fall_local_seconds':[0.23,0.85],
                                  'centre_drop_m':0.70,'centre_fall_path':'Cubic Bezier bowed fall, with lateral and depth movement','centre_fall_easing':'OutCubic: faster then slower, with a small absolute movement',
                                  'spin_local_seconds':[0.70,1.90],'spin_degrees':360,'spin_easing':'Asymmetric InSine/OutSine: 28% acceleration, 72% deceleration; continuous velocity',
                                  'room_print_switch':'Last edge-on pass at 270 degrees, approx 1.42721s, so the front is room before the turn settles',
                                  'photo_focus_local_seconds':[0.25,0.70],'photo_focus_blur_px':[24,0],'photo_focus_easing':'OutCubic',
                                  'axis_ring_radius_m':0.373,'axis_ring_decor':'Single fine pale line, 32% opacity, subtle small bead and gradual reveal/fade; no ticks, stars, dashed outer ring or scale bounce',
                                  'spin_emission':'36 particles and 18 short line rays launch from the 3D paper edges, travel outward with OutQuad, fade and shrink; local birth range 0.76-1.442s','background_instances':64,'photo_window_seconds':2.55,
                                  'photo_camera_entry_local_seconds':[1.65,2.55],'photo_entry_path':'Cubic Bezier spatial path; InOutSine time easing; starts 0.25s before rotation finishes',
                                  'omitted':'Ren CGC15_c.png and CGD03.png'},
        'screen':{'source':str(GAME/'其他图片/效果/恋発信中.png'),'portrait_crop':[784,353,1137,706],
                  'adaptation':'Recomposed cream/lavender call UI: upper portrait, centred name/status, three round function keys, separate full coral hang-up button',
                  'resolution':[618,1195]},
        'phone_camera':{'orbit_radius_m':[0.50,0.22],'height_above_phone_m':[0.325,0.105],
                        'easing':'OutSine: diagonal descending right arc, moving inward toward the call phone while SMS descends',
                        'fov_degrees':[55,48],'orbit_degrees':79.38,'orbit_angle_radians':[-math.pi/4,0.60],
                        'local_seconds':[2.25,4.95],'target':'Brief room glance in the middle, then centre on the call screen near desk height; camera descends 0.22m'},
        'sms':{'source':str(GAME/'其他图片/效果/恋メール.png'),'envelope_crop':[785,353,1135,703],
               'screen':'Recomposed blue sending UI, matched to call-screen resolution 618x1195',
               'model':'Same public CC0 Smartphone, foreground true-3D render with transparency',
               'fall_local_seconds':[3.85,4.90],'easing':'0.20-second rapid Hermite entry, speed-matched to a 0.85-second OutQuad deceleration from the lower-quarter screen boundary','screen_roll_degrees':-30,
               'brake_local_seconds':4.05,'brake_lower_edge_screen_y':0.75,
               'depth_yaw_degrees':8,'depth_pitch_degrees':-4,'settle_local_seconds':[4.90,4.95],
               'coverage':'Left half, screen faces camera and handset top points upper-right',
               'silhouette_at_local_seconds':4.95,'silhouette':'Instant white phone on protagonist blue #3e69a0',
               'outgoing_visible_until_song_seconds':65.910},
        'silhouette_call':{'character':silhouette_source,'start_local_seconds':4.95,
                          'phone_outline':'screen frame, speaker and home contour appear fully at local 4.95; only envelope has drawing animation',
                          'icon_draw_local_seconds':[4.95,5.17],
                          'flight_local_seconds':[5.17,6.30],'flight_easing':'74 percent InCubic, 26 percent OutCubic; actual arrival song65.100 after front compression',
                          'envelope_to_wave_local_seconds':[5.48,5.73],'wave_shape':'two short glints, alpha 0.22, width 3px; smooth 25px/s drift and 32px/s radius growth after reception, exponential fade 0.72 per second through shot end; no freeze','motion_blur':'22 temporal samples over 22ms plus soft stroke bands; speed dependent',
                          'ripples':'8 travel emissions plus 3 reception births at local 6.22/6.34/6.46; reception lifetime 1.40s, two layers, OutSine spread to 860px and continuous fade; no time clamp',
                          'impact_local_seconds':[6.30,6.58],'impact_amplitude_px':4,'impact_easing':'sin squared; zero-speed endpoints, slow single return',
                          'camera_local_seconds':[5.28,6.58],'camera_easing':'InOutCubic follow with early catch-up; 4px sin-squared return; replaced by right whip at actual song65.400',
                          'line_width_px':10,'world_camera_pan_px':18000,'heroine_shift_screen_px':180,'message_height_above_line_px':160,'completed_song_seconds':65.98,'ambient_reception_animated_until_song_seconds':65.91},
        'timing_retime':{'local_seconds_basis':'Existing photo_print, phone_camera, sms and silhouette_call fields retain nominal phase seconds; laser_transition song seconds are actual', 'nominal_to_actual_local_knots':[[0,0],[0.70,0.70],[2.55,2.43],[3.85,3.55],[4.95,4.55]], 'after_last_knot':'actual = nominal - 0.40', 'reclaimed_seconds':{'photo':0.12,'room':0.18,'sms_drop':0.10}, 'actual_arrival_song_seconds':65.100, 'actual_silhouette_song_seconds':63.750, 'actual_laser_segment_song_seconds':[65.200,65.980]},
        'laser_transition':{'fire_song_seconds':65.200,'crossing_seconds':0.085,'core_height_px':316,'impact_shock':{'song_seconds':[65.200,65.585],'impulses_seconds':[0,0.085],'second_impulse_gain':0.25,'translation_px':[-4,3,2.5],'roll_degrees':0.05,'decay_seconds':0.10,'zoom_punch':1.0045,'beam_width_punch':1.02,'scope':'Outgoing scene only; incoming puppet CG is stable'},'plane':'Behind character, enlarged cast shadow offset100/36px clipped to beam','whip_song_seconds':[65.400,65.980],'camera_start_delay_seconds':0.05,'crossfade_song_seconds':[65.670,65.910],'whip_easing':'InCubic outgoing acceleration, OutCubic incoming settle','blur':'33-tap Gaussian-weighted horizontal shutter, peak160px','incoming_cg':'CGC14_a; existing body/hand rig, independent RGBA hair mesh and fixed-iris eyelids; blink after arrival'},
        'incoming_override':({'source':('assets/incoming-cgc06-overscan.png' if (ASSETS/'incoming-cgc06-overscan.png').exists() else 'assets/incoming-cgc06.png'),
             'content':'CGC06 closed/o right-hand camera; replaces CGC14 placeholder',
             'motion':'Shared cgc06-motion.gd; linear preroll meets matched fast entry, early smooth braking and continuous visible slow pan at 66.000',
             'landing_song_seconds':65.980,'handoff_song_seconds':66.000,
               'atmosphere':'Shared atmosphere.gd: source-space background field with character exclusion plus five sparse closeup foreground particles across hands/clothing/background; screen-fixed Eagle white frame; same song time and 65.670–65.910 reveal',
             'next_shot_song_seconds':[66.000,72.300]}
             if (ASSETS/'incoming-cgc06.png').exists() else None),
        'gate_snapshot':'Current ChorusGate sprite tracks at 59200ms',
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared local photo, room, call and SMS screen assets')


def install(style="simple"):
    movie = REVIEW/("final.avi" if style == "simple" else "final-detail.avi")
    review = REVIEW/("Chorus-Photo-Phone-59.2-66.7-song.mp4" if style == "simple" else "Chorus-Photo-Phone-detail-59.2-66.7-song.mp4")
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(movie),
        '-ss','59.2','-i',str(MAPSET/'audio-balanced.mp3'),'-map','0:v:0','-map','1:a:0',
        '-t','7.5','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',str(review)],check=True)
    if style == 'detail':
        print(review)
        return
    out = MAPSET/'sb/chorus-phone'
    out.mkdir(parents=True,exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(movie),
        '-vf','scale=960:540:flags=lanczos','-frames:v','225','-q:v','2',
        '-start_number','0',str(out/'frame-%03d.jpg')],check=True)
    lines = []
    for i in range(225):
        filename = f'frame-{i:03d}.jpg'
        with Image.open(out/filename) as im:
            if im.size != (960,540):
                raise ValueError(f'Unexpected installed size: {filename}: {im.size}')
        lines.append(f'{filename}\t{59200+i*1000/30:.6f}\t{59200+(i+1)*1000/30:.6f}')
    text = '\n'.join(lines)+'\n'
    (out/'frames.tsv').write_text(text,encoding='utf-8')
    manifests = ROOT/'assets/chorus-phone'
    manifests.mkdir(parents=True,exist_ok=True)
    (manifests/'frames.tsv').write_text(text,encoding='utf-8')
    shutil.copy2(ASSETS/'sources.json',manifests/'sources.json')
    print(f'Installed {len(lines)} frames: 59200–66700ms, 960x540, 30fps')
    print(review)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--style',choices=['simple','detail'],default='simple')
    args = parser.parse_args()
    install(args.style) if args.install else prepare()
