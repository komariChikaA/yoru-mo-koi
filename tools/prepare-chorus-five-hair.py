"""Prepare native CGC16 hair layers, retaining the clean petal plate unchanged.

The authored polygons and joint chains live in chorus-five/hair-regions.json.
The full moving footprint is replaced by an authored hidden-surface redraw.
The original painting outside the footprint and fixed root bands is retained.
Roots (first 15 percent) and both ends of return loops stay fixed. Bangs, face,
scalp and the two hair accessories are outside this stage's masks.
"""
from pathlib import Path
import argparse
import json
import runpy

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/"godot/chorus-five/assets"
DEFINITION=ROOT/"godot/chorus-five/hair-regions.json"
SIZE=(1920,1080)
REDRAW=ASSETS/"hair-redraw"


def polygon_mask(points):
    # Oversampling keeps narrow curved hair boundaries antialiased.
    im=Image.new("L",(SIZE[0]*3,SIZE[1]*3))
    ImageDraw.Draw(im).polygon([(round(x*3),round(y*3)) for x,y in points],fill=255)
    return np.asarray(im.resize(SIZE,Image.Resampling.LANCZOS))


def chain_position(points, rect):
    x,y,w,h=rect
    yy,xx=np.mgrid[y:y+h,x:x+w]
    best=np.full((h,w),np.inf)
    result=np.zeros((h,w),np.float32)
    pts=np.asarray(points,np.float32)
    lengths=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    total=max(float(lengths.sum()),1)
    elapsed=0.0
    for i,length in enumerate(lengths):
        a,b=pts[i:i+2]
        dx,dy=b-a
        u=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/max(length*length,.001),0,1)
        d=(xx-a[0]-u*dx)**2+(yy-a[1]-u*dy)**2
        hit=d<best
        result[hit]=(elapsed+u[hit]*length)/total
        best[hit]=d[hit]
        elapsed+=length
    return result


def native_fan_mask(src, outline):
    """Separate the actual blonde fan, not the jacket inside a rough fork."""
    envelope=np.zeros((1080,1920),np.uint8)
    cv2.fillConvexPoly(envelope,cv2.convexHull(np.asarray(outline,np.int32)),255)
    envelope=cv2.dilate(envelope,np.ones((5,5),np.uint8))
    r,g,b=[src[...,i].astype(np.int16) for i in range(3)]
    gold=(r>130)&(g>90)&(g-b>-12)&(r-b>12)
    seeds=(gold&(envelope>0)).astype(np.uint8)
    seeds=cv2.morphologyEx(seeds,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,_=cv2.findContours(seeds,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    body=np.zeros_like(envelope)
    for contour in contours:
        if cv2.contourArea(contour)>30:cv2.drawContours(body,[contour],-1,255,cv2.FILLED)
    body=cv2.dilate(body,np.ones((3,3),np.uint8))
    # Fit away single-pixel colour-threshold teeth, keeping acute fork tips.
    # Rasterize the fitted contour at 4x instead of blurring the painted RGB.
    contours,_=cv2.findContours(body,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    smooth=Image.new("L",(1920*4,1080*4));draw=ImageDraw.Draw(smooth)
    for contour in contours:
        points=cv2.approxPolyDP(contour,.9,True)[:,0].astype(float)
        if len(points)<3:continue
        path=[]
        for i,b in enumerate(points):
            a=points[i-1];c=points[(i+1)%len(points)]
            u=a-b;v=c-b;lu=np.linalg.norm(u);lv=np.linalg.norm(v)
            radius=min(2,lu*.25,lv*.25)
            if lu*lv==0 or np.dot(u,v)/(lu*lv)>.7:
                path.append(b);continue
            start=b+u/lu*radius;end=b+v/lv*radius
            for t in np.linspace(0,1,7):path.append((1-t)**2*start+2*t*(1-t)*b+t*t*end)
        draw.polygon([(round(p[0]*4),round(p[1]*4)) for p in path],fill=255)
    return np.minimum(np.asarray(smooth.resize(SIZE,Image.Resampling.LANCZOS)),envelope)


def restore_loop_profile(src, mask, top=472, bottom=515):
    """Continue both native band edges and highlights through the old petal."""
    bounds={}
    for y in range(top,bottom+1):
        xx=np.flatnonzero(mask[y]>110)
        bounds[y]=(float(xx.min()),float(xx.max()))
    donor_bounds={}
    for y in [top,bottom]:
        left,right=bounds[y]
        xs=np.arange(max(0,int(left)-3),min(1920,int(right)+4))
        r,g,b=[src[y,xs,i].astype(np.int16) for i in range(3)]
        gold=(r>135)&(g>80)&(r-g>6)&(g-b>-8)
        selected=xs[gold]
        donor_bounds[y]=(float(selected.min()),float(selected.max())) if len(selected)>1 else bounds[y]
    repaired=src.copy()
    for y in range(top,bottom+1):
        left,right=bounds[y]
        xs=np.arange(max(0,int(left)),min(1920,int(right)+1))
        u=(xs-left)/max(1,right-left)
        samples=[]
        for donor in [top,bottom]:
            a,b=donor_bounds[donor]
            samples.append(cv2.remap(src,(a+u*(b-a)).astype(np.float32)[None,:],
                np.full((1,len(xs)),donor,np.float32),cv2.INTER_LINEAR)[0])
        t=(y-top)/(bottom-top);t=t*t*(3-2*t)
        repaired[y,xs]=np.rint(samples[0]*(1-t)+samples[1]*t).astype(np.uint8)
    weight=np.zeros(mask.shape,np.float32)
    weight[top:bottom+1]=mask[top:bottom+1]/255
    for y in range(top,bottom+1):
        weight[y]*=min(1,(y-top)/4,(bottom-y)/4)
    return np.rint(src*(1-weight[...,None])+repaired*weight[...,None]).clip(0,255).astype(np.uint8)


def restore_loop_petals(src, mask):
    """Continue the thin and broad branches independently across the old petal."""
    top,bottom=460,530
    def runs(row):
        xs=np.flatnonzero(mask[row]>128)
        return [p for p in np.split(xs,np.flatnonzero(np.diff(xs)>1)+1) if len(p)>1]
    donors=[runs(top),runs(bottom)]
    result=src.copy()
    for y in range(top,bottom+1):
        for j,xs in enumerate(runs(y)):
            if j>=min(len(p) for p in donors):continue
            u=(xs-xs.min())/max(1,xs.max()-xs.min())
            samples=[]
            for row,groups in zip([top,bottom],donors):
                p=groups[j]
                samples.append(cv2.remap(src,(p.min()+u*(p.max()-p.min())).astype(np.float32)[None,:],np.full((1,len(xs)),row,np.float32),cv2.INTER_LINEAR)[0])
            t=(y-top)/(bottom-top);t=t*t*(3-2*t)
            weight=min(1,(y-top)/6,(bottom-y)/6)
            result[y,xs]=np.rint(src[y,xs]*(1-weight)+(samples[0]*(1-t)+samples[1]*t)*weight).astype(np.uint8)
    return result


def continue_fan_under_curl(src):
    """Replace the complete rear-fan contact patch, preserving continuous lines."""
    x,y,w,h=1240,398,215,160
    patch=np.asarray(Image.open(ASSETS/"cut-repairs/fan-registered.png").convert("RGB"))
    yy,xx=np.mgrid[:h,:w]
    weight=np.clip(np.minimum.reduce([xx,yy,w-1-xx,h-1-yy])/5,0,1)
    result=src.copy()
    result[y:y+h,x:x+w]=np.rint(src[y:y+h,x:x+w]*(1-weight[...,None])+patch*weight[...,None]).astype(np.uint8)
    return result


def restore_arc_petals(src, mask):
    """Continue the arc cross-section through the old foreground petal."""
    result=src.copy()
    lo,hi=1410,1480
    ends=[]
    for x in [lo,hi]:
        ys=np.flatnonzero(mask[:,x]>128)
        ends.append((ys.min(),ys.max()))
    for x in range(lo,hi+1):
        ys=np.flatnonzero(mask[:,x]>0)
        if not len(ys):continue
        u=(ys-ys.min())/max(1,ys.max()-ys.min())
        profiles=[]
        for donor,(top,bottom) in zip([lo,hi],ends):
            profiles.append(cv2.remap(src,np.full((len(ys),1),donor,np.float32),(top+u*(bottom-top)).astype(np.float32)[:,None],cv2.INTER_LINEAR)[:,0])
        t=(x-lo)/(hi-lo)
        profile=profiles[0]*(1-t)+profiles[1]*t
        weight=mask[ys,x]/255*min(1,(x-lo)/4,(hi-x)/4)
        result[ys,x]=np.rint(src[ys,x]*(1-weight[:,None])+profile*weight[:,None]).astype(np.uint8)
    return result


def continue_rear_arc_under_curl(src, curl, arc):
    """Continue the narrow rear band through the S's original crossing.

    Its hidden root belongs to the rear band, so retaining the source pixels
    there would retain a short second copy of the foreground S.
    """
    yy,xx=np.mgrid[:1080,:1920].astype(np.float32)
    # Follow the rising native band, using intact cross-sections on both
    # sides of the foreground lock.  Retain their cream/brown edge profile.
    left_x,right_x=1310.0,1400.0
    slope=-.16
    left=cv2.remap(src,np.full_like(xx,left_x),yy+slope*(left_x-xx),
                   cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    right=cv2.remap(src,np.full_like(xx,right_x),yy+slope*(right_x-xx),
                    cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    t=np.clip((xx-left_x)/(right_x-left_x),0,1)[...,None]
    continued=left*(1-t)+right*t
    # The cast edge extends beyond the curl alpha.  Continue the whole
    # crossing corridor, including that old vertical brown shadow.
    weight=np.minimum(np.clip((xx-1317)/3,0,1),
                      np.clip((1398-xx)/3,0,1))
    weight*=arc.astype(np.float32)/255
    return np.rint(src*(1-weight[...,None])+continued*weight[...,None]).clip(0,255).astype(np.uint8)


def restore_fixed_fan_connection(clean, src, curl, fan):
    """Restore the fixed pink connector above the free fan's cut line.

    The original S crosses this connector before crossing the free fan.  The
    connector is outside the moving fan alpha, so jacket-only cleanup leaves
    a hard red S-shaped cut through the fixed hair when the S swings away.
    """
    # Keep the fixed rear ribbon linking the shoulder hair to the arc root.
    # This strip is behind the S, but is not part of the free fan mask.
    fixed=polygon_mask([(1215,388),(1245,392),(1274,390),(1300,387),
        (1325,381),(1338,379),(1342,404),(1325,416),(1298,419),
        (1265,415),(1235,405)]).astype(np.float32)/255
    clean=np.rint(clean*(1-fixed[...,None])+src*fixed[...,None]).astype(np.uint8)
    # The connector tapers towards the upper edge of the native free fan;
    # the real jacket above it stays red.  Reconstruct only the S crossing.
    connector=polygon_mask([(1296,402),(1310,397),(1326,395),
        (1340,395),(1353,402),(1365,414),(1380,428),
        (1390,433),(1390,447),(1296,428)])
    yy,xx=np.mgrid[:1080,:1920].astype(np.float32)
    # Use an intact native cross-section.  The moving-fan helper starts at
    # y402 and cannot restore the fixed band above its separate cut line.
    continued=cv2.remap(src,np.full_like(xx,1308),yy+.16*(xx-1308),
        cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    crossing=cv2.dilate((curl>8).astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
    weight=cv2.GaussianBlur(crossing.astype(np.float32),(0,0),.8)
    weight*=connector.astype(np.float32)/255
    weight*=1-fan.astype(np.float32)/255
    return np.rint(clean*(1-weight[...,None])+continued*weight[...,None]).clip(0,255).astype(np.uint8)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=ASSETS/"source-clean.png")
    args=parser.parse_args()
    plate_path=REDRAW/"redraw-no-petals.png"
    if not plate_path.exists():
        raise FileNotFoundError("Prepare the authored hidden-surface redraw in assets/hair-redraw; see docs/chorus-five-scene.md")
    redraw=np.array(Image.open(plate_path).convert("RGB").resize(SIZE,Image.Resampling.LANCZOS))
    for name,(x,y,w,h) in [("coat",(1260,240,360,520)),("building",(900,780,130,170))]:
        sharp=np.asarray(Image.open(ASSETS/"sharp-repairs"/(name+"-registered.png")).convert("RGB"),np.float32)
        yy,xx=np.mgrid[:h,:w]
        weight=np.clip(np.minimum.reduce([xx,yy,w-1-xx,h-1-yy])/4,0,1).astype(np.float32)
        if name=="building":
            # The fixed ribbon is restored from native pixels in the front
            # card, so a generated second contour must not enter the backplate.
            r,g,b=[sharp[...,i] for i in range(3)]
            ribbon=((r<125)&(g<105)&(b<145)&(r-g>5)&(b-g>5)).astype(np.uint8)
            weight*=1-cv2.dilate(ribbon,np.ones((3,3),np.uint8))
        redraw[y:y+h,x:x+w]=np.rint(redraw[y:y+h,x:x+w]*(1-weight[...,None])+sharp*weight[...,None]).clip(0,255).astype(np.uint8)
    # This input is already a complete petal-free hidden-surface repaint.
    # Sampling only the original petal coordinates would leave relocated
    # petals from the earlier generated plate baked behind the moving hair.
    Image.fromarray(redraw).save(REDRAW/"hidden-surfaces-no-petals.png")
    src=np.asarray(Image.open(args.source).convert("RGB"))
    if src.shape[:2]!=(1080,1920): raise ValueError("Expected CGC16 1920x1080")
    definition=json.loads(DEFINITION.read_text(encoding="utf8"))
    for part in definition["parts"]:
        if part["id"] in ["left-tail-thin","left-tail-wide"]:
            src=restore_loop_profile(src,polygon_mask(part["outline"]),790,910 if part["id"]=="left-tail-thin" else 880)
        if part["id"]=="right-upper-ponytail-front-curl":
            src=restore_loop_profile(src,polygon_mask(part["outline"]),295,345)
        if part["id"]=="blouse-right-under-tail":
            src=restore_loop_profile(src,polygon_mask(part["outline"]),870,910)
    old=runpy.run_path(str(ROOT/"tools/prepare-chorus-five.py"))
    out=ASSETS/"hair";out.mkdir(parents=True,exist_ok=True)
    clean=src.copy()
    overlay=src.astype(np.float32)
    all_parts=[]
    full_masks=[]
    part_masks={}
    redraw_masks=[]
    root_masks=[]
    for part in definition["parts"]:
        points=part.get("outline",old.get(part.get("reuse_outline","")))
        if points is None: raise ValueError(part["id"]+": no outline")
        mask=polygon_mask(points)
        if part["id"]=="right-main-fan-forked-ends":
            fan_source=continue_fan_under_curl(src)
            mask=native_fan_mask(fan_source,points)
        for exclusion in part.get("exclude",[]):
            mask=np.minimum(mask,255-polygon_mask(exclusion))
        if part.get("color_refine"):
            r,g,b=[src[...,i].astype(np.int16) for i in range(3)]
            warm=((r-g)>12)&((g-b)>0)
            warm=cv2.morphologyEx(warm.astype(np.uint8),cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
            warm=cv2.dilate(warm,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
            mask=np.minimum(mask,cv2.GaussianBlur(warm.astype(np.float32),(0,0),.5)*255).astype(np.uint8)
            # Isolated warm blossom pixels are not part of a native hair lock.
            count,labels,stats,_=cv2.connectedComponentsWithStats((mask>55).astype(np.uint8),8)
            if count>1:
                cutoff=max(8,int(stats[1:,cv2.CC_STAT_AREA].max()*.025))
                keep=np.isin(labels,[i for i in range(1,count) if stats[i,cv2.CC_STAT_AREA]>=cutoff])
                keep=cv2.dilate(keep.astype(np.uint8),np.ones((3,3),np.uint8))
                mask=np.minimum(mask,keep*255)
        ys,xs=np.nonzero(mask>2)
        x0,x1=max(int(xs.min())-3,0),min(int(xs.max())+4,1920)
        y0,y1=max(int(ys.min())-3,0),min(int(ys.max())+4,1080)
        rect=[x0,y0,x1-x0,y1-y0]
        cmask=mask[y0:y1,x0:x1]
        full_masks.append(mask)
        part_masks[part["id"]]=mask
        progress=chain_position(part["chain"],rect)
        # Clear the entire original moving lock, including its interior and
        # antialiased contour. Fixed roots continue underneath the moving mesh.
        released=np.clip((progress-.13)/.12,0,1)
        released=released*released*(3-2*released)
        repaint=np.zeros((1080,1920),np.float32)
        repaint[y0:y1,x0:x1]=cmask.astype(np.float32)/255*released
        repaint=cv2.dilate(repaint,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
        repaint=cv2.GaussianBlur(repaint,(0,0),1.4)
        redraw_masks.append(repaint)
        root=np.zeros((1080,1920),np.float32)
        root[y0:y1,x0:x1]=cmask.astype(np.float32)/255*(1-released)
        root_masks.append(root)
        texture_source=src
        if part["id"]=="blouse-left-under-tail":
            # Complete the hidden tapered end behind the fixed skirt; never
            # attach pixels from the skirt to a moving hair lock.
            texture_source=src.copy()
            donor=np.flatnonzero(mask[960]>128)
            for row in range(965,1017):
                xs=np.flatnonzero(mask[row]>0)
                if not len(xs):continue
                u=(xs-xs.min())/max(1,xs.max()-xs.min())
                sample=cv2.remap(src,(donor.min()+u*(donor.max()-donor.min())).astype(np.float32)[None,:],np.full((1,len(xs)),960,np.float32),cv2.INTER_LINEAR)[0]
                blend=min(1,(row-965)/7)
                texture_source[row,xs]=np.rint(src[row,xs]*(1-blend)+sample*blend).astype(np.uint8)
        if part["id"]=="left-loop":texture_source=restore_loop_petals(src,mask)
        if part["id"]=="right-main-fan-forked-ends":
            # The original S-shaped foreground lock lies across this fan.
            # Its pixels belong to that independently moving layer; continue
            # the rear fan beneath it rather than duplicating the moving curl.
            curl=part_masks.get("right-upper-ponytail-front-curl")
            if curl is not None:
                texture_source=fan_source
            r,g,b=[texture_source[...,i].astype(np.int16) for i in range(3)]
            native=(mask>128)&(r>70)&(r-b>8)&(g-b>-15)
            _,nearest=distance_transform_edt(~native,return_indices=True)
            rim=(mask>0)&(mask<250)&~native
            texture_source=texture_source.copy()
            texture_source[rim]=texture_source[nearest[0][rim],nearest[1][rim]]
        if part["id"]=="right-rear-fine-arc":
            curl=part_masks.get("right-upper-ponytail-front-curl")
            if curl is not None:
                texture_source=restore_arc_petals(continue_rear_arc_under_curl(src,curl,mask),mask)
        if part["id"] in ["left-tail-thin","left-tail-wide","blouse-left-under-tail","blouse-right-under-tail"]:
            # Traced edges retain pale/purple tips. Extend native hair RGB into
            # the alpha rim instead of moving blue building pixels with it.
            r,g,b=[texture_source[...,i].astype(np.int16) for i in range(3)]
            native=(mask>128)&(r-g>12)&(r-b>5)&(r>80)
            _,nearest=distance_transform_edt(~native,return_indices=True)
            contaminated=(mask>0)&~native
            texture_source=texture_source.copy()
            texture_source[contaminated]=texture_source[nearest[0][contaminated],nearest[1][contaminated]]
        rgba=np.dstack([texture_source[y0:y1,x0:x1],cmask])
        Image.fromarray(rgba).save(out/(part["id"]+".png"))
        item={key:part[key] for key in ["id","chain","amplitude_px","response_delay","propagation","frequency_hz","pin_tip","depth","cut_line","root_band"]}
        item.update(texture="res://assets/hair/"+part["id"]+".png",rect=rect)
        all_parts.append(item)
        tint=np.array([(81+len(all_parts)*49)%200+55,(165+len(all_parts)*39)%200+55,(63+len(all_parts)*73)%200+55])
        a=mask[...,None]/255*.32
        overlay=overlay*(1-a)+tint*a
    # Replace all previous smear/inpaint repairs with the complete redraw.
    # Use only the authored repair domains, never the generated full frame.
    # The fixed foreground continues to use untouched original pixels.
    redraw_weight=np.maximum.reduce(redraw_masks)
    for region in definition["redraw_regions"]:
        solid=polygon_mask(region).astype(np.float32)/255
        solid=cv2.GaussianBlur(solid,(0,0),5)
        redraw_weight=np.maximum(redraw_weight,solid)
    redraw_weight*=1-np.maximum.reduce(root_masks)
    clean=np.rint(src*(1-redraw_weight[...,None])+redraw*redraw_weight[...,None]).clip(0,255).astype(np.uint8)
    clean=restore_fixed_fan_connection(clean,src,
        part_masks["right-upper-ponytail-front-curl"],
        part_masks["right-main-fan-forked-ends"])
    Image.fromarray(clean).save(out/"source-hair-clean.png")
    Image.fromarray(np.rint(redraw_weight*255).astype(np.uint8)).save(out/"redraw-mask.png")
    hair_union=np.maximum.reduce(full_masks)
    # Rear particles see the fixed bodies, rather than the old hair silhouette.
    original_occ=np.asarray(Image.open(ASSETS/"occlusion.png").convert("L"))
    male=polygon_mask(old["RIGHT_PERSON"])
    for gap in old["BACKGROUND_GAPS"][7:]:
        male=np.minimum(male,255-polygon_mask(gap))
    original_body=old["HEAD_AND_BODY"]
    # Use the girl's actual fixed head/blouse edge, rather than the outer fan
    # envelope: the large red triangles between the fan and ponytail are the
    # man's jacket and must remain behind the moving hair.
    girl_body=(original_body[:original_body.index((1091,82))+1]+
        [(1095,122),(1086,155),(1094,205),(1115,259),(1146,305),
         (1191,348),(1240,376),(1260,385),(1230,390),(1195,395),
         (1185,410),(1207,440),(1225,474),(1244,507),(1268,548),
         (1280,580),(1286,616),(1297,650),(1315,687),(1335,726),
         (1360,759),(1390,801)]+
        original_body[original_body.index((1393,806)):])
    foreground=polygon_mask(girl_body)
    for gap in old["BACKGROUND_GAPS"]:
        foreground=np.minimum(foreground,255-polygon_mask(gap))
    foreground=np.minimum(foreground,255-cv2.dilate(hair_union,np.ones((3,3),np.uint8)))
    # The fixed body outline encloses the return loop's narrow inner opening.
    # Clearing only its hair alpha leaves an original pink/gold crescent and
    # lower shadow triangle in front of the moving lock.  Neither is a fixed
    # body part: release the full loop envelope, then restore the real hand
    # below.
    ly,lx=np.nonzero(part_masks["left-loop"]>8)
    loop_envelope=np.zeros_like(foreground)
    cv2.fillConvexPoly(loop_envelope,
        cv2.convexHull(np.column_stack([lx,ly]).astype(np.int32)),255)
    loop_envelope=cv2.dilate(loop_envelope,np.ones((3,3),np.uint8))
    foreground=np.minimum(foreground,255-loop_envelope)
    hand=polygon_mask([(489,640),(500,632),(523,637),(546,641),(573,635),
        (597,629),(572,605),(566,595),(573,592),(597,610),(617,619),
        (645,626),(671,632),(689,631),(710,641),(736,675),(750,713),
        (758,747),(745,773),(716,788),(692,786),(679,775),(663,758),
        (651,740),(643,723),(639,705),(617,703),(585,702),(561,699),
        (542,693),(529,684),(519,672),(503,664),(496,652)])
    yy,xx=np.mgrid[:1080,:1920]
    r,g,b=[src[...,i].astype(np.int16) for i in range(3)]
    white=((b>=g-5)&(r-b<45)&(r+g+b>410)&
           (xx>730)&(xx<1380)&(yy>390)&(yy<870))
    white=np.minimum(white.astype(np.uint8)*255,polygon_mask(girl_body))
    skirt=polygon_mask([(900,975),(970,967),(970,1080),(921,1080),
        (882,1051),(860,1023),(852,1001),(857,987),(876,979)])
    # The diagonal dark ribbon crosses the rear lock. Restore its own native
    # contour in front, including the portion covered by the hair clean-out.
    front_src=np.asarray(Image.open(args.source).convert("RGB"))
    fr,fg,fb=[front_src[...,i].astype(np.int16) for i in range(3)]
    strap_area=polygon_mask([(1028,823),(1038,831),(1001,859),(979,886),
        (969,907),(975,915),(1007,928),(1003,941),(958,923),(951,914),
        (957,890),(975,866),(1000,844)])
    strap=((fr<120)&(fg<100)&(fb<140)&(fr-fg>5)&(fb-fg>5)).astype(np.uint8)*255
    strap=np.minimum(strap_area,cv2.dilate(strap,np.ones((3,3),np.uint8)))
    foreground=np.maximum.reduce([foreground,hand,white,skirt,strap])
    static_occ=np.minimum(original_occ,255-hair_union)
    static_occ=np.maximum.reduce([static_occ,male,foreground])
    Image.fromarray(static_occ).save(out/"occlusion.png")
    Image.fromarray(foreground).save(out/"foreground.png")
    manifest={"source_size":list(SIZE),"clean_path":"res://assets/hair/source-hair-clean.png",
              "root_fixed_fraction":.15,"foreground_source":"res://assets/source-clean.png",
              "occlusion_path":"res://assets/hair/occlusion.png",
              "foreground_mask":"res://assets/hair/foreground.png",
              "front_occlusion_path":"res://assets/hair/foreground.png","parts":all_parts}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
    overlay_im=Image.fromarray(overlay.clip(0,255).astype(np.uint8))
    draw=ImageDraw.Draw(overlay_im)
    for part in all_parts:
        draw.line([tuple(p) for p in part["chain"]],fill=(20,240,255),width=2)
        draw.text(tuple(part["chain"][0]),part["id"],fill=(20,40,60),stroke_width=1,stroke_fill=(255,255,255))
    overlay_im.save(out/"mask-overlay.jpg",quality=95)
    board=Image.new("RGB",(480*3,330*((len(all_parts)+2)//3)),(66,71,80))
    for index,part in enumerate(all_parts):
        tile=Image.new("RGB",(480,330),(58,64,74))
        d=ImageDraw.Draw(tile)
        for iy in range(0,330,15):
            for ix in range(0,480,15):
                if (iy//15+ix//15)%2:d.rectangle((ix,iy,ix+14,iy+14),fill=(88,93,102))
        d.text((8,7),part["id"],fill="white")
        thumb=Image.open(out/(part["id"]+".png"));thumb.thumbnail((460,290))
        tile.paste(thumb,((480-thumb.width)//2,30+(290-thumb.height)//2),thumb)
        board.paste(tile,((index%3)*480,(index//3)*330))
    board.save(out/"alpha-review.jpg",quality=95)
    review=Image.new("RGB",(1920,2160));review.paste(Image.fromarray(src),(0,0));review.paste(Image.fromarray(clean),(0,1080))
    review.save(out/"clean-review.jpg",quality=95)
    print(f"Prepared {len(all_parts)} native hair parts; roots fixed 0..15%; bangs and face remain static")


if __name__=="__main__":main()
