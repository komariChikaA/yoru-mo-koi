"""Native CGC14 cutouts, region-calibrated wind and continuous eyelid assets."""
from pathlib import Path
import importlib.util
import json
import cv2
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'godot/chorus-four'
ASSETS=PROJECT/'assets'
SIZE=(1920,1080)

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def regions():
    original=json.loads((PROJECT/'hair-regions.json').read_text())['CGC14']
    arch=original[0].copy()
    arch.update(region='left-front',sway_percent=30,response=7.4)
    defs = [
      dict(name='left-back-high',region='left-back',sway_percent=60,phase=.3,
        outline='M1050,76 C976,44 893,4 807,20 C772,26 749,38 743,48 C785,12 847,20 912,43 C960,59 1005,81 1030,91 Z',
        chain=[[1042,82],[959,56],[880,31],[800,29],[750,45]],root_pin=[12,30]),
      dict(name='left-back-middle',region='left-back-center',sway_percent=44,phase=.7,
        outline='M1435,107 C1310,171 1242,160 1125,121 C1029,88 932,46 846,51 C751,52 674,77 644,105 C704,59 787,64 854,71 C968,84 1034,119 1120,148 C1245,192 1336,182 1435,136 Z',
        chain=[[1430,122],[1230,156],[1038,113],[828,61],[652,101]],root_pin=[35,75]),
      dict(name='left-back-wide',region='left-back',sway_percent=60,phase=1.5,
        outline='M1440,242 C1290,290 1167,253 1049,220 C922,186 822,186 749,222 C695,249 659,281 630,321 C650,258 700,225 766,207 C877,173 980,205 1095,230 C1216,257 1310,272 1440,222 Z',
        chain=[[1434,235],[1220,271],[1014,218],[800,217],[638,310]],root_pin=[40,90]),
      arch,
      dict(name='left-front-lower',region='left-front-center',sway_percent=22,phase=2.1,
        outline='M1430,277 C1260,304 1110,295 1011,300 C920,303 836,311 792,338 C783,343 786,348 791,350 C785,341 848,328 902,321 C1076,298 1230,339 1430,293 Z',
        chain=[[1423,284],[1235,313],[1044,306],[893,319],[791,344]],root_pin=[25,65]),
      dict(name='right-back-fine',region='right-back',sway_percent=70,phase=1.3,
        outline='M1800,95 C1832,41 1784,-6 1730,0 C1610,-12 1490,26 1430,102 C1496,39 1614,9 1730,14 C1790,17 1814,48 1800,95 Z',
        chain=[[1465,77],[1570,19],[1700,6],[1784,28],[1805,86]],root_pin=[30,65]),
      dict(name='right-back-outer',region='right-back',sway_percent=70,phase=2.6,
        outline='M1830,418 C1781,483 1748,571 1732,645 C1720,706 1732,766 1686,792 C1653,814 1600,784 1568,756 C1614,786 1662,808 1696,778 C1731,740 1711,691 1722,637 C1737,547 1770,474 1814,430 Z',
        chain=[[1820,430],[1768,543],[1722,665],[1709,765],[1655,794],[1578,759]],root_pin=[30,70]),
      dict(name='right-back-bottom-curl',region='right-back',sway_percent=70,phase=3.1,
        outline='M1599,930 C1595,1001 1571,1059 1534,1069 C1487,1082 1438,1035 1390,1020 C1365,1012 1347,1018 1337,1028 C1352,1001 1380,1000 1404,1012 C1460,1035 1500,1058 1534,1045 C1568,1031 1577,976 1583,930 Z',
        chain=[[1591,937],[1578,1007],[1534,1058],[1444,1039],[1344,1024]],root_pin=[20,45]),
      dict(name='right-front-arm-loop',region='right-front',sway_percent=15,phase=.8,response=9,
        outline='M1755,470 C1692,542 1655,635 1667,716 C1673,770 1692,823 1693,862 C1697,910 1678,934 1634,933 C1568,930 1503,883 1449,887 C1360,890 1250,883 1175,922 C1137,943 1112,957 1100,967 C1110,934 1167,900 1225,878 C1295,852 1378,870 1447,872 C1530,866 1600,907 1660,906 C1683,897 1674,862 1669,827 C1652,740 1645,689 1659,625 C1675,549 1711,496 1755,470 Z',
        chain=[[1745,480],[1674,630],[1677,767],[1680,882],[1480,879],[1260,875],[1104,959]],root_pin=[35,80]),
      dict(name='right-front-shoulder',region='right-front',sway_percent=15,phase=1.9,response=10,
        outline='M1748,414 C1689,462 1614,496 1544,519 C1491,538 1443,548 1409,579 C1423,551 1471,531 1515,515 C1618,478 1671,459 1721,421 Z',
        chain=[[1734,422],[1660,474],[1575,509],[1488,541],[1415,571]],root_pin=[25,65]),
      dict(name='right-front-upper-filament',region='right-front',sway_percent=15,phase=2.4,response=10,
        outline='M1670,889 C1590,904 1510,846 1440,842 C1365,836 1360,868 1285,855 C1230,843 1190,829 1157,845 C1220,830 1260,861 1312,866 C1378,872 1399,849 1450,854 C1520,861 1590,909 1670,902 Z',
        chain=[[1665,895],[1530,872],[1435,848],[1300,858],[1170,841]],root_pin=[20,45]),
      dict(name='bang-left',region='bangs',sway_percent=10,phase=.4,response=12,
        outline='M1644,78 C1580,99 1527,153 1486,212 C1463,245 1443,269 1424,290 C1434,254 1464,210 1486,183 C1532,126 1591,89 1644,78 Z',
        chain=[[1639,84],[1577,120],[1517,176],[1466,241],[1428,284]],root_pin=[50,95]),
      dict(name='bang-center',region='bangs',sway_percent=10,phase=1.4,response=12,
        outline='M1743,161 C1709,216 1657,264 1601,282 C1567,293 1539,295 1511,287 C1564,301 1628,267 1661,240 C1692,215 1714,190 1743,161 Z',
        chain=[[1735,170],[1688,222],[1639,263],[1575,289],[1517,289]],root_pin=[30,65]),
    ]

    # Occluding intersections remain fixed. Only the visible, free interval
    # belongs to a strand, so lifting it cannot expose a severed neighbouring lock.
    free = {
      'left-back-high': ([[948,66],[888,42],[817,27],[765,35],[746,46]], [10,30]),
      'left-back-middle': ([[900,76],[831,57],[752,58],[688,76],[647,102]], [12,32]),
      'left-back-wide': ([[848,214],[788,218],[719,250],[663,289],[633,316]], [12,28]),
      'left-front-lower': ([[1040,308],[963,308],[874,320],[815,335],[790,346]], [12,30]),
      'right-back-outer': ([[1740,690],[1722,739],[1695,787],[1653,794],[1594,763]], [12,28]),
      'right-front-arm-loop': ([[1678,819],[1680,882],[1480,879],[1260,875],[1104,959]], [12,30]),
      'right-back-bottom-curl': ([[1594,962],[1577,1016],[1536,1055],[1450,1039],[1344,1024]], [12,30]),
      'right-front-shoulder': ([[1597,495],[1549,516],[1493,536],[1442,554],[1415,572]], [12,30]),
      'right-front-upper-filament': ([[1480,860],[1425,846],[1365,861],[1287,858],[1170,841]], [10,28]),
    }
    for d in defs:
        if d['name'] in free:
            d['chain'], d['root_pin'] = free[d['name']]
            d['free_interval'] = True
    # The fine loop rejoins the main hanging hair at its other end.
    defs[6]['tip_pin'] = [12,30]
    return defs


def hair():
    build=module('hair_native',ROOT/'tools/build-cg-hair.py')
    photo=np.array(Image.open(ASSETS/'CGC14_a.png').convert('RGB'))
    defs=regions()
    folder=ASSETS/'CGC14-wind';folder.mkdir(exist_ok=True)
    masks=[]
    # Supersampled authored outlines retain continuous native strand edges.
    for definition in defs:
        p=build.contour(definition['outline'])
        matte=Image.new('L',(3840,2160))
        ImageDraw.Draw(matte).polygon([tuple(v*2) for v in p],fill=255)
        mask=np.array(matte.resize(SIZE,Image.Resampling.LANCZOS))
        if definition['region']!='bangs':
            from pymatting import estimate_alpha_cf
            occupied=cv2.dilate(np.uint8(mask>100),np.ones((13,13),np.uint8))
            ys,xs=np.where(occupied)
            x0=max(0,xs.min()-4);x1=min(1920,xs.max()+5)
            y0=max(0,ys.min()-4);y1=min(1080,ys.max()+5)
            color=photo[y0:y1,x0:x1].astype(float)
            scope=occupied[y0:y1,x0:x1]>0
            # A geometric trimap preserves shaded native ink. Colour thresholds
            # misclassified warm brown shadows as red background and tore holes.
            authored=mask[y0:y1,x0:x1]>127
            fg=cv2.erode(np.uint8(authored),np.ones((9,9),np.uint8))>0
            bg=~(cv2.dilate(np.uint8(authored),np.ones((13,13),np.uint8))>0)
            trimap=np.full(scope.shape,.5);trimap[bg]=0;trimap[fg]=1
            solved=estimate_alpha_cf(color/255,trimap)
            # Static contour cleanup removes isolated matte fragments while
            # retaining one continuous native alpha edge for each strand.
            solid=np.uint8(solved>.5)*255
            solid=cv2.morphologyEx(solid,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
            contours,_=cv2.findContours(solid,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            clean=np.zeros_like(solid)
            for outline in contours:
                if cv2.contourArea(outline)>=18:
                    cv2.fillPoly(clean,[cv2.approxPolyDP(outline,.65,True)],255)
            clean=cv2.GaussianBlur(clean,(3,3),.5)
            mask[:]=0;mask[y0:y1,x0:x1]=clean
            print('Native alpha solved:',definition['name'],flush=True)
        if definition.get('free_interval'):
            yy,xx=np.mgrid[:1080,:1920]
            anchor=np.array(definition['chain'][0]);direction=np.array(definition['chain'][1])-anchor
            direction=direction/np.linalg.norm(direction)
            along=(xx-anchor[0])*direction[0]+(yy-anchor[1])*direction[1]
            scope=np.clip((along+8)/24,0,1);scope=scope*scope*(3-2*scope)
            mask=np.uint8(np.round(mask*scope))
        mask=np.uint8(np.round(mask*build.pin_coverage(mask.shape,definition)))
        masks.append(mask)
    # Front-to-back ownership: every native pixel belongs to one moving part.
    for i in range(len(masks)-1,-1,-1):
        for j in range(i):masks[j]=np.uint8(masks[j].astype(float)*(1-masks[i]/255))
    union=np.maximum.reduce(masks)
    manifest=[]
    for index,(definition,mask) in enumerate(zip(defs,masks)):
        # Preserve native RGB; do not unmatte against the temporary Telea
        # underlay (its guessed colors would create black/saturated fringes).
        rgba=np.dstack([photo,mask])
        rgba[mask==0,:3]=0
        Image.fromarray(rgba).save(folder/f'hair-{index}.png')
        ys,xs=np.where(mask>0)
        item=dict(definition,texture=f'assets/CGC14-wind/hair-{index}.png',
          bounds=[int(xs.min())-3,int(ys.min())-3,int(xs.max())+4,int(ys.max())+4],
          sway=0,stiffness=4,damping=.85,mass=.7)
        manifest.append(item)
    Image.fromarray(union).save(folder/'selection.png')
    report=photo.copy();report[union>0]=np.uint8(photo[union>0]*.45+np.array([0,220,210])*.55)
    Image.fromarray(report).save(folder/'selection-review.jpg')
    paths=json.loads((PROJECT/'hair-rigs.json').read_text())
    paths['CGC14']=manifest
    (PROJECT/'hair-rigs.json').write_text(json.dumps(paths,indent=2)+'\n')
    (PROJECT/'cgc14-hair-regions.json').write_text(json.dumps(defs,indent=2)+'\n')
    print('CGC14 native wind cutouts:',len(manifest))

def polygon(points):
    canvas=Image.new('L',(3840,2160))
    ImageDraw.Draw(canvas).polygon([tuple(np.array(p)*2) for p in points],fill=255)
    return np.array(canvas.resize(SIZE,Image.Resampling.LANCZOS))

def stroke_matte(photo,envelope,mean_limit=110):
    """CGC06's closed-form native matte, with CGC14 warm-brown ink seeds."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    ys,xs=np.where(envelope>0)
    x0=max(0,xs.min()-4);x1=min(1920,xs.max()+5)
    y0=max(0,ys.min()-4);y1=min(1080,ys.max()+5)
    raw=photo[y0:y1,x0:x1].astype(float);color=raw/255
    window=envelope[y0:y1,x0:x1]>0
    fg=window&(raw.mean(2)<mean_limit)&(raw[:,:,1]<raw[:,:,0]-6)
    if not np.any(fg):raise ValueError('Native stroke has no foreground seed')
    bg=(~cv2.dilate(np.uint8(window),np.ones((3,3),np.uint8)).astype(bool))|((raw[:,:,1]>raw[:,:,0]+23)&window)
    h,w=window.shape;n=h*w;indices=np.arange(n).reshape(h,w)
    patches=np.lib.stride_tricks.sliding_window_view(indices,(3,3)).reshape(-1,9)
    colors=color.reshape(-1,3)[patches];centered=colors-colors.mean(1,keepdims=True)
    covariance=np.einsum('nki,nkj->nij',centered,centered)/9+np.eye(3)[None]*1e-6/9
    local=np.eye(9)[None]-(1+np.einsum('nki,nij,nlj->nkl',centered,np.linalg.inv(covariance),centered))/9
    rows=np.repeat(patches,9,1).ravel();cols=np.tile(patches,(1,9)).ravel()
    lap=sparse.coo_matrix((local.ravel(),(rows,cols)),shape=(n,n)).tocsr()
    known=(fg|bg).ravel().astype(float)
    alpha=np.clip(spsolve(lap+sparse.diags(100*known),100*fg.ravel()),0,1).reshape(h,w)
    alpha[~cv2.dilate(np.uint8(window),np.ones((3,3),np.uint8)).astype(bool)]=0
    _,labels=cv2.distanceTransformWithLabels(np.uint8(~fg),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    palette=np.zeros((labels.max()+1,3),np.uint8);palette[labels[fg]]=photo[y0:y1,x0:x1][fg]
    ink=palette[labels];ink[fg]=photo[y0:y1,x0:x1][fg]
    result=np.zeros((1080,1920,4),np.uint8)
    result[y0:y1,x0:x1,:3]=ink;result[y0:y1,x0:x1,3]=np.uint8(np.round(alpha*255))
    return result

def eyes():
    """One whole upper/lower mesh per eye; native c is a shape constraint."""
    from scipy.interpolate import PchipInterpolator
    definitions=json.loads((ROOT/'godot/cg-puppet/eyes.json').read_text())['CGC14']['eyes']
    photo=np.array(Image.open(ASSETS/'CGC14_a.png').convert('RGB'))
    folder=ASSETS/'CGC14-eyes';folder.mkdir(exist_ok=True)
    upper_outlines=[
      [[-49,7],[-46,-9],[-40,-23],[-25,-32],[-7,-35],[15,-34],[30,-30],[39,-20],[43,-1],[42,24],[35,27],[33,18],[35,2],[29,-13],[19,-22],[1,-24],[-16,-22],[-29,-15],[-38,-3],[-43,11]],
      [[-59,-2],[-54,-16],[-43,-26],[-22,-30],[-1,-31],[19,-24],[33,-12],[40,0],[36,10],[32,1],[22,-10],[6,-18],[-15,-21],[-35,-19],[-46,-11],[-53,2]]]
    lower_outlines=[
      [[-44,-5],[-38,9],[-25,21],[-11,24],[9,23],[28,20],[38,16],[41,22],[29,27],[8,30],[-13,31],[-28,26],[-40,13],[-47,-3]],
      [[-56,-6],[-51,15],[-46,26],[-32,31],[-13,35],[7,31],[23,20],[36,0],[40,3],[28,23],[9,36],[-14,40],[-36,36],[-49,31],[-55,19],[-59,-4]]]
    closed=[ [[-24,9],[-9,15],[8,16],[25,13],[39,7]],
      [[-48,17],[-30,23],[-10,28],[10,30],[25,26]] ]
    native_guides=[
      dict(upper=[[-44,-5],[-36,-20],[-20,-28],[0,-30],[23,-27],[34,-16],[39,19]],lower=[[-44,-5],[-35,13],[-22,25],[0,27],[24,23],[39,19]]),
      dict(upper=[[-54,-7],[-43,-20],[-24,-26],[-5,-27],[14,-22],[29,-12],[35,-4]],lower=[[-54,-7],[-48,22],[-32,30],[-13,34],[8,29],[25,13],[35,-4]])]
    all_parts=[];rig=[];edit=np.zeros((1080,1920),np.uint8)
    opening=np.zeros((1080,1920,3),np.uint8)
    parts_sheet=Image.new('RGBA',SIZE,(25,30,36,255))
    fixed_hair=np.zeros((1080,1920,4),np.uint8)
    pins=['[gd_scene load_steps=2 format=3]','',
      '[ext_resource type="Texture2D" path="res://assets/CGC14_a.png" id="1"]','',
      '[node name="CGC14ClosedPose" type="Node2D"]','',
      '[node name="Reference" type="Sprite2D" parent="."]','texture = ExtResource("1")','centered = false','modulate = Color(1, 1, 1, 0.6)','']
    for i,definition in enumerate(definitions):
        angle=np.deg2rad(definition['angle']);axis=np.array([np.cos(angle),np.sin(angle)]);normal=np.array([-axis[1],axis[0]])
        origin=np.array(definition['center'])
        def world(points):
            p=np.asarray(points,float);return origin+p[:,0,None]*axis+p[:,1,None]*normal
        guides=native_guides[i]
        xmin,xmax=guides['upper'][0][0],guides['upper'][-1][0]
        for kind,outline in [('upper',upper_outlines[i]),('lower',lower_outlines[i])]:
            envelope=polygon(world(outline))
            cut=stroke_matte(photo,envelope)
            # Authoritative tight envelopes prevent the iris/hair becoming ink.
            cut[:,:,3]=np.minimum(cut[:,:,3],envelope)
            if kind=='upper':
                # Fixed foreground hair above the upper stroke belongs on the
                # static native hair layer, never on the moving lashes.
                yy,xx=np.mgrid[:1080,:1920]
                local_x=(xx-origin[0])*axis[0]+(yy-origin[1])*axis[1]
                local_y=(xx-origin[0])*normal[0]+(yy-origin[1])*normal[1]
                g=np.asarray(guides[kind],float)
                ridge=PchipInterpolator(g[:,0],g[:,1],extrapolate=True)(np.clip(local_x,g[0,0],g[-1,0]))
                transfers=(local_y<ridge-4.0)&(local_x>-30)&(local_x<20)
                fixed_hair[transfers]=cut[transfers]
                cut[transfers,3]=0
            name=f'{kind}-{i}.png';Image.fromarray(cut).save(folder/name)
            parts_sheet.alpha_composite(Image.fromarray(cut))
            g=np.asarray(guides[kind],float)
            xs=np.linspace(xmin-5,xmax+5,64)
            source=np.column_stack([xs,PchipInterpolator(g[:,0],g[:,1],extrapolate=True)(np.clip(xs,g[0,0],g[-1,0]))])
            ys=np.linspace(float(np.min(outline,axis=0)[1])-3,float(np.max(outline,axis=0)[1])+3,33)
            all_parts.append(dict(eye=i,part=kind,texture=f'assets/CGC14-eyes/{name}',basis=[*origin.tolist(),*axis.tolist()],
                source=source.tolist(),grid_y=ys.tolist(),closed=closed[i],opening=[xmin,xmax]))
            group=f'{kind.capitalize()}Lid{i+1}'
            pins+= [f'[node name="{group}" type="Node2D" parent="."]','']
            for j,p in enumerate(world(closed[i])):
                pins += [f'[node name="Pin{j+1}" type="Marker2D" parent="{group}"]',f'position = Vector2({p[0]:.4f}, {p[1]:.4f})','gizmo_extents = 4.0','']
        native=polygon(world(guides['upper']+list(reversed(guides['lower']))))
        opening[:,:,i]=native
        region=cv2.dilate(polygon(world(upper_outlines[i]+list(reversed(lower_outlines[i])))),np.ones((9,9),np.uint8))
        # Complete eye footprints, including the closed target and creases.
        cv2.fillPoly(region,[np.int32(world([[xmin-8,-43],[xmax+8,-43],[xmax+8,43],[xmin-8,43]]))],255)
        edit=np.maximum(edit,region)
        brow=[ [[-66,-61],[-40,-65],[-15,-66],[10,-64],[40,-61]],
          [[-74,-50],[-45,-55],[-17,-59],[10,-60],[37,-54]] ][i]
        brow_envelope=np.zeros((1080,1920),np.uint8)
        cv2.polylines(brow_envelope,[np.int32(world(brow))],False,255,5,cv2.LINE_AA)
        Image.fromarray(stroke_matte(photo,brow_envelope,170)).save(folder/f'eyebrow-{i}.png')
        edit=np.maximum(edit,cv2.dilate(brow_envelope,np.ones((7,7),np.uint8)))
        rig.append(dict(basis=[*origin.tolist(),*axis.tolist()],opening=[xmin,xmax]))
        # Separate native crease ink; short line above each upper lash.
        crease=[[[18,-42],[31,-36],[34,-32],[26,-33],[17,-39]],
          [[-44,-36],[-28,-36],[-21,-33],[-29,-32],[-45,-32]]][i]
        try:
            rgba=stroke_matte(photo,polygon(world(crease)))
            rgba[:,:,3]=np.minimum(rgba[:,:,3],polygon(world(crease)))
            Image.fromarray(rgba).save(folder/f'crease-{i}.png')
        except ValueError:
            Image.new('RGBA',SIZE).save(folder/f'crease-{i}.png')
    Image.fromarray(opening).save(folder/'native-opening.png')
    Image.fromarray(fixed_hair).save(folder/'fixed-hair.png')
    # Native b mouth is a small independent mesh. Flattening its cross-section
    # produces the closed a/c lip, then opening restores its original texture.
    b=np.array(Image.open(ASSETS/'CGC14_b.png').convert('RGB'))
    yy,xx=np.mgrid[:1080,:1920]
    delta=np.stack([xx-1528.0,yy-366.5],axis=-1)
    axis=np.array([np.cos(np.deg2rad(54)),np.sin(np.deg2rad(54))])
    normal=np.array([-axis[1],axis[0]])
    x=delta@axis;y=delta@normal
    scope=(abs(x)<11)&(abs(y)<6)
    alpha=np.clip((b[:,:,0].astype(float)-b[:,:,1]-29)/25,0,1)*scope
    Image.fromarray(np.dstack([b,np.uint8(alpha*255)])).save(folder/'mouth-b.png')
    Image.fromarray(edit).save(folder/'edit-region.png')
    parts_sheet.convert('RGB').crop((1430,140,1760,470)).resize((990,990)).save(folder/'native-parts-review.jpg')
    (PROJECT/'cgc14-eyes.json').write_text(json.dumps(dict(parts=all_parts,eyes=rig),indent=2)+'\n')
    pin_path=PROJECT/'cgc14-pin-pose.tscn'
    if not pin_path.exists():pin_path.write_text('\n'.join(pins),encoding='utf-8')
    print('CGC14 native upper/lower meshes and editable closed-pose pins prepared')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--eyes',action='store_true')
    args=p.parse_args()
    eyes() if args.eyes else hair()
