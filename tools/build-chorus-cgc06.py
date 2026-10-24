"""Prepare the clothed CGC06 third shot and install its 66.000–72.300s frames."""
from pathlib import Path
import argparse
import json
import math
import shutil
import subprocess
import cv2
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
INPUT=Path('../../工作文件夹/output/CGC06_puppet')
OUT=INPUT.parent/'CGC06_scene3'
PROJECT=ROOT/'godot/chorus-cgc06'
ASSETS=PROJECT/'assets'
MAPSET=Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
FFMPEG=Path('D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe')
FFPROBE=FFMPEG.with_name('ffprobe.exe')
PAD=(128,192)
SIZE=(1376,752)

def rgb(path):
    return np.array(Image.open(path).convert('RGB'))

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    Image.fromarray(data).save(temporary,format=Image.registered_extensions()[path.suffix.lower()])
    temporary.replace(path)

def polygon(points):
    im=Image.new('L',(SIZE[0]*4,SIZE[1]*4))
    ImageDraw.Draw(im).polygon([(x*4,y*4) for x,y in points],fill=255)
    return np.array(im.resize(SIZE,Image.Resampling.LANCZOS))

def heroine_mask(reference):
    # Trace only the heroine, including both hands and the long hair.
    main=[(1144,279),(1165,237),(1164,176),(1143,108),(1110,62),(1060,34),
      (994,24),(944,29),(880,45),(817,60),(753,80),(687,103),(624,116),
      (559,129),(496,139),(430,151),(366,151),(300,168),(232,184),(169,214),
      (111,242),(66,266),(33,284),(24,305),(33,324),(65,337),(107,340),
      (151,337),(192,329),(164,348),(133,366),(114,384),(117,400),(143,410),
      (184,408),(195,391),(189,426),(196,465),(211,497),(233,528),(216,568),
      (210,614),(207,660),(231,659),(268,629),(292,605),(318,621),(346,636),
      (370,642),(397,656),(411,653),(414,644),(401,628),(429,645),(441,646),
      (443,636),(428,615),(454,636),(468,639),(475,633),(466,617),(487,633),
      (498,631),(501,625),(491,608),(507,601),(502,590),(483,575),(515,578),
      (554,566),(598,546),(642,523),(680,501),(719,479),(755,465),(788,454),
      (816,447),(814,419),(832,406),(887,401),(946,405),(1006,410),(1028,426),
      (1064,438),(1101,441),(1128,429),(1144,405),(1138,382),(1146,350)]
    arm=[(534,719),(576,679),(624,625),(657,584),(675,552),(684,524),
      (686,502),(692,497),(700,499),(703,510),(700,531),(696,548),(717,526),
      (740,500),(747,495),(754,498),(755,505),(746,521),(734,543),(769,511),
      (783,504),(792,506),(792,514),(780,532),(765,554),(799,535),(807,535),
      (812,540),(807,548),(787,573),(776,585),(774,600),(758,622),(729,646),
      (696,665),(656,685),(613,704),(571,718),(549,723)]
    mask=np.maximum(polygon(main),polygon(arm))
    # Open blue gaps between the long hair locks remain part of the background.
    gaps=[[(63,278),(96,256),(147,229),(206,209),(166,236),(113,262),(80,281)],
          [(126,287),(182,261),(241,237),(306,215),(255,238),(190,269),(145,291)],
          [(325,185),(369,171),(415,165),(452,169),(404,174),(365,184)]]
    for gap in gaps:
        mask=np.minimum(mask,255-polygon(gap))
    # Refine the thin neutral-colored hair locks against the saturated blue
    # bedding. Keep the face/head interior solid, including the green eyes.
    r,g,b=reference.astype(np.int16).transpose(2,0,1)
    hair=np.uint8((r>b-44)&(r>g-15)&(r>55))*255
    hair[440:]=0;hair[:,1168:]=0;hair[280:,1148:]=0
    count,labels,stats,_=cv2.connectedComponentsWithStats(hair)
    # Keep only locks attached to the traced heroine, not isolated bedding or
    # the man's skin beyond the right hair edge.
    attached=np.unique(labels[mask>128])
    accepted=[i for i in attached if i and stats[i,cv2.CC_STAT_AREA]>=18]
    hair=np.uint8(np.isin(labels,accepted))*255
    mask=np.maximum(mask,hair)
    # Skin segmentation within the two hand areas preserves every finger and
    # fingernail. The masculine blue shirt is outside both skin components.
    for box,area in [((304,505,522,673),[(312,566),(385,514),(449,530),(515,586),(522,629),(472,657),(396,671),(350,645),(319,617)]),
                     ((525,487,825,730),arm)]:
        x0,y0,x1,y1=box
        skin=np.uint8((r[y0:y1,x0:x1]>g[y0:y1,x0:x1]-5)&
                      (r[y0:y1,x0:x1]>b[y0:y1,x0:x1]-45)&(r[y0:y1,x0:x1]>80))*255
        count,labels,stats,_=cv2.connectedComponentsWithStats(skin)
        component=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
        contours,_=cv2.findContours(np.uint8(labels==component)*255,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        hand=np.zeros_like(mask)
        local=np.zeros_like(skin);cv2.drawContours(local,contours,-1,255,-1)
        hand[y0:y1,x0:x1]=local
        hand=cv2.dilate(hand,np.ones((3,3),np.uint8))
        cut=cv2.dilate(polygon(area),np.ones((9,9),np.uint8))
        mask[cut>100]=0
        mask=np.maximum(mask,hand)
    return cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),2.2)

def smooth_smile(photo):
    # Replace the angular tail of the original strained smile with one relaxed
    # fine curve; keep the mouth center, face proportions and nose unchanged.
    mask=np.zeros(SIZE[::-1],np.uint8)
    path=np.array([(828,315),(828,329),(832,343),(844,351),(855,356)],np.int32)
    cv2.polylines(mask,[path],False,255,7,cv2.LINE_AA)
    clean=cv2.inpaint(photo,mask,5,cv2.INPAINT_TELEA)
    alpha=cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),.65)[...,None]
    result=np.uint8(np.round(photo*(1-alpha)+clean*alpha))
    canvas=Image.new('RGBA',(SIZE[0]*4,SIZE[1]*4))
    start=np.array([829.,320.]);c1=np.array([826.,336.]);c2=np.array([837.,350.]);end=np.array([851.,352.])
    t=np.linspace(0,1,100)[:,None]
    points=(1-t)**3*start+3*(1-t)**2*t*c1+3*(1-t)*t*t*c2+t**3*end
    ImageDraw.Draw(canvas).line([tuple(p*4) for p in points],fill=(160,106,119,185),width=4)
    ink=canvas.resize(SIZE,Image.Resampling.LANCZOS)
    return np.array(Image.alpha_composite(Image.fromarray(result).convert('RGBA'),ink).convert('RGB'))

def lighting(photo,mask):
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]].astype(np.float32)
    beam=np.exp(-(((xx-1040)/760)**2+((yy-90)/600)**2))
    face=np.exp(-(((xx-877)/165)**2+((yy-275)/160)**2))
    image=photo.astype(np.float32)/255
    # Soft blue-white upper-right key with warm skin retained on the face.
    image*=np.stack([.89+.11*mask,.92+.08*mask,.97+.03*mask],axis=2)
    gain=(.08+.24*beam)*mask*(1-.55*face)
    image=1-(1-image)*(1-gain[...,None]*np.array([.82,.9,1.]))
    nx=cv2.Sobel(mask,cv2.CV_32F,1,0,ksize=3)
    ny=cv2.Sobel(mask,cv2.CV_32F,0,1,ksize=3)
    outward=np.maximum(0,(-.6*nx+.8*ny)/(np.hypot(nx,ny)+1e-4))
    rim=np.clip(mask-cv2.GaussianBlur(mask,(0,0),3),0,1)*outward
    image+=rim[...,None]*np.array([.12,.17,.22])
    return np.uint8(np.clip(np.round(image*255),0,255))

def focus(photo,mask,sigma):
    exterior=1-mask
    weight=cv2.GaussianBlur(exterior,(0,0),sigma)
    blurred=cv2.GaussianBlur(photo.astype(np.float32)*exterior[...,None],(0,0),sigma)
    background=blurred/np.maximum(weight[...,None],.001)
    # Avoid foreground colors spilling into the Gaussian background edge.
    return np.uint8(np.clip(np.round(photo*mask[...,None]+background*exterior[...,None]),0,255))

def extend_bedding(photo):
    px,py=PAD
    generated=OUT/'generated-bedding-overscan.png'
    if generated.exists():
        padded=cv2.GaussianBlur(rgb(generated),(0,0),6.5)
        assert padded.shape[:2]==(SIZE[1]+2*py,SIZE[0]+2*px)
        # Only consume the model's extended border. Preserve the approved
        # character and eye registration at every original-image pixel.
        padded[py:py+SIZE[1],px:px+SIZE[0]]=photo
        return padded
    # Continue the existing bedding palette/texture into overscan. No reflected
    # character copies; only the top/bottom margin is painted from bed samples.
    h,w=photo.shape[:2]
    edge=cv2.GaussianBlur(photo,(0,0),8)
    padded=cv2.copyMakeBorder(edge,py,py,px,px,cv2.BORDER_REPLICATE)
    bed=photo[0:110,0:520]
    bed=cv2.resize(bed,(w+2*px,py),interpolation=cv2.INTER_CUBIC)
    bed=cv2.GaussianBlur(bed,(0,0),5)
    edge_row=np.pad(edge[0:1],((0,0),(px,px),(0,0)),mode='edge').astype(np.float32)
    for y in range(py):
        distance=(py-y)/py
        padded[y]=np.uint8(np.clip(.82*edge_row[0]*(1-.12*distance)+.18*bed[y],0,255))
    low=np.pad(edge[-1:],((0,0),(px,px),(0,0)),mode='edge').astype(np.float32)
    for y in range(py):
        padded[py+h+y]=np.uint8(np.clip(low[0]*(1-.07*y/py),0,255))
    padded[py:py+h,px:px+w]=photo
    return padded

def native_stroke_matte(photo,envelope):
    """Closed-form color matting inside a traced native stroke, not a color key.

    Dark purple pixels are foreground seeds only. All uncertain edge pixels are
    solved with their neighbors; no threshold is applied to the final ink edge.
    """
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    ys,xs=np.where(envelope>0);x0=max(0,xs.min()-4);x1=min(SIZE[0],xs.max()+5)
    y0=max(0,ys.min()-4);y1=min(SIZE[1],ys.max()+5)
    color=photo[y0:y1,x0:x1].astype(float)/255
    window=envelope[y0:y1,x0:x1]>0
    raw=photo[y0:y1,x0:x1].astype(float)
    fg=window&(raw.mean(axis=2)<110)&(raw[:,:,1]<raw[:,:,0]+9)&(raw[:,:,2]>raw[:,:,1]+1)
    if not np.any(fg): raise ValueError('Traced native stroke has no foreground seed')
    # Known green iris pixels are background, not lost ink fringes.
    bg=(~cv2.dilate(np.uint8(window),np.ones((3,3),np.uint8)).astype(bool))|((raw[:,:,1]>raw[:,:,0]+23)&window)
    h,w=window.shape;n=h*w
    indices=np.arange(n).reshape(h,w)
    patches=np.lib.stride_tricks.sliding_window_view(indices,(3,3)).reshape(-1,9)
    colors=color.reshape(-1,3)[patches]
    centered=colors-colors.mean(axis=1,keepdims=True)
    covariance=np.einsum('nki,nkj->nij',centered,centered)/9+np.eye(3)[None]*1e-6/9
    local=np.eye(9)[None]-(1+np.einsum('nki,nij,nlj->nkl',centered,np.linalg.inv(covariance),centered))/9
    rows=np.repeat(patches,9,axis=1).ravel();cols=np.tile(patches,(1,9)).ravel()
    lap=sparse.coo_matrix((local.ravel(),(rows,cols)),shape=(n,n)).tocsr()
    known=(fg|bg).ravel().astype(float)
    alpha=np.clip(spsolve(lap+sparse.diags(100*known),100*fg.ravel()),0,1).reshape(h,w)
    alpha[~cv2.dilate(np.uint8(window),np.ones((3,3),np.uint8)).astype(bool)]=0
    # Use actual nearest opaque native pigment at fractional coverage, avoiding
    # a photographed skin/iris fringe baked into the moving transparent layer.
    _,labels=cv2.distanceTransformWithLabels(np.uint8(~fg),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    palette=np.zeros((labels.max()+1,3),np.uint8);palette[labels[fg]]=photo[y0:y1,x0:x1][fg]
    ink=palette[labels]
    ink[fg]=photo[y0:y1,x0:x1][fg]
    result=np.zeros((*SIZE[::-1],4),np.uint8)
    result[y0:y1,x0:x1,:3]=ink
    result[y0:y1,x0:x1,3]=np.uint8(np.round(alpha*255))
    return result


def trace_native_brow(photo,trace,origin,axis):
    """Follow the original thin brow ridge before solving its soft matte."""
    from scipy.ndimage import gaussian_filter1d
    normal=np.array([-axis[1],axis[0]])
    trace=np.array(trace,float);xs=np.arange(trace[0,0],trace[-1,0]+.25,.5)
    center=np.interp(xs,trace[:,0],trace[:,1]);offsets=np.arange(-2,2.01,.25)
    positions=origin+xs[:,None,None]*axis+(center[:,None]+offsets)[...,None]*normal
    gray=photo.mean(axis=2).astype(np.float32)
    def sample(shift):
        points=positions+normal*shift
        return cv2.remap(gray,points[:,:,0].astype(np.float32),points[:,:,1].astype(np.float32),cv2.INTER_LINEAR)
    cost=sample(0)-(sample(-2)+sample(2))*.5+offsets[None]**2*.15
    transitions=(offsets[:,None]-offsets[None,:])**2*8
    scores=cost[0];parents=[]
    for row in cost[1:]:
        candidates=scores[:,None]+transitions
        best=np.argmin(candidates,axis=0);parents.append(best)
        scores=candidates[best,np.arange(len(offsets))]+row
    selected=[int(np.argmin(scores))]
    for parent in reversed(parents): selected.append(int(parent[selected[-1]]))
    selected=selected[::-1]
    ys=center+gaussian_filter1d(offsets[selected],1)
    # A thin, partially covered brow has no reliable opaque seed. Recover its
    # coverage against the local background on both sides of the actual ridge.
    # This preserves the photographed ink edge without promoting pink hair or
    # white skin pixels to solid foreground, as the previous seed matte did.
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]].astype(np.float32)
    local_x=(xx-origin[0])*axis[0]+(yy-origin[1])*axis[1]
    local_y=(xx-origin[0])*normal[0]+(yy-origin[1])*normal[1]
    ridge=np.interp(local_x,xs,ys)
    distance=local_y-ridge
    def background(side):
        samples=[]
        for radius in [3.5,4.0,4.5]:
            shift=ridge+side*radius-local_y
            samples.append(cv2.remap(photo,(xx+normal[0]*shift).astype(np.float32),
                         (yy+normal[1]*shift).astype(np.float32),cv2.INTER_LINEAR))
        return np.median(samples,axis=0)
    weight=np.clip((distance+4)/8,0,1)[...,None]
    behind=background(-1)*(1-weight)+background(1)*weight
    # Native dark-purple pigment sampled from the intact thick first brow.
    pigment=np.array([97.,89.,108.])
    direction=behind-pigment
    alpha=np.clip(np.sum((behind-photo)*direction,axis=2)/np.maximum(np.sum(direction**2,axis=2),1),0,1)
    support=np.clip((2.6-np.abs(distance))/.8,0,1)
    support*=np.clip((local_x-xs[0]+.4)/1.5,0,1)*np.clip((xs[-1]+.4-local_x)/1.5,0,1)
    alpha*=support
    # Keep the actual native pigment variation. Save the background used in
    # this decomposition rather than reverse-solving it from quantized alpha;
    # that inversion amplified tiny RGB errors into cyan/white edge spots.
    active=alpha>1/255
    residual=photo.astype(float)-behind
    minimum=np.max(np.where(residual<0,-residual/np.maximum(behind,1),residual/np.maximum(255-behind,1)),axis=2)
    alpha[active]=np.maximum(alpha[active],minimum[active])
    alpha=np.round(alpha*255)/255
    ink=behind+(photo.astype(float)-behind)/np.maximum(alpha[...,None],1/255)
    result=np.zeros((*SIZE[::-1],4),np.uint8)
    result[:,:,:3]=np.uint8(np.clip(np.round(ink),0,255))
    result[:,:,3]=np.uint8(np.round(alpha*255))
    underlay=photo.copy();underlay[alpha>0]=np.uint8(np.clip(np.round(behind[alpha>0]),0,255))
    return result,underlay


def refine_cutout_edge(layer):
    """Subpixel matte cleanup and color bleed for moving native cutouts only."""
    result=layer.copy();alpha=layer[:,:,3].astype(float)/255
    # A subpixel filter smooths stair steps in the matte without blurring the
    # opaque native ink or any face/iris pixels. Never filter expression frames.
    soft=cv2.GaussianBlur(alpha,(0,0),.4)
    result[:,:,3]=np.uint8(np.round((alpha*.3+soft*.7)*255))
    visible=alpha>0
    if np.any(visible):
        threshold=max(.03,float(np.quantile(alpha[visible],.7)))
        reliable=alpha>=threshold
        _,labels=cv2.distanceTransformWithLabels(np.uint8(~reliable),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        palette=np.zeros((labels.max()+1,3),np.uint8);palette[labels[reliable]]=layer[:,:,:3][reliable]
        # Transparent RGB previously contained arbitrary inverse-matte colors;
        # bilinear filtering pulled those into the moving purple ink edge.
        fringe=alpha<.15;result[fringe,:3]=palette[labels][fringe]
    return result


def native_eye_layers(photo):
    """Separate native ink, iris, eye body and hidden skin for GPU deformation."""
    from scipy.interpolate import PchipInterpolator
    directory=ASSETS/'eyes'; directory.mkdir(parents=True,exist_ok=True)
    manual_path=PROJECT/'brow-paths.json'
    manual_lids=None
    if manual_path.exists():
        from brow_paths import load as load_brow_paths
        # Historical JSON key/name is retained for the pen editor. The user's
        # saved contours surround the upper lashes, not the separate eyebrows.
        manual_lids=load_brow_paths(manual_path)['brows']
    trace_data=json.loads((PROJECT/'eye-traces.json').read_text(encoding='utf-8'))
    traces=trace_data['eyes']
    previous=json.loads((INPUT/'godot/rigs.json').read_text(encoding='utf-8'))['a']['eyes']
    yy,xx=np.mgrid[:SIZE[1],:SIZE[0]].astype(np.float32)
    regions=np.zeros((*SIZE[::-1],3),np.uint8)
    foreground=np.zeros(SIZE[::-1],np.uint8)
    first_strand=np.zeros_like(foreground)
    # Original a eyes were removed and the full exposed footprints completed
    # once with gpt-image-2, including continuous tapered hair behind the eyes.
    # This registered static clean plate is not a generated expression frame.
    # No local color fills or wide inpaint ribbons may replace its skin/hair.
    native_skin=rgb(ROOT/'assets/chorus-cgc06/eye-clean-plate.png')
    upper_fringe=polygon(np.array([(914,201),(918,204),(922,215),(918,219),(917,225),(914,230),(911,228),(913,220),(914,214),(912,206)]))
    skin=native_skin.copy();sclera=photo.copy()
    eyes=[];brows=[];lid_meshes=[];brow_cutouts=[];brow_underlays=[]
    upper_layer=np.zeros((*SIZE[::-1],4),np.uint8);lower_layer=upper_layer.copy();brow_layer=upper_layer.copy()
    iris_mask=np.zeros(SIZE[::-1],np.uint8);face_base=native_skin.copy()
    for index,(trace,old) in enumerate(zip(traces,previous)):
        origin=np.array(old['basis'][:2]);old_axis=np.array(old['basis'][2:]);old_normal=np.array([-old_axis[1],old_axis[0]])
        def world(points):
            points=np.asarray(points,float)
            return origin+points[:,0,None]*old_axis+points[:,1,None]*old_normal
        # All pins move in the face's original local up/down coordinates.
        # Eye-corner diagonals are not used as the closure axis.
        axis=old_axis;normal=old_normal;center=origin
        def local(points): return np.asarray(points,float)
        xmin=min(p[0] for p in trace['upper']);xmax=max(p[0] for p in trace['upper'])
        xs=np.linspace(xmin,xmax,512)
        meet=14.0+12.0*np.sin(np.pi*np.linspace(0,1,512))
        closed_world=center+xs[:,None]*axis+meet[:,None]*normal
        for part,rows in [('upper',[-18,-12,-7,-3,0,4,8]),('lower',[-8,-5,0,3,7,12])]:
            points=local(trace[part])
            length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
            dense=PchipInterpolator(length,points,axis=0)(np.linspace(0,length[-1],2048))
            arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
            samples=np.column_stack([np.interp(np.linspace(0,arc[-1],64),arc,dense[:,j]) for j in range(2)])
            lid_meshes.append({'eye':index,'part':part,'basis':[*center.tolist(),*axis.tolist()],
                               'source':samples.tolist(),'rows':rows})
        outline=cv2.dilate(polygon(world(trace['outline'])),np.ones((7,7),np.uint8))
        closed_region=np.zeros(SIZE[::-1],np.uint8)
        cv2.polylines(closed_region,[np.round(closed_world).astype(np.int32)],False,255,22,cv2.LINE_AA)
        outline=np.maximum(outline,closed_region)
        # The polygon includes native lash tips, but excludes brows/creases.
        regions[:,:,index]=outline
        for points in trace['foreground']:
            strand=polygon(world(points))
            foreground=np.maximum(foreground,strand)
            if index==0: first_strand=np.maximum(first_strand,strand)
        upper_depth,lower_depth=trace['depth']
        for name,layer in [('upper_outline',upper_layer),('lower_outline',lower_layer)]:
            envelope=polygon(world(trace[name]))
            manual=name=='upper_outline' and manual_lids and manual_lids[index].get('closed')
            if manual:
                from brow_paths import rasterize
                envelope=rasterize(manual_lids[index])
            extracted=native_stroke_matte(photo,envelope)
            if manual:
                # Refine only soft skin spill within the user's outline. Keep
                # the native ink and lash tips; never turn the entire U-shaped
                # selection into a flattened closing ribbon.
                extracted[:,:,3]=np.uint8(np.round(extracted[:,:,3].astype(float)*envelope/255))
            select=extracted[:,:,3]>layer[:,:,3];layer[select]=extracted[select]
        iris=polygon(world(trace['iris']))
        iris_mask=np.maximum(iris_mask,iris)
        white_colors=[]
        for sx,sy in world(trace['white_samples']):
            px,py=int(round(sx)),int(round(sy))
            white_colors.append(photo[py,px])
        # Sclera under the movable iris is extended from existing native white
        # samples, solely for the hidden layer. Native iris RGB is never painted.
        sclera[iris==255]=np.uint8(np.median(white_colors,axis=0))
        # Independent native eyebrow ribbon, including its antialiased fringe.
        brow_points=np.asarray(trace['brow'],float)
        brow_width=7
        extracted,brow_underlay=trace_native_brow(photo,trace['brow'],origin,old_axis)
        brow_cutouts.append(extracted.copy());brow_underlays.append(brow_underlay)
        select=extracted[:,:,3]>brow_layer[:,:,3];brow_layer[select]=extracted[select]
        face_base[select]=brow_underlay[select]
        brows.append({'basis':[*origin.tolist(),*old_axis.tolist()],
                      'bounds':[float(brow_points[:,0].min()),float(brow_points[:,0].max()),0,0]})
        points=brow_points
        length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        samples=PchipInterpolator(length,points,axis=0)(np.linspace(0,length[-1],64))
        lid_meshes.append({'eye':index,'part':'brow','basis':[*origin.tolist(),*old_axis.tolist()],
                           'source':samples.tolist(),'rows':np.linspace(-brow_width,brow_width,7).tolist()})
        # Use the complete eye-free background on both base layers. Reusing
        # the open photo at an eroded patch perimeter leaves static old ink
        # behind the puppet; native eye pixels belong only to the eye parts.
        eyes.append({'basis':[*center.tolist(),*axis.tolist()],
                     'bounds':[float(xmin),float(xmax),float(upper_depth),float(lower_depth)],
                     'iris_center':world(trace['iris']).mean(axis=0).tolist()})
    # Upper corner fibers belong to the upper part, never to both lid layers.
    # User-marked side strand is stationary hair, not part of the lash cutout.
    upper_layer[:,:,3]=np.uint8(np.round(upper_layer[:,:,3]*(1-foreground.astype(float)/255)))
    lower_layer[:,:,3]=np.uint8(np.round(lower_layer[:,:,3]*(1-foreground.astype(float)/255)))
    lower_layer[:,:,3]=np.uint8(np.round(lower_layer[:,:,3]*(1-upper_layer[:,:,3].astype(float)/255)))
    # Center the ribbon on actual native ink, rather than its inner edge.
    # Both lids can then meet on the same curve without double outlines.
    from scipy.ndimage import gaussian_filter1d
    # Recover pigment against the actual clean underlay. This makes native
    # eye reconstruction exact instead of substituting nearest dark pigment.
    combined=1-(1-upper_layer[:,:,3].astype(float)/255)*(1-lower_layer[:,:,3].astype(float)/255)
    eye_clean=cv2.inpaint(photo,np.uint8(combined>.005)*255,3,cv2.INPAINT_TELEA)
    behind=eye_clean.astype(float);residual=photo.astype(float)-behind
    minimum=np.max(np.where(residual<0,-residual/np.maximum(behind,1),residual/np.maximum(255-behind,1)),axis=2)
    desired=np.ceil(np.maximum(combined,minimum)*255)/255
    ua=upper_layer[:,:,3].astype(float)/255;la=lower_layer[:,:,3].astype(float)/255
    choose=ua>=la
    ua[choose]=np.clip((desired[choose]-la[choose])/np.maximum(1-la[choose],1e-6),0,1)
    la[~choose]=np.clip((desired[~choose]-ua[~choose])/np.maximum(1-ua[~choose],1e-6),0,1)
    upper_layer[:,:,3]=np.uint8(np.ceil(ua*255));lower_layer[:,:,3]=np.uint8(np.ceil(la*255))
    combined=1-(1-upper_layer[:,:,3].astype(float)/255)*(1-lower_layer[:,:,3].astype(float)/255)
    pigment=np.uint8(np.clip(np.round(behind+residual/np.maximum(combined[...,None],1/255)),0,255))
    upper_layer[:,:,:3]=pigment;lower_layer[:,:,:3]=pigment
    # Keep each upper/lower cutout complete. The short horizontal trace is
    # only a displacement guide; it never partitions the original alpha.
    native_opening=np.zeros((*SIZE[::-1],3),np.uint8)
    full_lid_sources={}
    guide_ranges={(0,'upper'):(8,43),(0,'lower'):(12,56),
                  (1,'upper'):(26,57),(1,'lower'):(8,38)}
    for part in lid_meshes:
        source=np.array(part['source']);kind=part['part'];index=part['eye']
        if kind!='brow':
            tangent=np.gradient(source,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
            normals=np.c_[-tangent[:,1],tangent[:,0]]
            distances=np.linspace(-12 if kind=='upper' else -3,4 if kind=='upper' else 10,97)
            positions=source[:,None]+normals[:,None]*distances[None,:,None]
            cx,cy,ax,ay=part['basis'];mx=(cx+positions[:,:,0]*ax-positions[:,:,1]*ay).astype('float32');my=(cy+positions[:,:,0]*ay+positions[:,:,1]*ax).astype('float32')
            alpha=cv2.remap((upper_layer if kind=='upper' else lower_layer)[:,:,3],mx,my,cv2.INTER_LINEAR).astype(float)/255
            weights=alpha**2;valid=weights.sum(axis=1)>2
            centers=(weights*distances).sum(axis=1)/np.maximum(weights.sum(axis=1),1e-6)
            centers=np.interp(np.arange(64),np.flatnonzero(valid),centers[valid])
            source+=normals*gaussian_filter1d(centers,2)[:,None]
        if kind!='brow':
            full_lid_sources[index,kind]=source.copy()
            first,last=guide_ranges[index,kind]
            guide=source[first:last+1]
            cx,cy,ax,ay=part['basis']
            xlocal=(xx-cx)*ax+(yy-cy)*ay;ylocal=-(xx-cx)*ay+(yy-cy)*ax
            layer=upper_layer if kind=='upper' else lower_layer
            selected=(np.abs(xlocal)<75)&(np.abs(ylocal)<75)&(layer[:,:,3]>0)
            xgrid=np.linspace(min(-60,float(xlocal[selected].min())-3),
                              max(55,float(xlocal[selected].max())+3),64)
            source=np.c_[xgrid,np.interp(xgrid,guide[:,0],guide[:,1])]
            # The complete cutout is transported around this reference ridge.
            # Smooth the joins to its constant tails, otherwise their slope
            # jumps turn thick native lash edges into angular blocks mid-blink.
            source[:,1]=gaussian_filter1d(source[:,1],1.5)
            part['grid_y']=np.linspace(float(ylocal[selected].min())-4,
                                       float(ylocal[selected].max())+4,41).tolist()
            part['mode']='whole_cutout'
        source_pins=np.array([source[0],source[16],source[32],source[47],source[63]])
        if kind=='brow': closed=source_pins+np.array([0.,6.])
        else:
            xmin=min(p[0] for p in traces[index]['upper']);xmax=max(p[0] for p in traces[index]['upper'])
            tx=np.linspace(xmin,xmax,5)
            closed=np.c_[tx,np.zeros(5)]
        part['stations']=np.linspace(0,1,len(source)).tolist()
        part['source']=source.tolist();part['source_pins']=source_pins.tolist();part['closed_pins']=closed.tolist()
    for index in range(2):
        lower=next(p for p in lid_meshes if p['eye']==index and p['part']=='lower')
        upper=next(p for p in lid_meshes if p['eye']==index and p['part']=='upper')
        # Reference BV1rR4y1N7q4 at54–55s: shallow closed line around mid-eye.
        # Both lid cages share these anchors; native x stays fixed at runtime.
        tx=np.array(upper['closed_pins'])[:,0]
        ys=[8.5,10.5,11.0,10.5,8.5] if index==0 else [8.5,9.8,10.2,9.8,8.5]
        upper['closed_pins']=np.c_[tx,ys].tolist()
        lower['closed_pins']=[point[:] for point in upper['closed_pins']]
        # Native tip regions in the original eye coordinates. The long side
        # tip is measured from actual cutout coverage; the short opposite tip
        # is retained in the rig but remains below the default 14px threshold.
        root=np.array([-43.,-8.] if index==0 else [31.,-6.])
        cx,cy,ax,ay=upper['basis'];ty,tx0=np.where(upper_layer[:,:,3]>32)
        local=np.c_[(tx0-cx)*ax+(ty-cy)*ay,-(tx0-cx)*ay+(ty-cy)*ax]
        side=local[(local[:,0]<-20 if index==0 else local[:,0]>15)&(local[:,1]>root[1])]
        end=np.median(side[side[:,1]>=np.quantile(side[:,1],.95)],axis=0)
        # Place the root on the main native stroke, rather than halfway down
        # the long side wall. The far-eye old anchor left a hooked closed tip.
        source=np.array(upper['source'])
        root[1]=np.interp(root[0],source[:,0],source[:,1])+2.0
        length=float(np.linalg.norm(end-root));direction=(end-root)/length
        short_root=np.array([29.,-26.] if index==0 else [-29.,-20.])
        short_end=np.array([37.,-17.] if index==0 else [-33.,-13.])
        short_length=float(np.linalg.norm(short_end-short_root))
        upper['tip_regions']=[{'anchor':root.tolist(),'direction':direction.tolist(),'length':length,'radius':50.0 if index==0 else 40.0},
                              {'anchor':short_root.tolist(),'direction':((short_end-short_root)/short_length).tolist(),'length':short_length,'radius':8.0}]
    for index in range(2):
        full=np.r_[full_lid_sources[index,'upper'],full_lid_sources[index,'lower'][::-1]]
        cx,cy,ax,ay=eyes[index]['basis']
        native_opening[:,:,index]=polygon(np.c_[cx+full[:,0]*ax-full[:,1]*ay,cy+full[:,0]*ay+full[:,1]*ax])
        sources=[np.array(p['source']) for p in lid_meshes if p['eye']==index and p['part']!='brow']
        eyes[index]['opening_x']=[float(min(p[0,0] for p in sources)),float(max(p[-1,0] for p in sources))]
    # Recover native ink against the actual shader underlay at rest. The iris
    # gate follows the lash centerline; original fringe colors are therefore
    # solved against clean skin outside the opening and clean eye inside it.
    rest_gate=np.zeros(SIZE[::-1],float)
    for index,eye in enumerate(eyes):
        selected=regions[:,:,index]>0
        cx,cy,ax,ay=eye['basis'];pixels=np.c_[((xx-cx)*ax+(yy-cy)*ay)[selected],(-(xx-cx)*ay+(yy-cy)*ax)[selected]]
        gx=np.linspace(*eye['opening_x'],64);curves=[]
        for kind in ['upper','lower']:
            source=np.array(next(p for p in lid_meshes if p['eye']==index and p['part']==kind)['source'])
            gy=np.full(64,source[-1,1]);left=gx<source[0,0];right=gx>source[-1,0]
            gy[left]=source[0,1]+(-1 if kind=='upper' else 1)*abs(gx[left]-source[0,0])*.25
            gy[right]=source[-1,1]+(-1 if kind=='upper' else 1)*abs(gx[right]-source[-1,0])*.25
            pending=~(left|right)
            for j in range(len(source)-1):
                take=pending&(gx<=source[j+1,0]);gy[take]=source[j,1]+(source[j+1,1]-source[j,1])*(gx[take]-source[j,0])/max(source[j+1,0]-source[j,0],.00001);pending[take]=False
            curves.append(np.c_[gx,gy])
        poly=np.r_[curves[0],curves[1][::-1]];inside=np.zeros(len(pixels),bool);nearest=np.full(len(pixels),np.inf)
        top_distance=nearest.copy();bottom_distance=nearest.copy();top=np.zeros_like(pixels);bottom=np.zeros_like(pixels)
        for j,a in enumerate(poly):
            b=poly[(j+1)%128];edge=b-a;t=np.clip((pixels-a)@edge/max(float(edge@edge),1e-8),0,1);closest=a+t[:,None]*edge;distance=np.sum((pixels-closest)**2,axis=1);nearest=np.minimum(nearest,distance)
            if j<63:
                take=distance<top_distance;top_distance[take]=distance[take];top[take]=closest[take]
            if 64<=j<127:
                take=distance<bottom_distance;bottom_distance[take]=distance[take];bottom[take]=closest[take]
            if abs(b[1]-a[1])>1e-12:
                crossing=a[0]+(pixels[:,1]-a[1])*(b[0]-a[0])/(b[1]-a[1]);inside^=((a[1]>pixels[:,1])!=(b[1]>pixels[:,1]))&(pixels[:,0]<crossing)
        coverage=np.clip(np.sqrt(nearest)*np.where(inside,1,-1)+.5,0,1)*np.clip(np.linalg.norm(top-bottom,axis=1),0,1)
        rest_gate[selected]=coverage*native_opening[:,:,index][selected].astype(float)/255
    ua=upper_layer[:,:,3].astype(float)/255;la=lower_layer[:,:,3].astype(float)/255
    combined=1-(1-ua)*(1-la)
    # Never refill the concealed eye area from the open plate. A soft matte
    # can have zero-alpha gaps along antialiased side walls; refilling those
    # gaps leaves a stationary dotted edge when the whole lid moves away.
    # The saved clean plate already preserves exact source pixels outside its
    # edit mask. Do not refill it with old eye ink at the eye-region perimeter.
    behind=skin*(1-rest_gate[...,None])+eye_clean*rest_gate[...,None]
    residual=photo.astype(float)-behind
    minimum=np.max(np.where(residual<0,-residual/np.maximum(behind,1),residual/np.maximum(255-behind,1)),axis=2)
    desired=np.ceil(np.maximum(combined,np.where(combined>0,minimum,0))*255)/255
    choose=ua>=la
    ua[choose]=np.clip((desired[choose]-la[choose])/np.maximum(1-la[choose],1e-6),0,1)
    la[~choose]=np.clip((desired[~choose]-ua[~choose])/np.maximum(1-ua[~choose],1e-6),0,1)
    upper_layer[:,:,3]=np.uint8(np.ceil(ua*255));lower_layer[:,:,3]=np.uint8(np.ceil(la*255))
    combined=1-(1-upper_layer[:,:,3].astype(float)/255)*(1-lower_layer[:,:,3].astype(float)/255)
    pigment=np.uint8(np.clip(np.round(behind+residual/np.maximum(combined[...,None],1/255)),0,255))
    for layer in [upper_layer,lower_layer]:layer[:,:,:3]=pigment
    # Remove the isolated matte fleck below the second inner corner. This is
    # local alpha cleanup, never a partition of the complete lower lid.
    fleck=np.zeros(SIZE[::-1],np.uint8)
    cv2.circle(fleck,(906,354),2,255,-1)
    lower_layer[fleck>0,3]=0
    # Hidden skin/hair comes solely from the completed clean plate above.
    # Actual component PNGs, not whole-face stand-ins. Body keeps native whites;
    # only the concealed area under the iris is filled from existing sclera.
    eye_mask=np.max(regions[:,:,:2],axis=2)
    sclera[iris_mask<255]=eye_clean[iris_mask<255]
    for name,data in [('eyebrow',brow_layer),('eye-iris',np.dstack([eye_clean,iris_mask])),
                      ('eye-body',np.dstack([sclera,eye_mask])),('upper-lid',upper_layer),('lower-lid',lower_layer)]:
        save(directory/(name+'.png'),refine_cutout_edge(data) if name in ['eyebrow','upper-lid','lower-lid'] else data)
        settings=directory/(name+'.png.import')
        config=settings.read_text(encoding='utf-8') if settings.exists() else '[remap]\nimporter="texture"\n\n[params]\nprocess/fix_alpha_border=false\n'
        settings.write_text(config.replace('process/fix_alpha_border=true','process/fix_alpha_border=false'),encoding='utf-8')
    edge_definitions=[]
    edge_paths=[[
        [(920.7,193.0),(922.8,200.0),(924.0,208.0),(922.0,218.0)],
        [(926.3,201.0),(925.2,206.0),(924.0,210.0)]
    ],[
        [(964.7,306.6),(967.5,306.9),(970.0,307.7),(972.4,309.0),(974.6,310.5)],
        [(967.3,309.1),(970.3,309.4),(972.4,310.8)]
    ]]
    edge_paths=trace_data.get('edge_paths_world',edge_paths)
    for index,paths in enumerate(edge_paths):
        patch=Image.new('L',(SIZE[0]*4,SIZE[1]*4));draw=ImageDraw.Draw(patch)
        for path in paths: draw.line([tuple(np.array(point)*4) for point in path],fill=255,width=6 if index==1 else 14,joint='curve')
        support=np.array(patch.resize(SIZE,Image.Resampling.LANCZOS));active=support>3
        cleanup=cv2.dilate(np.uint8(active),np.ones((3,3) if index==1 else (7,7),np.uint8))>0
        if index==1:
            # The long line above this crease is HAIR (user annotation).
            # Bound both extraction and concealed repair to the small mark;
            # never erase or transport the neighboring stationary hair ridge.
            crease_domain=polygon(np.array([(965,305),(977,307),(991,313),(991,322),(979,318),(965,311)]))>0
            active&=crease_domain;cleanup&=crease_domain
        if index==0: cleanup|=cv2.dilate(upper_fringe,np.ones((5,5),np.uint8))>0
        if index==0: active&=upper_fringe==0
        # Keep the original small-stroke matte estimate. The broad donor
        # exclusion below is only for extraction, never a visible skin repair.
        donor_mask=np.uint8((cv2.dilate(np.uint8(cleanup),np.ones((5,5),np.uint8))>0)|(regions[:,:,index]>0))*255
        under=cv2.inpaint(photo,donor_mask,5,cv2.INPAINT_TELEA)
        direction=under.astype(float)-np.array([141.,119.,134.])
        coverage=np.clip(np.sum((under.astype(float)-photo)*direction,axis=2)/np.maximum(np.sum(direction**2,axis=2),1),0,1)
        active&=coverage>1/255
        # Stable native gray-purple pigment avoids carrying reconstructed
        # white/black background fragments into a different skin location.
        pigment=np.array([141.,119.,134.])
        maximum=np.min(np.minimum(photo.astype(float)/pigment,(255-photo.astype(float))/(255-pigment)),axis=2)
        alpha=np.floor(np.minimum(coverage,np.minimum(maximum,.98))*255)/255
        alpha[~active]=0
        if index==1:
            # The two fine native creases cross static hair. A wide color
            # selection transported those diagonal hair fragments as a grid.
            # Recover coverage along each annotated crease, reject isolated
            # crossing samples, and retain only its narrow transverse profile.
            from scipy.ndimage import median_filter,gaussian_filter1d
            clean_alpha=np.zeros_like(alpha)
            for path in paths:
                path=np.array(path,float)
                arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
                stations=np.linspace(0,arc[-1],int(arc[-1]*4)+1)
                centers=np.column_stack([np.interp(stations,arc,path[:,j]) for j in range(2)])
                values=cv2.remap(coverage,centers[:,0].astype(np.float32)[None],
                                 centers[:,1].astype(np.float32)[None],cv2.INTER_LINEAR)[0]
                values=gaussian_filter1d(median_filter(values,size=13,mode='nearest'),2)
                nearest_distance=np.full(alpha.shape,np.inf);nearest_arc=np.zeros_like(alpha)
                for j in range(len(path)-1):
                    direction=path[j+1]-path[j];length=np.linalg.norm(direction)
                    parameter=np.clip(((xx-path[j,0])*direction[0]+(yy-path[j,1])*direction[1])/length**2,0,1)
                    distance=np.hypot(xx-path[j,0]-parameter*direction[0],yy-path[j,1]-parameter*direction[1])
                    nearer=distance<nearest_distance
                    nearest_distance[nearer]=distance[nearer]
                    nearest_arc[nearer]=arc[j]+parameter[nearer]*length
                profile=np.exp(-.5*(nearest_distance/.55)**2)
                profile[nearest_distance>1.4]=0
                taper=np.clip(nearest_arc/.8,0,1)*np.clip((arc[-1]-nearest_arc)/.8,0,1)
                clean_alpha=np.maximum(clean_alpha,np.interp(nearest_arc,stations,values)*profile*taper)
            alpha=np.round(clean_alpha*255)/255
        # Keep stable pigment for the thin cutout. Inverting a nearly opaque
        # stroke amplifies color noise into moving red/black fragments.
        layer=np.dstack([np.broadcast_to(np.uint8(pigment),photo.shape),np.uint8(alpha*255)])
        save(directory/f'edge-detail-{index+1}.png',refine_cutout_edge(layer))
        # Complete eye-free background; preserve its drawn hair tips instead
        # of smearing the entire eye region with the extraction estimate.
        under=native_skin
        # Erase the whole traced support, including faint antialias pixels and
        # the join to the old lash fringe. Erasing only measured ink coverage
        # left stationary speckles when the independent crease moved away.
        # A feather outside the complete stroke support avoids a staircase
        # seam through the surrounding fine hair/skin colors.
        blend=cv2.GaussianBlur(np.float32(cleanup),(0,0),1.0)[...,None]
        for field in [face_base,skin]:
            field[:]=np.uint8(np.clip(np.round(field*(1-blend)+under*blend),0,255))
            if index==1:
                brow_mask=brow_cutouts[index][:,:,3]>0
                field[brow_mask]=brow_underlays[index][brow_mask]
        # Inside the still-visible eye preserve its original RGB; only erase
        # the vacated crease outside the original opening.
        eye_blend=blend*(1-rest_gate[...,None])
        eye_clean[:]=np.uint8(np.clip(np.round(eye_clean*(1-eye_blend)+under*eye_blend),0,255))
        body_path=directory/'eye-body.png';body=np.array(Image.open(body_path))
        body[:,:,:3]=np.uint8(np.clip(np.round(body[:,:,:3]*(1-eye_blend)+under*eye_blend),0,255));save(body_path,body)
        anchor=np.mean(np.array([point for path in paths for point in path]),axis=0)
        ridge=np.array(paths[0]);direction=ridge[-1]-ridge[0]
        edge_definitions.append({'eye':index,'anchor':anchor.tolist(),
                                 'angle':float(np.arctan2(direction[1],direction[0])),
                                 'texture':f'edge-detail-{index+1}.png','mesh_link':False})
    (directory/'edge-details.json').write_text(json.dumps(edge_definitions,indent=2),encoding='utf-8')
    save(directory/'face-base.png',face_base)
    save(directory/'eye-clean.png',eye_clean)
    save(directory/'eye-skin.png',skin)
    save(directory/'eye-region.png',regions)
    save(directory/'eye-foreground.png',foreground)
    # The side strand overlaps the original sclera. An opaque photograph
    # patch freezes a white sliver beside the closed lash; retain only its ink.
    stationary=np.dstack([photo,np.uint8(foreground>0)*255])
    strand_ink=native_stroke_matte(photo,first_strand)
    strand_ink[:,:,3]=np.uint8(np.round(strand_ink[:,:,3]*first_strand.astype(float)/255))
    stationary[first_strand>0]=strand_ink[first_strand>0]
    save(directory/'stationary-hair.png',refine_cutout_edge(stationary))
    save(directory/'native-opening.png',native_opening)
    save(directory/'eyebrow.png',refine_cutout_edge(brow_layer))
    (directory/'lid-meshes.json').write_text(json.dumps(lid_meshes),encoding='utf-8')
    (PROJECT/'rig.json').write_text(json.dumps({'closed':False,'eyes':eyes,'brows':brows},indent=2),encoding='utf-8')
    separate_stationary_hair(photo,native_skin,trace_data,directory)


def separate_stationary_hair(photo,native_skin,trace_data,directory):
    """Reassign marked native hair from the moving cutout to the fixed layer."""
    stationary=Image.open(directory/'stationary-hair.png').convert('RGBA')
    for region in trace_data.get('stationary_hair_transfers_world',[]):
        path=directory/(region.get('part','upper')+'-lid.png')
        layer=np.array(Image.open(path))
        support=polygon(np.array(region['polygon_world']))/255.
        # Color matching helps where the selection crosses a lash junction.
        # Precisely bounded hair selections transfer all opacity, including
        # fringes whose clean-plate color differs from the original photo.
        if region.get('match_underlay',True):
            difference=np.linalg.norm(photo.astype(float)-native_skin.astype(float),axis=2)
            t=np.clip((difference-region['difference_full'])/(region['difference_reject']-region['difference_full']),0,1)
            support*=1-t*t*(3-2*t)
        original=layer[:,:,3]/255.
        remaining=original*(1-support)
        # Conserve the original composite when the two native parts overlap
        # at rest. This is a static ownership correction, not animated clipping.
        transferred=np.divide(original-remaining,1-remaining,out=np.zeros_like(original),where=1-remaining>1e-8)
        hair=layer.copy();hair[:,:,3]=np.uint8(np.round(transferred*255))
        stationary=Image.alpha_composite(Image.fromarray(hair),stationary)
        layer[:,:,3]=np.uint8(np.round(remaining*255))
        save(path,layer)
    save(directory/'stationary-hair.png',np.array(stationary))


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    ASSETS.mkdir(parents=True,exist_ok=True)
    original=rgb(INPUT/'photos/CGC06_a-clothed-lit.png')
    mask=heroine_mask(original)
    save(OUT/'heroine-focus-mask.png',np.uint8(np.round(mask*255)))
    relaxed=smooth_smile(original)
    before=Image.fromarray(original).crop((800,300,875,380)).resize((450,480))
    after=Image.fromarray(relaxed).crop((800,300,875,380)).resize((450,480))
    comp=Image.new('RGB',(900,504),'#142239');comp.paste(before,(0,24));comp.paste(after,(450,24))
    d=ImageDraw.Draw(comp);d.text((8,6),'BEFORE',fill='white');d.text((458,6),'RELAXED SMILE',fill='white')
    comp.save(OUT/'smile-before-after.png')
    for shot in ['a','e']:
        source=relaxed if shot=='a' else rgb(INPUT/f'photos/CGC06_{shot}-clothed-lit.png')
        lit=lighting(source,mask)
        save(OUT/f'CGC06-{shot}-lit-unfocused.png',lit)
        # Bridge's 11px blur is at 1920px output width. Account for this shot's
        # crop zoom rather than magnifying an 11px source blur into 18–38px.
        plate=focus(lit,mask,6.5 if shot=='a' else 3.25)
        save(ASSETS/f'{shot}-plate.png',plate)
        save(ASSETS/f'{shot}-overscan.png',extend_bedding(plate))
        save(OUT/f'CGC06-{shot}-focused-lit.png',plate)
    # Puppet textures use this shot's exact approved/lighted native plate.
    native_eye_layers(rgb(ASSETS/'a-plate.png'))
    metadata={'song_start':66.0,'song_end':72.3,'duration':6.3,'pad':list(PAD),
       'source_size':list(SIZE),'output_size':[1920,1080],
       'source':'User-approved clothed CGC06 plates from issue128; originals unchanged',
       'light':'Upper-right cool blue-white key, controlled highlights, face warmth retained',
       'focus':'Bridge-like ~11px screen Gaussian: source sigma6.5 overview / 3.25 closeup; heroine edge feather sigma2.2',
       'overscan':('gpt-image-2 API generated border; original central image preserved' if (OUT/'generated-bedding-overscan.png').exists() else 'Bedding texture/palette continuation; generation pending'),
       'timeline':{'static_closed_o_closeup':[0,2.55],'gaussian_transition':[2.55,3.10],
          'smile_open':[3.10,4.30],'quick_close':[4.30,4.45],'closed_hold':[4.45,4.45],
          'fast_blink_to_70_percent':[4.30,4.60],'opening_0_to_70_percent':[4.45,4.60],
          'opening_70_to_100_percent':[4.60,6.30],'slow_open':[4.60,6.30],'open_finish':[6.30,6.30]},
       'rotation':{'local_seconds':[2.55,6.3],'degrees':[0,-10],
          'progress':'Integrated velocity: smoothstep ramp over2.55..3.10, constant speed3.10..4.60, smoothstep deceleration4.60..6.30; distance normalization2.625',
          'deceleration_local_seconds':[4.60,6.30],'quick_blink_speed_degrees_per_second':-10/2.625,
          'source_pivot':[900,270],'screen_pivot':[1400,420]},
       'closeup':{'source_from':[430,560],'source_to':[765,430],
          'rotation_degrees':0,'scale':[3.15,3.50],
          'translation_easing':'Gentler entry hold 0.08s, integrated smoothstep velocity deceleration 1.50s, then continuous visible slow pan',
          'entry_progress_rate':.85,'tail_progress_rate':.08,'entry_hold':.08,'deceleration_seconds':1.50,'slow_start':1.58,'zoom_easing':'smoothstep 0–1.58s',
          'preroll':'Same motion script in the phone incoming viewport; position and velocity continuous at 66.000'},
       'transition':{'blur_seconds':[2.55,3.10],'blur_peak_radius_px':22,'dissolve_seconds':[2.55,3.10],'method':'Original Gaussian cross-dissolve between independent views; outgoing closeup keeps slow pan until fully faded; no pullback'},
       'eye_puppet':{'method': 'Complete native upper/lower cutouts on continuous 64x41 grids. Shared five-pin closed lines sit near mid-eye with shallow arches, inspired by BV1rR4y1N7q4 at54–55s. Both lids retain native x; lower closure follows p*(0.7+0.3*p), rises and flattens onto the upper line. Long lash roots lie on the native stroke; tips shorten along their measured directions, then the mesh samples both guide curves at the displaced x. Broad smooth root gathering reduces hooked corners; original UV and alpha remain intact. Static iris/sclera are spatially occluded by the opening. True brows and separate crease parts remain controllable. No generated poses, lash clipping, expression switches or temporal crossfade.', 'shader': 'eyes.gdshader', 'controls': '30 Marker2D pins; native brow meshes synchronized with upper closure; separate EyeEdgeDetail1/2 sprites; fixed StationaryHair sprite; Inspector Resource, no panel', 'time_driver': 'continuous analytic time parameter; same geometry path for closing/opening; no AnimationPlayer pose keys or expression image sequence'},
       'frames_install_fps':30,'visual_acceptance':'pending'}
    metadata['eye_puppet']['cutout_policy']='Whole upper and whole lower native cutouts, one 64x41 grid per lid; true brows retained as native ribbons, small creases separate, marked hair excluded from moving lash cutouts'
    metadata['eye_puppet']['deformation_details']={'ridge_spans': {'upper1': [8, 43], 'upper2': [26, 57]}, 'reference_smoothing_sigma_stations': 1.5, 'turn_soft_limit_radians': 0.35, 'rotation_spatial_smoothing_passes': 3, 'rotation_reach_px': 4, 'upper_width_radius_px': 6, 'lower_width_radius_px': 4, 'alpha_subpixel_sigma': 0.4, 'alpha_subpixel_mix': 0.7, 'occlusion_aa': 'eye-body gate only; no lash clipping', 'lower_meeting_mode': 'shared five-pin line sampled at native x for both lids', 'lower_flatten': [0.94, 0.94], 'lower_closed_x_scale': [1.0, 1.0], 'lower_closed_x_offset': [0.0, 0.0], 'lower_progress': 'p*(0.7+0.3*p)', 'brow_rigid_follow_px': 6, 'default_upper_thickness': 0.78, 'default_lower_thickness': 1.0, 'closed_pin_x': [[-49, -27.75, -6.5, 14.75, 36], [-31, -15.25, 0.5, 16.25, 32]], 'closed_pin_y': [[8.5, 10.5, 11, 10.5, 8.5], [8.5, 9.8, 10.2, 9.8, 8.5]], 'root_depth_gather': {'x_ranges': [[-38, -15], [5, 25]], 'amount': 0.9, 'method': 'C1 whole cross-section compression evaluated at warped x'}, 'lash_edge_alpha_clipping': False, 'long_tip_min_length': 14.0, 'lash_tip_compress': [0.6, 0.6], 'tip_root': 'native reference ridge plus2px', 'tip_direction_compression': True, 'tip_progress': 'p*(0.85+0.15*p)', 'tip_lateral_radius': [50.0, 40.0], 'guide_resampling': 'source and moving ridges at directionally warped x', 'reference': {'url': 'https://www.bilibili.com/video/BV1rR4y1N7q4', 'seconds': [54, 55], 'cid': 578320471, 'available_reference_resolution': [852, 480], 'timing_policy': 'Close plus reopen to70% together0.3s (0.15+0.15); final30% in1.7s; reference only for shape hierarchy'}}
    metadata['eye_puppet']['deformation_details']['closed_outer_tail_softening']={'root_x': [-35, 20], 'strength': 0.35, 'rolloff_px': 6, 'progress': 'smoothstep(0.55,1.0,p)', 'mapping': 'monotone C1 x gathering for whole lids and eye-body gate; original UV/alpha unchanged'}
    metadata['eye_puppet']['deformation_details']['root_depth_gather']['near_eye_sidewall_excess']={'progress':'p/(p+0.10*(1-p))-p','x_range':[-26,-12],'protected_positive_depth_px':3.0,'rolloff_px':1.0,'method':'Subtract progress*side_weight*excess^2/(excess+1) only from long positive side-wall depth after original root gathering; preserve upper stroke, native x transport and open/closed poses'}
    metadata['eye_puppet']['stationary_hair_ownership']={'source': 'eye-traces.json/stationary_hair_transfers_world', 'method': 'Static alpha-conserving transfer of marked native hair from upper and lower cutouts into StationaryHair; inspect both eyelid mattes for residual hair, no animated clipping', 'right_eye': 'Marked native hair below outer corner transferred from lower-lid into StationaryHair; precise polygon with no color-difference rejection'}
    if (PROJECT/'brow-paths.json').exists():
        paths=json.loads((PROJECT/'brow-paths.json').read_text(encoding='utf-8'))
        metadata['eye_puppet']['manual_lash_contours']={'path':'brow-paths.json','target':'upper_lid',
            'nodes':[len(b['nodes']) for b in paths['brows']],
            'feather_px':[b['feather'] for b in paths['brows']]}
    metadata['eye_puppet']['hidden_underlay']={'source':'assets/chorus-cgc06/eye-clean-plate.png',
        'method':'gpt-image-2 completes both eye-free footprints with continuous native-style skin/hair; registered and gradient-matched to native a; static background only, no generated expression frames',
        'forbidden':'manual color fills or broad skin/hair inpaint ribbons'}
    (OUT/'scene.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    shutil.copy2(OUT/'scene.json',PROJECT/'scene.json')
    print('Prepared scene3: static closed/o, relaxed smile, selective focus, lighting and overscan.')

def camera_coverage():
    meta=json.loads((OUT/'scene.json').read_text(encoding='utf-8'))
    corners=np.array([[0,0],[1920,0],[1920,1080],[0,1080]])
    low=np.full(2,np.inf);high=np.full(2,-np.inf)
    def smooth(a,b,t):
        u=np.clip((t-a)/(b-a),0,1);return u*u*(3-2*u)
    def rotation(t):
        elapsed=max(0.,t-2.55)
        if elapsed<.55:
            u=elapsed/.55
            distance=.55*(u**3-.5*u**4)
        elif t<4.60:distance=elapsed-.275
        else:
            u=np.clip((t-4.60)/1.70,0,1)
            distance=1.775+1.70*(u-u**3+.5*u**4)
        return distance/2.625
    for t in np.arange(-20,379)/60:
        c=meta['closeup'];entry=c['entry_progress_rate'];tail=c['tail_progress_rate'];hold=c['entry_hold'];decel=c['deceleration_seconds']
        elapsed=max(t-hold,0);q=np.clip(elapsed/decel,0,1)
        u=entry*t if t<=hold else entry*hold+tail*elapsed+(entry-tail)*decel*(q-q**3+.5*q**4)
        z=smooth(0,c['slow_start'],t);r=meta['rotation']
        source=np.array(c['source_from'])*(1-u)+np.array(c['source_to'])*u
        zoom=c['scale'][0]*(1-z)+c['scale'][1]*z
        close_position=np.array([960,540])-source*zoom
        wide_angle=math.radians(-10*rotation(t))
        rot=np.array([[math.cos(wide_angle),-math.sin(wide_angle)],[math.sin(wide_angle),math.cos(wide_angle)]])
        wide_position=np.array(r['screen_pivot'])-rot@np.array(r['source_pivot'])*1.65
        for active,position,scale,angle in [
            (t<=meta['timeline']['gaussian_transition'][1],close_position,zoom,0),
            (t>=meta['timeline']['gaussian_transition'][0],wide_position,1.65,wide_angle)]:
            if not active:continue
            corners=np.array([[0,0],[1920,0],[0,1080],[1920,1080]])
            inv=np.array([[math.cos(angle),math.sin(angle)],[-math.sin(angle),math.cos(angle)]])
            p=(corners-position)@inv.T/scale
            low=np.minimum(low,p.min(0));high=np.maximum(high,p.max(0))
    pad=np.array(meta['pad']);size=np.array(meta['source_size'])
    assert np.all(low>=-pad) and np.all(high<=size+pad), 'Camera exceeds painted border'
    return {'status':'passed','samples':399,'includes_incoming_preroll':True,'native_min':low.tolist(),'native_max':high.tolist(),
            'padded_min':(-pad).tolist(),'padded_max':(size+pad).tolist()}

def install():
    movie=OUT/'scene3.avi'
    review=OUT/'Chorus-CGC06-66.000-72.300-song.mp4'
    subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-y','-i',str(movie),
       '-ss','66','-i',str(MAPSET/'audio-balanced.mp3'),'-map','0:v:0','-map','1:a:0',
       '-frames:v','378','-t','6.3','-c:v','libx264','-crf','16','-pix_fmt','yuv420p',
       '-c:a','aac','-b:a','192k','-movflags','+faststart',str(review)],check=True)
    out=MAPSET/'sb/chorus-cgc06';out.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-y','-i',str(movie),
       '-vf','fps=30','-frames:v','189','-q:v','2','-pix_fmt','yuvj444p',
       '-start_number','0',str(out/'frame-%03d.jpg')],check=True)
    rows=[]
    for i in range(189):
        name=f'frame-{i:03d}.jpg'
        with Image.open(out/name) as im: assert im.size==(1920,1080)
        rows.append(f'{name}\t{66000+i*1000/30:.6f}\t{min(72300,66000+(i+1)*1000/30):.6f}')
    text='\n'.join(rows)+'\n'
    (out/'frames.tsv').write_text(text,encoding='utf-8')
    records=ROOT/'assets/chorus-cgc06';records.mkdir(parents=True,exist_ok=True)
    (records/'frames.tsv').write_text(text,encoding='utf-8')
    shutil.copy2(OUT/'scene.json',records/'sources.json')
    probe=json.loads(subprocess.check_output([str(FFPROBE),'-v','error','-count_frames',
       '-show_streams','-show_format','-of','json',str(review)],encoding='utf-8'))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (video['width'],video['height'])==(1920,1080)
    assert video['avg_frame_rate']=='60/1' and int(video['nb_read_frames'])==378
    assert abs(float(video['duration'])-6.3)<.001
    assert abs(float(audio['duration'])-6.3)<.05
    subprocess.run([str(FFMPEG),'-hide_banner','-v','error','-xerror','-i',str(review),
                    '-f','null','-'],check=True)
    # Inspect actual exported frames, including the first frame of the nested
    # viewports, and retain a compact review sheet for expression/camera QA.
    capture=cv2.VideoCapture(str(review))
    times=[0,.70,1.58,2.55,2.825,3.10,4.30,4.45,4.60,5.15,5.75,6.283]
    sheet=Image.new('RGB',(1920,3*300),'#142239')
    detail=Image.new('RGB',(3*590,2*570),'#142239')
    for i,t in enumerate(times):
        capture.set(cv2.CAP_PROP_POS_FRAMES,round(t*60))
        ok,bgr=capture.read();assert ok
        frame=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
        assert float(np.asarray(frame).mean())>5, 'Uninitialized/black render frame'
        x=(i%4)*480;y=(i//4)*300
        sheet.paste(frame.resize((480,270),Image.Resampling.LANCZOS),(x,y+30))
        ImageDraw.Draw(sheet).text((x+8,y+8),f'{66+t:.3f}s',fill='white')
        if i>=6:
            j=i-6;dx=(j%3)*590;dy=(j//3)*570
            detail.paste(frame.crop((1150,100,1740,640)),(dx,dy+30))
            ImageDraw.Draw(detail).text((dx+8,dy+8),f'{66+t:.3f}s',fill='white')
    capture.release()
    sheet.save(OUT/'scene3-contact.jpg',quality=94)
    detail.save(OUT/'slow-blink-detail.jpg',quality=95)
    validation={'video_frames':378,'fps':60,'video_duration':float(video['duration']),
       'audio_duration':float(audio['duration']),'full_decode':'passed',
       'installed_frames':189,'installed_fps':30,'installed_size':[1920,1080],
       'installed_jpeg':{'quality':2,'pixel_format':'yuvj444p','source':'1080p GPU movie'},
       'song_ms':[66000,72300],
       'first_frame':'nonblack','camera_coverage':camera_coverage(),'visual_acceptance':'pending'}
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(review)
    print('Installed 189 native 1920x1080 Storybrew frames, exactly 66000–72300ms.')

def join_previous():
    previous=ROOT/'_preview/chorus-photo-phone/final.avi'
    incoming=ROOT/'godot/chorus-phone/assets/incoming-cgc06.png'
    assert incoming.exists(), 'Prepare the CGC06 incoming frame before rendering the phone shot'
    full=OUT/'Chorus-Linked-59.200-72.300-song.mp4'
    short=OUT/'Chorus-Linked-End-64.800-72.300-song.mp4'
    # 204 phone frames at 30fps end exactly at 66.000; the new shot contributes
    # 378 frames at 60fps. Use one continuous song excerpt across the join.
    graph=('[0:v]trim=end_frame=204,setpts=PTS-STARTPTS,fps=60,scale=1920:1080:flags=lanczos,setsar=1[a];'
           '[1:v]trim=end_frame=378,setpts=PTS-STARTPTS,setsar=1[b];[a][b]concat=n=2:v=1:a=0[joined];[joined]fps=60[v]')
    subprocess.run([str(FFMPEG),'-hide_banner','-v','error','-y','-i',str(previous),
        '-i',str(OUT/'scene3.avi'),'-ss','59.2','-i',str(MAPSET/'audio-balanced.mp3'),
        '-filter_complex',graph,'-map','[v]','-map','2:a:0','-frames:v','786','-t','13.1',
        '-r','60','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
        '-movflags','+faststart',str(full)],check=True)
    subprocess.run([str(FFMPEG),'-hide_banner','-v','error','-y','-ss','5.6','-i',str(full),
        '-frames:v','450','-t','7.5','-r','60','-c:v','libx264','-crf','16','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',str(short)],check=True)
    results=[]
    for path,count,duration in [(full,786,13.1),(short,450,7.5)]:
        probe=json.loads(subprocess.check_output([str(FFPROBE),'-v','error','-count_frames',
            '-show_streams','-of','json',str(path)],encoding='utf-8'))
        v=next(s for s in probe['streams'] if s['codec_type']=='video')
        a=next(s for s in probe['streams'] if s['codec_type']=='audio')
        assert (v['width'],v['height'],v['avg_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'60/1',count)
        assert abs(float(v['duration'])-duration)<.001 and abs(float(a['duration'])-duration)<.05
        subprocess.run([str(FFMPEG),'-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
        results.append({'file':path.name,'frames':count,'duration':duration,'full_decode':'passed'})
    capture=cv2.VideoCapture(str(full));sheet=Image.new('RGB',(1920,600),'#142239')
    for i,t in enumerate([65.20,65.667,65.90,65.967,66.0,66.10,66.85,67.72]):
        capture.set(cv2.CAP_PROP_POS_FRAMES,round((t-59.2)*60))
        ok,frame=capture.read();assert ok
        x=(i%4)*480;y=(i//4)*300
        sheet.paste(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).resize((480,270)),(x,y+30))
        ImageDraw.Draw(sheet).text((x+8,y+8),f'{t:.3f}s',fill='white')
    capture.release();sheet.save(OUT/'linked-cut-contact.jpg',quality=95)
    shutil.copy2(short,OUT/'Chorus-Linked-End-Native-Detail-64.800-72.300-song.mp4')
    shutil.copy2(full,OUT/'Chorus-Linked-Native-Detail-59.200-72.300-song.mp4')
    shutil.copy2(short,OUT/'Chorus-Linked-End-Whole-Cutout-64.800-72.300-song.mp4')
    shutil.copy2(full,OUT/'Chorus-Linked-Whole-Cutout-59.200-72.300-song.mp4')
    shutil.copy2(short,OUT/'Chorus-Linked-End-Curve-Frame-64.800-72.300-song.mp4')
    shutil.copy2(full,OUT/'Chorus-Linked-Curve-Frame-59.200-72.300-song.mp4')
    shutil.copy2(short,OUT/'Chorus-Linked-End-Restrained-64.800-72.300-song.mp4')
    shutil.copy2(full,OUT/'Chorus-Linked-Restrained-59.200-72.300-song.mp4')
    shutil.copy2(short,OUT/'Chorus-Linked-End-Native-Tips-64.800-72.300-song.mp4')
    shutil.copy2(full,OUT/'Chorus-Linked-Native-Tips-59.200-72.300-song.mp4')
    (OUT/'linked-validation.json').write_text(json.dumps({'join_song_seconds':66.0,
        'incoming':'CGC06 camera preroll matches shot-three position and velocity; no CGC14 placeholder',
        'audio':'one continuous song excerpt','previews':results},indent=2),encoding='utf-8')
    print(full);print(short)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true')
    parser.add_argument('--join-previous',action='store_true')
    parser.add_argument('--eyes-only',action='store_true',help='Rebuild native eye parts using saved pen contours')
    args=parser.parse_args()
    if args.eyes_only:
        native_eye_layers(rgb(ASSETS/'a-plate.png'))
        print('Native eye parts rebuilt from saved contours.')
    else:
        join_previous() if args.join_previous else install() if args.install else prepare()
