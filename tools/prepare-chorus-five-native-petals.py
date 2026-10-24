"""Separate CGC16's painted, defocused foreground petals for 3D animation.

Contours and restoration donors are traced in the original 1920 x 1080 art.
The original 17 soft petals retain their native restoration. Additional crisp
petals use authored image-generation repairs sampled only inside traced holes.
RGBA keeps the native centre texture and extends its own colour into the soft
edge, so the defocused rim does not carry a background tile.
The source is retained unchanged; edge-cut petals remain marked as such.
"""
from pathlib import Path
import argparse
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "godot/chorus-five/assets"
SIZE = (1920, 1080)

# A contour follows the visible petal body. A Gaussian then retains the native
# defocus falloff. Donors are source offsets, never external image fragments.
PETALS = [
    dict(id="upper-left-edge", blur=5.0, depth=2.5, donor=(125,165),
         points=[(-18,70),(8,80),(35,91),(64,98),(95,101),(112,109),(106,125),(89,141),(66,150),(37,150),(13,140),(-16,119)], edge="left"),
    dict(id="upper-left-small", blur=4.0, depth=2.1, donor=(145,210),
         points=[(193,70),(206,54),(229,54),(248,63),(256,78),(252,94),(232,104),(212,98),(198,86)]),
    dict(id="left-upper-large", blur=5.2, depth=2.4, donor=(60,235),
         points=[(247,151),(253,132),(269,118),(294,105),(326,101),(356,106),(380,112),(400,127),(406,142),(395,158),(367,175),(340,195),(311,207),(282,203),(262,190),(251,174)]),
    dict(id="middle-left-distant", blur=4.2, depth=1.7, donor=(-100,65),
         points=[(477,280),(495,278),(512,261),(523,246),(533,244),(535,257),(530,273),(517,287),(499,290),(481,288)]),
    dict(id="upper-right-large", blur=5.0, depth=2.6,
         points=[(1173,161),(1186,137),(1191,102),(1202,75),(1218,58),(1240,54),(1259,61),(1272,81),(1279,111),(1271,140),(1251,163),(1226,179),(1208,182),(1193,170),(1179,170)]),
    dict(id="right-edge-large", blur=4.3, depth=2.8,
         points=[(1802,228),(1798,205),(1801,174),(1814,149),(1839,130),(1865,111),(1884,110),(1899,125),(1914,128),(1937,126),(1943,155),(1933,188),(1910,206),(1877,215),(1842,224),(1821,246),(1809,246)], edge="right"),
    dict(id="left-middle-small", blur=3.4, depth=1.8, donor=(-165,30),
         points=[(548,484),(559,473),(577,469),(598,476),(613,488),(617,500),(607,505),(591,496),(569,494),(556,494)]),
    dict(id="left-hand-under", blur=5.1, depth=2.5, donor=(65,150),
         points=[(251,678),(260,655),(278,648),(295,632),(311,617),(331,619),(344,636),(351,662),(359,674),(351,691),(333,708),(310,722),(287,723),(276,711),(259,707)]),
    dict(id="right-middle-large", blur=4.4, depth=2.7,
         points=[(1774,464),(1774,440),(1781,420),(1796,407),(1818,402),(1837,406),(1852,404),(1862,412),(1864,431),(1856,446),(1833,454),(1808,464),(1792,485),(1780,478)]),
    dict(id="left-bottom-edge", blur=5.0, depth=2.8, donor=(155,-60),
         points=[(-17,793),(6,790),(27,798),(39,813),(43,833),(34,852),(14,870),(-8,879)], edge="left"),
    dict(id="under-hand-small", blur=3.6, depth=1.8,
         points=[(598,817),(610,822),(622,829),(636,831),(647,832),(651,842),(638,849),(624,849),(610,840),(600,831)]),
    dict(id="left-lower-large", blur=5.0, depth=2.8, donor=(-35,-145),
         points=[(84,988),(92,971),(107,957),(127,952),(150,955),(174,960),(184,975),(185,987),(194,999),(184,1013),(162,1017),(142,1009),(123,1007),(105,1009),(89,1006)]),
    dict(id="lower-middle-large", blur=3.7, depth=2.4, donor=(95,25),
         points=[(668,936),(682,926),(703,919),(720,923),(733,935),(741,949),(733,961),(733,971),(721,979),(708,974),(696,964),(688,947),(676,946)]),
    dict(id="right-skirt-large", blur=4.2, depth=2.6,
         points=[(1368,830),(1381,811),(1394,792),(1401,770),(1408,746),(1417,752),(1428,775),(1434,794),(1427,814),(1413,829),(1393,842),(1378,845)]),
    dict(id="bottom-middle-edge", blur=4.8, depth=2.9, donor=(120,-30),
         points=[(641,1080),(651,1068),(671,1061),(694,1062),(719,1069),(733,1088)], edge="bottom"),
    dict(id="bottom-right-edge", blur=5.2, depth=2.9,
         points=[(1667,1055),(1687,1053),(1701,1045),(1718,1041),(1740,1045),(1760,1057),(1774,1074),(1778,1098),(1744,1107),(1706,1084),(1685,1074)], edge="bottom"),
    dict(id="bottom-right-thin-edge", blur=3.5, depth=2.7,
         points=[(1598,1089),(1605,1067),(1617,1049),(1637,1034),(1645,1028),(1641,1038),(1626,1054),(1616,1072),(1614,1094)], edge="bottom"),
]


def feather(points, blur):
    im = Image.new("L", SIZE)
    ImageDraw.Draw(im).polygon([tuple(p) for p in points], fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255


def translated(src, offset):
    dx, dy = offset
    return cv2.warpAffine(src, np.float32([[1,0,-dx],[0,1,-dy]]), SIZE,
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)


def guided_jacket(src, hole, petal_id):
    """Interpolate smooth cloth and preserve the known painted silhouette."""
    mask = (hole > 0.006).astype(np.uint8) * 255
    restored = cv2.inpaint(src, mask, 6, cv2.INPAINT_NS)
    yy, xx = np.mgrid[:SIZE[1], :SIZE[0]]
    if petal_id == "upper-right-large":
        # The character outline is hidden by the flower, but the two visible
        # ends establish its curve. Adjacent cherry texture restores its left.
        boundary = np.interp(yy[:,0], [15,35,55,80,108,135,159,175,195],
                             [1290,1281,1266,1247,1223,1195,1163,1144,1125])[:,None]
        donor = translated(src, (-750,180))
        # Smooth native shoulder shading, with the lapel and gold edging
        # continued between their unobscured endpoints. No hair is cloned.
        f=np.clip((xx-1190)/100,0,1)[...,None]
        shoulder=np.broadcast_to(np.array([161,55,101])*(1-f)+np.array([103,68,91])*f,src.shape).copy()
        light=np.clip((195-yy)/190,0,1)[...,None]*np.array([50,31,27])
        shoulder=np.clip(shoulder+light,0,255)
        lapel_edge=np.interp(yy[:,0],[40,70,100,130,160,200,230],
                             [1280,1268,1261,1256,1255,1258,1264])[:,None]
        lapel=np.array([106,75,95])+np.clip((190-yy)/160,0,1)[...,None]*np.array([35,29,27])
        lapel=np.broadcast_to(lapel,src.shape)
        mix=np.clip((xx-lapel_edge)/2,0,1)[...,None]
        body=shoulder*(1-mix)+lapel*mix
        edge_shade=np.exp(-((xx-lapel_edge-1)/2.0)**2)[...,None]*np.array([22,16,20])
        body=np.clip(body-edge_shade,0,255)
        outer_mix=np.clip((xx-boundary+1)/2,0,1)[...,None]
        restored=np.rint(donor*(1-outer_mix)+body*outer_mix).astype(np.uint8)
        drawing=Image.fromarray(restored).resize((3840,2160),Image.Resampling.BICUBIC)
        d=ImageDraw.Draw(drawing)
        d.polygon([(1264*2,86*2),(1267*2,105*2),(1274*2,137*2),
                   (1279*2,176*2),(1284*2,216*2),(1276*2,216*2),
                   (1271*2,177*2),(1266*2,139*2),(1263*2,105*2)],fill=(241,213,158))
        restored=np.asarray(drawing.resize(SIZE,Image.Resampling.LANCZOS))
    elif petal_id == "right-edge-large":
        # The sleeve/sky boundary continues diagonally through the petal.
        boundary = (1768 + yy*0.285)
        t=np.clip((yy-70)/260,0,1)[...,None]
        sky=(np.array([194,234,243])*(1-t)+np.array([140,205,235])*t)
        sky=np.broadcast_to(sky,src.shape).astype(np.uint8)
        t=np.clip((yy-90)/220,0,1)[...,None]
        sleeve=np.array([235,144,171])*(1-t)+np.array([180,58,114])*t
        sleeve=np.broadcast_to(sleeve,src.shape).astype(np.uint8)
        restored[xx > boundary] = sky[xx > boundary]
        restored[xx <= boundary] = sleeve[xx <= boundary]
    elif petal_id == "right-middle-large":
        # Sky gap between the jacket front and its sleeve, with native colour.
        drawing=Image.fromarray(restored)
        d=ImageDraw.Draw(drawing)
        d.polygon([(1768,309),(1785,329),(1808,358),(1836,389),(1835,411),
            (1839,439),(1846,477),(1853,501),(1821,478),(1807,457),
            (1795,432),(1787,403),(1780,373),(1774,342)],fill=(127,205,237))
        restored=np.asarray(drawing)
    elif petal_id == "right-skirt-large":
        # The petal hides the girl's skirt in front of the man's jacket.
        # Interpolation must not smear the gold trim at x1435 into this hole.
        skirt_edge=np.interp(yy[:,0],[790,800,810,820,830,850],
                              [1345,1374,1398,1435,1500,1550])[:,None]
        girl=xx < skirt_edge
        coat=np.broadcast_to(np.array([146,34,71])+np.clip((810-yy)/130,0,1)[...,None]*np.array([12,4,6]),src.shape).copy()
        crease=yy-(834+.56*(xx-1355))
        skirt=np.broadcast_to(np.array([182,40,82]),src.shape).astype(float).copy()
        skirt-=np.exp(-(crease/2.0)**2)[...,None]*np.array([34,14,21])
        skirt-=np.clip(crease/60,0,1)[...,None]*np.array([17,6,9])
        skirt+=np.exp(-((crease+15)/13)**2)[...,None]*np.array([15,4,8])
        restored=np.where(girl[...,None],skirt,coat).clip(0,255).astype(np.uint8)
        drawing=Image.fromarray(restored).resize((3840,2160),Image.Resampling.BICUBIC)
        d=ImageDraw.Draw(drawing)
        d.line([(1434*2,749*2),(1503*2,791*2)],fill=(61,46,65),width=42)
        d.line([(1434*2,754*2),(1503*2,796*2)],fill=(220,170,111),width=24)
        d.line([(1440*2,785*2),(1503*2,824*2)],fill=(60,47,67),width=38)
        d.line([(1440*2,790*2),(1503*2,829*2)],fill=(211,157,104),width=20)
        restored=np.asarray(drawing.resize(SIZE,Image.Resampling.LANCZOS))
    elif petal_id == "under-hand-small":
        # This petal crosses two slender hair locks. Ordinary inpainting blends
        # their gold/pink bands across the background and leaves a ghost. Trace
        # each original border through the hidden interval, then reproject the
        # unobscured native colour cross-section from y800 along those borders.
        rows=[790,800,810,820,830,840,850,860,870,880,890]
        thin_l=np.interp(yy[:,0],rows,[626,621,616,611,606,602,598,595,593,592,592])[:,None]
        thin_r=np.interp(yy[:,0],rows,[636,631,625,620,615,610,605,601,598,595,594])[:,None]
        wide_l=np.interp(yy[:,0],rows,[641,637,634,631,628,626,625,624,623,623,623])[:,None]
        wide_r=np.interp(yy[:,0],rows,[693,684,676,669,663,658,653,649,646,643,641])[:,None]
        t=np.clip((yy-800)/70,0,1)[...,None]
        bg=np.array([199,179,216])*(1-t)+np.array([181,164,213])*t
        bg=np.broadcast_to(bg,src.shape).copy()
        bg+=np.clip((615-xx)/50,-1,1)[...,None]*np.array([7,8,3])
        restored=bg.astype(np.float32)
        for left,right,donor_left,donor_right in [
                (thin_l,thin_r,621.0,631.0),
                (wide_l,wide_r,637.0,684.0)]:
            u=np.clip((xx-left)/np.maximum(right-left,1),0,1)
            mx=(donor_left+u*(donor_right-donor_left)).astype(np.float32)
            my=np.full(mx.shape,800,np.float32)
            hair=cv2.remap(src,mx,my,cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT_101).astype(np.float32)
            coverage=np.clip(np.minimum(xx-left,right-xx)+.7,0,1)[...,None]
            restored=restored*(1-coverage)+hair*coverage
        restored=restored.clip(0,255).astype(np.uint8)
    return restored


def to_linear(x):
    x=x/255.0
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)


def to_srgb(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,x*12.92,1.055*x**(1/2.4)-.055)*255


def sharp_clothing_repairs(clean, all_petals, supports):
    """Repair removed petals with sharp local patches and complete crease bands."""
    for name,rect in [("bodice",(940,620,320,420)),("coat",(1260,240,360,520))]:
        x,y,w,h=rect
        patch=np.asarray(Image.open(ASSETS/"sharp-repairs"/(name+"-registered.png")).convert("RGB"),np.float32)
        holes=np.zeros((h,w),np.float32)
        for part,support in zip(all_petals,supports):
            if name=="coat" and part["id"] not in ["original-ponytail-junction","original-rear-arc-front","original-coat-mid-curve"]:continue
            holes=np.maximum(holes,support[y:y+h,x:x+w])
        mask=(holes>.05).astype(np.uint8)
        count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
        crop=clean[y:y+h,x:x+w].astype(np.float32)
        if name=="bodice":
            # Reconstruct complete crease bands, rather than clipping a new
            # crease to the little petal-shaped holes that originally hid it.
            r,g,b=[crop[...,i] for i in range(3)]
            yy,_=np.mgrid[:h,:w]
            cloth=((r-g>40)&(b-g>8)&(r>80)&(yy>120)&(yy<385)).astype(np.float32)
            cloth*=np.clip((yy-120)/6,0,1)*np.clip((385-yy)/6,0,1)
            region=cloth>.9
            offset=np.median((crop-patch)[region],axis=0)
            crop=crop*(1-cloth[...,None])+np.clip(patch+offset,0,255)*cloth[...,None]
            clean[y:y+h,x:x+w]=np.rint(crop).clip(0,255).astype(np.uint8)
            continue
        for label in range(1,count):
            body=(labels==label).astype(np.uint8)
            ring=(cv2.dilate(body,np.ones((11,11),np.uint8))>0)&(mask==0)
            offset=np.median((crop-patch)[ring],axis=0) if ring.any() else np.zeros(3)
            corrected=np.clip(patch+offset,0,255)
            weight=cv2.GaussianBlur(body.astype(np.float32),(0,0),.6)
            crop=crop*(1-weight[...,None])+corrected*weight[...,None]
        clean[y:y+h,x:x+w]=np.rint(crop).clip(0,255).astype(np.uint8)
    return clean


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ASSETS / "source.png")
    args = parser.parse_args()
    original = np.asarray(Image.open(args.source).convert("RGB"))
    if original.shape[:2] != (1080,1920):
        raise ValueError("CGC16 must be the unmodified 1920 x 1080 source")
    out = ASSETS / "native-petals"
    out.mkdir(parents=True, exist_ok=True)
    clean = original.copy()
    alphas = []
    supports=[]
    extra=json.loads((ROOT/"godot/chorus-five/native-petals-extra.json").read_text(encoding="utf8"))["petals"]
    all_petals=PETALS+extra
    redraw_path=out/"redraw-no-petals.png"
    redraw=np.asarray(Image.open(redraw_path).convert("RGB").resize(SIZE,Image.Resampling.LANCZOS))
    extra_union=np.zeros((1080,1920),np.float32)
    removal_union=np.zeros_like(extra_union)
    for petal in all_petals:
        alpha = feather(petal["points"], petal["blur"])
        # The full defocus tail is removed as well as the bright petal core.
        repair_mask=cv2.dilate((alpha>.012).astype(np.uint8),
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
        support=cv2.GaussianBlur(repair_mask.astype(np.float32),(0,0),2.5)
        if petal in extra:
            support=cv2.GaussianBlur(cv2.dilate((alpha>.008).astype(np.uint8),np.ones((7,7),np.uint8)).astype(np.float32),(0,0),.9)
            # Match the surrounding native colour as well as the redrawn
            # gradients; a literal paste leaves a dark petal-shaped patch.
            mask=(support>.02).astype(np.uint8)*255
            x,y,w,h=cv2.boundingRect(mask)
            repair_source=translated(original,petal["donor"]) if "donor" in petal else redraw
            restored=cv2.seamlessClone(repair_source[y:y+h,x:x+w],clean,
                mask[y:y+h,x:x+w],(x+w//2,y+h//2),cv2.NORMAL_CLONE)
            extra_union=np.maximum(extra_union,support)
        elif "donor" in petal:
            donor = translated(original, petal["donor"])
            mask = (support > .02).astype(np.uint8)*255
            # Poisson joining retains the native boundary's colour and texture.
            x,y,w,h = cv2.boundingRect(mask)
            restored = cv2.seamlessClone(donor[y:y+h,x:x+w], clean,
                mask[y:y+h,x:x+w], (x+w//2,y+h//2), cv2.NORMAL_CLONE)
        else:
            restored = guided_jacket(original, support, petal["id"])
        weight = support[...,None]
        clean = np.rint(clean*(1-weight) + restored*weight).clip(0,255).astype(np.uint8)
        alphas.append(alpha)
        supports.append(support)
        removal_union=np.maximum(removal_union,support)

    clean=sharp_clothing_repairs(clean,all_petals,supports)
    # Replace the whole damaged skirt/coat contact, including its continuous
    # outline. A petal-shaped patch would cut the new seam into little pieces.
    x,y,w,h=1330,740,290,270
    patch=np.asarray(Image.open(ASSETS/"cut-repairs/skirt-registered.png").convert("RGB"),np.float32)
    yy,xx=np.mgrid[:h,:w]
    weight=np.clip(np.minimum.reduce([xx,yy,w-1-xx,h-1-yy])/5,0,1)[...,None]
    clean[y:y+h,x:x+w]=np.rint(clean[y:y+h,x:x+w]*(1-weight)+patch*weight).clip(0,255).astype(np.uint8)
    Image.fromarray(clean).save(ASSETS / "source-clean.png")
    Image.fromarray(np.rint(extra_union*255).astype(np.uint8)).save(out/"extra-removal-mask.png")
    Image.fromarray(np.rint(removal_union*255).astype(np.uint8)).save(out/"removal-mask.png")
    manifest = {"source_size":list(SIZE), "clean_path":"res://assets/source-clean.png",
                "petals":[]}
    reconstructed = clean.astype(np.float32)
    tiles = []
    for petal, shape in zip(all_petals, alphas):
        ys,xs = np.nonzero(shape>.001)
        x0,x1,y0,y1 = max(int(xs.min())-2,0),min(int(xs.max())+3,1920),max(int(ys.min())-2,0),min(int(ys.max())+3,1080)
        shape=shape[y0:y1,x0:x1]
        s=to_linear(original[y0:y1,x0:x1].astype(np.float32))
        # Extrapolate the petal's own centre colour into its defocused edge.
        # This removes flower/cloth texture contamination from the moving rim.
        native=original[y0:y1,x0:x1]
        pink=(native[...,0]>205)&(native[...,1]>125)&(native[...,2]>150)
        core=(shape>(.45 if petal in extra else .88))&pink
        if not core.any():
            core=shape>=shape.max()*.9
        _, inds=distance_transform_edt(~core,return_indices=True)
        natural=s[inds[0],inds[1]]
        natural=cv2.GaussianBlur(natural,(0,0),.65 if petal in extra else 3)
        keep=(np.clip((shape-.8)*5,0,1)*pink)[...,None]
        f=s*keep+natural*(1-keep)
        # A single smooth silhouette avoids admitting the background's flower
        # texture into the alpha matte. Native core colour remains untouched.
        alpha=shape*.985
        alpha[shape<.001]=0
        rgba=np.dstack([to_srgb(f),alpha*255]).clip(0,255).round().astype(np.uint8)
        crop = Image.fromarray(rgba)
        crop.save(out / (petal["id"]+".png"))
        manifest["petals"].append({"id":petal["id"],
            "texture":"res://assets/native-petals/"+petal["id"]+".png",
            "rect":[x0,y0,x1-x0,y1-y0], "center":[(x0+x1)/2,(y0+y1)/2],
            "depth":petal["depth"], "alpha_range":[0,int(rgba[...,3].max())/255],
            "edge_clipped":bool(petal.get("edge")), "clip_edge":petal.get("edge",""),
            "completed":False})
        a=rgba[...,3:4].astype(np.float32)/255
        rec=to_linear(reconstructed[y0:y1,x0:x1])
        reconstructed[y0:y1,x0:x1] = to_srgb(to_linear(rgba[...,:3].astype(np.float32))*a+rec*(1-a))
        tile = Image.new("RGB",(420,235),(58,64,73))
        # Checkerboard makes background contamination readily visible.
        for iy in range(0,235,12):
            for ix in range(0,420,12):
                if (ix//12+iy//12)%2:
                    ImageDraw.Draw(tile).rectangle((ix,iy,ix+11,iy+11),fill=(90,95,104))
        thumb=crop.copy(); thumb.thumbnail((400,195))
        tile.paste(thumb,((420-thumb.width)//2,22+(195-thumb.height)//2),thumb)
        ImageDraw.Draw(tile).text((8,5),petal["id"],fill="white")
        tiles.append(tile)
    (out / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
    Image.fromarray(reconstructed.round().clip(0,255).astype(np.uint8)).save(out / "reconstructed.png")
    grid=Image.new("RGB",(420*4,235*((len(tiles)+3)//4)),(32,35,43))
    for i,tile in enumerate(tiles): grid.paste(tile,((i%4)*420,(i//4)*235))
    grid.save(out / "alpha-review.jpg",quality=95)
    review=Image.new("RGB",(1920,1080*2))
    review.paste(Image.fromarray(original),(0,0));review.paste(Image.fromarray(clean),(0,1080))
    review.save(out / "plate-review.jpg",quality=95)
    error=np.abs(reconstructed-original).mean()
    print(f"Prepared {len(all_petals)} native petals; t=0 reconstruction mean absolute RGB error {error:.3f}/255")


if __name__ == "__main__":
    main()
