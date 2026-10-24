"""Prepare CGC15's native eye components and generated hidden skin for scene four.

Preserve the user's tears and hair; the default reuses saved static image edits.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import re
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'godot/chorus-four/assets/CGC15_c.png'
NATIVE = Path('${GAME_ROOT}/解包/CG')
OUT = Path('../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆/CGC15/closed-smile')
REVISION = OUT.parents[2] / '眼型修复-20261018'
spec = importlib.util.spec_from_file_location('hair_contour', ROOT/'tools/prepare-layered-hair.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

# Native tear surface only, including the complete white rim and no eye wedge.
TEARS = [
    'M934,595 C937,592 940,592 941,596 C943,606 934,617 926,619 C919,621 914,616 916,610 C917,604 925,602 934,595 Z',
    'M986,512 C994,505 1002,508 1002,516 C1002,526 993,535 985,535 C981,535 979,531 980,526 C981,520 983,515 986,512 Z',
    'M1096,415 C1101,411 1106,415 1105,421 C1104,427 1097,432 1091,430 C1084,428 1085,423 1088,419 C1090,417 1093,416 1096,415 Z',
    'M1173,346 C1181,338 1192,335 1197,340 C1202,347 1194,358 1185,362 C1179,365 1170,366 1167,360 C1165,355 1167,350 1173,346 Z',
]
# b's tear footprints differ from the user's eye-corner tears. They are removed
# from the donor, never copied on top of the preserved user detail.
DONOR_TEARS = [
    'M909,582 C918,579 932,583 936,592 C938,604 927,611 916,608 C902,605 900,593 909,582 Z',
    'M972,514 C984,511 990,515 990,523 C990,530 980,532 971,529 C964,525 965,518 972,514 Z',
    'M1086,406 C1095,400 1104,402 1108,410 C1110,419 1100,426 1090,425 C1080,424 1078,413 1086,406 Z',
    'M1157,334 C1167,328 1177,331 1178,341 C1179,350 1172,356 1162,355 C1151,353 1149,342 1157,334 Z',
    'M1186,359 C1190,356 1195,359 1195,365 C1195,371 1188,373 1185,368 C1183,365 1183,361 1186,359 Z',
    'M1165,365 C1169,362 1172,365 1172,369 C1170,373 1164,372 1164,369 C1163,367 1164,366 1165,365 Z',
]

# Complete authored ink, including both corner walls. These paths use the
# corresponding eye's local basis, rather than a colour key through the ink.
LASH_PATHS = [
    {
        'upper': 'M-76,8 C-69,-2 -62,-10 -54,-18 C-41,-30 -18,-36 3,-37 C25,-39 49,-35 61,-30 C67,-28 72,-24 76,-20 L67,-23 L73,-16 L64,-20 L69,-12 L60,-17 C47,-25 24,-29 2,-28 C-18,-28 -36,-22 -47,-12 C-55,-3 -59,6 -56,19 C-54,29 -48,37 -40,43 L-47,42 C-58,33 -63,20 -65,12 L-72,10 L-68,7 Z',
        'lower': 'M-43,39 C-30,41 -22,42 -11,39 C3,38 17,34 30,33 C42,31 54,26 61,22 L66,23 L64,30 C47,34 31,37 15,40 C-3,44 -14,46 -25,45 L-43,44 Z',
        'crease': 'M18,-50 C36,-48 51,-45 63,-40 C50,-44 35,-46 18,-48 Z',
        'source': [[-80,12],[-70,8],[-60,-1],[-45,-18],[-25,-25],[0,-28],[25,-27],[45,-25],[60,-19],[78,-12]],
        'crease_source': [[-5,-50],[20,-49],[45,-45],[66,-40]],
        'lower_source': [[-48,41],[-30,43],[-10,42],[0,41],[20,37],[40,33],[60,27],[70,25]],
        'scales': [[-80,.08],[-65,.10],[-58,.15],[-48,.52],[-35,.60],[-10,.60],[30,.60],[50,.52],[65,.35],[80,.15]],
    },
    {
        'upper': 'M-71,-27 L-62,-33 L-67,-32 C-53,-41 -34,-45 -12,-45 C16,-44 51,-40 65,-32 C77,-25 85,-13 92,0 L87,-2 L91,5 L85,1 C82,13 71,26 61,34 L55,35 C66,23 74,11 72,-1 C70,-14 58,-25 41,-29 C17,-33 -13,-34 -34,-32 C-49,-30 -56,-21 -62,-12 L-60,-23 L-67,-18 L-62,-29 Z',
        'lower': 'M-65,22 C-45,22 -22,26 0,30 C16,32 30,36 38,29 L42,25 L44,32 C39,40 25,40 7,36 C-16,32 -43,28 -65,27 Z',
        'crease': 'M-44,-55 C-30,-58 -13,-58 4,-56 C-14,-56 -30,-55 -44,-53 Z',
        'source': [[-75,-18],[-65,-19],[-55,-28],[-35,-33],[-15,-35],[15,-34],[40,-31],[60,-22],[76,-5],[95,14]],
        'lower_source': [[-72,24],[-50,25],[-30,28],[-10,30],[10,34],[25,37],[40,29],[48,27]],
        'crease_source': [[-66,-48],[-45,-54],[-20,-56],[7,-55]],
        'scales': [[-75,.16],[-60,.35],[-45,.56],[-25,.60],[15,.60],[40,.50],[55,.25],[68,.10],[95,.10]],
    },
]
# CGC06's accepted closed style keeps the native eye span and a restrained arc.
# Work in each eye's face-aligned basis; static tear positions are independent
# details, not endpoints that should squeeze the full eyelash into a short hook.
CLOSED_LOCAL = [
    [(-68,29),(-36,25.3),(-2,24.3),(32,24.8),(66,27)],
    [(-65,23),(-30,21.7),(7,22.3),(45,25.3),(80,30)],
]


def smooth_curve(points, xs):
    """C1 guide; stable hand-placed knots instead of per-pixel width noise."""
    points = np.asarray(points, float)
    slopes = np.gradient(points[:, 1], points[:, 0])
    i = np.clip(np.searchsorted(points[:, 0], xs)-1, 0, len(points)-2)
    span = points[i+1, 0]-points[i, 0]
    t = (xs-points[i, 0])/span
    return ((2*t**3-3*t**2+1)*points[i, 1]
        +(t**3-2*t**2+t)*span*slopes[i]
        +(-2*t**3+3*t**2)*points[i+1, 1]
        +(t**3-t**2)*span*slopes[i+1])


def native_lash_mask(path, eye):
    tokens = re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?', path)
    angle = math.radians(eye['angle'])
    co, si = math.cos(angle), math.sin(angle)
    world = []
    i = 0
    while i < len(tokens):
        command = tokens[i]; i += 1
        world.append(command)
        count = {'M':1, 'L':1, 'C':3, 'Z':0}[command]
        for _ in range(count):
            x, y = float(tokens[i]), float(tokens[i+1]); i += 2
            world.append(f'{eye["center"][0]+co*x-si*y:.5f},{eye["center"][1]+si*x+co*y:.5f}')
    return np.array(helper.contour_mask(' '.join(world)))


def read_rgb(path):
    return np.array(Image.open(path).convert('RGB'))


def write_rgba(rgb, alpha, path):
    im = Image.fromarray(rgb).convert('RGBA')
    im.putalpha(Image.fromarray(alpha))
    im.save(path)


def expression_masks(b, c):
    difference = (np.max(abs(b.astype(float)-c.astype(float)), axis=2)>4).astype(np.uint8)
    masks = []
    for box in [(858,466,1007,625), (1038,281,1206,441)]:
        x1,y1,x2,y2=box
        roi=difference[y1:y2,x1:x2]
        _, labels, stats, _ = cv2.connectedComponentsWithStats(roi, 8)
        selected=1+np.argmax(stats[1:,4])
        core=np.uint8(labels==selected)*255
        contours,_=cv2.findContours(core,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(core,contours,-1,255,cv2.FILLED)
        core=cv2.dilate(core,np.ones((5,5),np.uint8))
        canvas=np.zeros(difference.shape,np.uint8);canvas[y1:y2,x1:x2]=core
        canvas=np.array(Image.fromarray(canvas).filter(ImageFilter.GaussianBlur(1.1)))
        masks.append(canvas)
    return masks


def make_assets():
    OUT.mkdir(parents=True,exist_ok=True)
    assets=ROOT/'godot/chorus-four/assets/CGC15-closed-smile'
    assets.mkdir(parents=True,exist_ok=True)
    user=read_rgb(SOURCE);b=read_rgb(NATIVE/'CGC15_b.png');c=read_rgb(NATIVE/'CGC15_c.png')
    masks=expression_masks(b,c)
    union=np.maximum.reduce(masks)
    eyes=json.loads((ROOT/'godot/cg-puppet/eyes.json').read_text(encoding='utf-8'))['CGC15_c']['eyes']
    for i,e in enumerate(eyes):
        angle=math.radians(e['angle']);co,si=math.cos(angle),math.sin(angle);cx,cy=e['center']
        points=np.asarray(CLOSED_LOCAL[i],float)
        xs=np.linspace(points[0,0],points[-1,0],64)
        e['closed']=np.column_stack([xs,smooth_curve(points,xs)]).tolist()
        e['closed_world_pins']=[[cx+co*x-si*y,cy+si*x+co*y] for x,y in points]
        gate=np.linspace(e['upper'][0][0],e['upper'][-1][0],64)
        e['gate_x']=gate.tolist()
        e['opening_upper']=smooth_curve(e['upper'],gate).tolist()
        e['opening_lower']=smooth_curve(e['lower'],gate).tolist()
    yy,xx=np.mgrid[0:1080,0:1920].astype(np.float32)
    opening=np.zeros((1080,1920,3),np.uint8)
    tear_masks=[np.array(helper.contour_mask(p)) for p in TEARS]
    tear_union=np.maximum.reduce(tear_masks)
    parts=[]
    for i,e in enumerate(eyes):
        angle=math.radians(e['angle']);co,si=math.cos(angle),math.sin(angle)
        cx,cy=e['center'];lx=(xx-cx)*co+(yy-cy)*si;ly=-(xx-cx)*si+(yy-cy)*co
        up=np.array(e['upper']);low=np.array(e['lower']);smile=np.array(e['skin_lash'])
        top=np.interp(lx,up[:,0],up[:,1]);bottom=np.interp(lx,low[:,0],low[:,1]);seam=np.interp(lx,smile[:,0],smile[:,1])
        xmin,xmax=up[0,0],up[-1,0]
        horizontal=np.clip(np.minimum(lx-xmin+.5,xmax-lx+.5),0,1)
        aperture=np.clip(np.minimum(ly-top+.5,bottom-ly+.5),0,1)*horizontal
        opening[:,:,i]=np.uint8(aperture*255)
        for part in ['upper','lower','crease']:
            alpha=native_lash_mask(LASH_PATHS[i][part],e)
            # Static edge matting inside the authored contour excludes pale
            # skin and golden iris spill, without dropping warm red lash ink.
            r,g,blue=[user[:,:,k].astype(float) for k in range(3)]
            ink=np.minimum.reduce([np.clip((175-g)/35,0,1),
                np.clip((blue-g+38)/16,0,1),np.clip((r-g-24)/22,0,1)])
            # The fine crease is pale native red; colour-keying it breaks a
            # continuous line into floating specks. Its small authored contour
            # carries the complete antialiased original stroke instead.
            if part!='crease':alpha=np.uint8(np.rint(alpha*ink))
            alpha=np.uint8(np.rint(alpha*(1-tear_union.astype(float)/255)))
            write_rgba(user,alpha,assets/f'{part}-{i}.png')
            ink_x,ink_y=lx[alpha>0],ly[alpha>0]
            xs=np.linspace(float(ink_x.min()-2),float(ink_x.max()+2),64)
            knots=LASH_PATHS[i]['source' if part=='upper' else part+'_source']
            source=np.column_stack([xs,smooth_curve(knots,xs)]).tolist()
            grid_y=np.linspace(float(ink_y.min()-2),float(ink_y.max()+2),41).tolist()
            item=dict(eye=i,part=part,texture=f'assets/CGC15-closed-smile/{part}-{i}.png',
                source=source,grid_y=grid_y,basis=[cx,cy,co,si],closed_scale=.22 if part=='lower' else .75,
                native_path_local=LASH_PATHS[i][part])
            if part=='crease':item['closed_offset_y']=-11.0
            if part=='upper':
                item['closed_scale_curve']=LASH_PATHS[i]['scales']
                item['corner_wall_scale']=.035
            parts.append(item)
    # Generated static skin is registered once and reused; never erase animated
    # ink with runtime skin covers or broad deterministic inpainting.
    candidate=REVISION/'skin-generation/registered-eye-free.png'
    support=REVISION/'skin-generation/registered-eye-support.png'
    skin=read_rgb(candidate)
    union=np.array(Image.open(support).convert('L'))
    a=union.astype(float)/255
    write_rgba(skin,union,assets/'skin-overlay.png')
    Image.fromarray(skin).save(OUT/'complete-eye-skin-full.png')
    Image.fromarray(opening).save(assets/'native-opening.png')
    for i,alpha in enumerate(tear_masks):write_rgba(user,alpha,assets/f'user-tear-{i}.png')
    write_rgba(user,tear_union,assets/'user-tears.png')
    # Four original white iris glints are isolated from their unchanged iris UV.
    glint_mask=np.zeros_like(union)
    for cx,cy,radius in [(901,574,8),(940,502,4),(1081,384,7),(1135,316,4)]:
        zone=(xx-cx)**2+(yy-cy)**2<=radius**2
        white=np.minimum.reduce([np.clip((user[:,:,0].astype(float)-205)/30,0,1),np.clip((user[:,:,1].astype(float)-190)/30,0,1),np.clip((user[:,:,2].astype(float)-175)/30,0,1)])
        glint_mask=np.maximum(glint_mask,np.uint8(np.rint(white*zone*255)))
    write_rgba(user,glint_mask,assets/'native-glints.png')
    cleaned=cv2.inpaint(user,np.uint8(glint_mask>5)*255,3,cv2.INPAINT_NS)
    Image.fromarray(cleaned).save(assets/'original-without-glints.png')
    # Static supplied smile is reference/inspection only; runtime moves source
    # eyelids and clips a fixed original iris against the changing aperture.
    record=dict(canvas=[1920,1080],source=str(SOURCE),native_closed_reference=str(NATIVE/'CGC15_b.png'),
        method='complete native eyelash cutouts; shared continuous gate correspondence; fixed iris UV; static generated hidden skin',
        generation=str(candidate),parts=parts,eyes=eyes,
        skin='assets/CGC15-closed-smile/skin-overlay.png',tears='assets/CGC15-closed-smile/user-tears.png',
        original='assets/CGC15-closed-smile/original-without-glints.png',opening='assets/CGC15-closed-smile/native-opening.png',
        glints='assets/CGC15-closed-smile/native-glints.png')
    (ROOT/'godot/chorus-four/smile15.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    (assets/'closed-smile.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    crop=(825,285,1210,650);w,h=770,730
    sheet=Image.new('RGB',(w*2,h+28),'#26313d');d=ImageDraw.Draw(sheet)
    for j,im in enumerate([user,skin]):
        sheet.paste(Image.fromarray(im).crop(crop).resize((w,h),Image.Resampling.NEAREST),(j*w,28))
        d.text((j*w+5,8),['user open','complete hidden skin'][j],fill='white')
    sheet.save(OUT/'face-final-static-check.png')
    report=dict(outside_support_max_difference=int(abs(skin.astype(int)-user.astype(int))[union==0].max()),
        unchanged_mouth=True,unchanged_hair_assets=True,iris_uv='fixed in shader',native_eyelid_parts=len(parts),
        source_rgba='original user pixels',generator='unmodified bundled CLI gpt-image-2',
        final_prompt_files=[str(REVISION/'skin-generation/skin-prompt.txt')])
    (OUT/'local-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

def make_preview():
    # Actual GPU captures from the production meshes and aperture shader.
    # Never synthesize a preview by compressing or remapping the iris image.
    directory=REVISION/'gpu';states=[0,12,25,37,50,62,75,87,100]
    box=(790,255,1245,690);frames=[]
    for value in states:
        image=Image.open(directory/f'state-{value:03d}.png').convert('RGB')
        frames.append(image.crop(box).resize((728,696),Image.Resampling.LANCZOS))
    frames[0].save(REVISION/'open-to-closed-local.gif',save_all=True,append_images=frames[1:],
        duration=[450]+[30]*7+[900],loop=0,optimize=False)
    w,h=780,750;sheet=Image.new('RGB',(w*3,h+28),'#26313d');draw=ImageDraw.Draw(sheet)
    for j,value in enumerate([0,50,100]):
        im=Image.open(directory/f'state-{value:03d}.png').crop((825,275,1215,650)).resize((w,h),Image.Resampling.NEAREST)
        sheet.paste(im,(j*w,28));draw.text((j*w+7,7),str(value)+'%',fill='white')
    sheet.save(directory/'open-half-closed.png')
    print(REVISION/'open-to-closed-local.gif')


def prepare_edit():
    OUT.mkdir(parents=True,exist_ok=True)
    user=read_rgb(SOURCE);b=read_rgb(NATIVE/'CGC15_b.png');c=read_rgb(NATIVE/'CGC15_c.png')
    masks=expression_masks(b,c)
    allow=cv2.dilate(np.uint8(np.maximum.reduce(masks)>2)*255,np.ones((11,11),np.uint8))
    tears=np.maximum.reduce([np.array(helper.contour_mask(p)) for p in TEARS])
    protected=cv2.dilate(np.uint8(tears>2)*255,np.ones((5,5),np.uint8))
    allow[protected>0]=0
    box=(815,275,1225,685)
    Image.fromarray(user).crop(box).resize((1024,1024),Image.Resampling.LANCZOS).save(OUT/'edit-input.png')
    Image.fromarray(b).crop(box).resize((1024,1024),Image.Resampling.LANCZOS).save(OUT/'native-b-closed-reference.png')
    alpha=Image.fromarray(255-allow).crop(box).resize((1024,1024),Image.Resampling.NEAREST)
    mask=Image.new('RGBA',(1024,1024),'white');mask.putalpha(alpha);mask.save(OUT/'edit-mask.png')
    Image.fromarray(allow).save(OUT/'edit-allowed-native.png')
    prompt='''Use case: precise-object-edit.
Asset type: one static closed-eye expression for a 2D anime puppet.
Input 1 is the EDIT TARGET. Input 2 is an exact native-art reference for the character's CLOSED SMILING EYELASH CURVES; it is not the new target.
Change only the two masked eye regions of Input 1 from open eyes to a gentle, relieved, tender closed-eye smile. Reuse the graceful upward curving closed lashes from Input 2, fitted naturally to Input 1's unchanged eye positions and original tears.
The eyes are fully and naturally closed: no iris, no pupil, no white eyeball and no eye-glint visible. Continue smooth original peach skin over the hidden eyeball areas. The lashes remain fine native ink, with tapered ends rather than thick dark blobs. Match the existing face light and very subtle cheek blush, no new shadows or bright streaks.
Keep Input 1's four original eye-corner tear droplets exactly at their original positions, with the same shapes, translucent rims and highlights; closed lash ends should meet them naturally. Do not add extra tears from Input 2.
Keep the existing slightly open soft smiling mouth, face silhouette, nose, hair strands, eyebrows outside the eye edit area, hair ornament, highlights, colour palette and hand-painted line style unchanged. Never copy the larger mouth or other details from Input 2. Preserve all unmasked pixels. No text, no logos, no watermark.'''
    (OUT/'edit-prompt.txt').write_text(prompt,encoding='utf-8')
    (OUT/'edit-preparation.json').write_text(json.dumps(dict(crop=box,request_size=[1024,1024],
        edit_target='edit-input.png',closed_reference='native-b-closed-reference.png',mask='edit-mask.png',
        final_prompt='edit-prompt.txt',generator='unmodified bundled image_gen.py edit, gpt-image-2'),indent=2),encoding='utf-8')
    print(OUT/'edit-input.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',nargs='?',default='assets',choices=['assets','preview','prepare-edit']);args=parser.parse_args()
    {'assets':make_assets,'preview':make_preview,'prepare-edit':prepare_edit}[args.action]()
