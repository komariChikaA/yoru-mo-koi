"""Build continuous eyelid strips and skin underlays, never runtime CG crossfades."""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "godot" / "cg-puppet"
ASSETS = PROJECT / "assets"
SOURCE = Path("${GAME_ROOT}/解包/CG")
OUT = ROOT / "_preview" / "cg-puppet" / "eyes"


def curve(points, x):
    points = sorted(points)
    return np.interp(x, np.array(points)[:,0], np.array(points)[:,1])


def smooth_curve(points, x):
    """Cubic contour through hand-placed closed-lid points."""
    p = np.array(sorted(points),dtype=np.float64)
    slopes = np.gradient(p[:,1],p[:,0])
    index = np.clip(np.searchsorted(p[:,0],x)-1,0,len(p)-2)
    span = p[index+1,0]-p[index,0]
    t = np.clip((x-p[index,0])/span,0,1)
    return ((2*t**3-3*t**2+1)*p[index,1]+(t**3-2*t**2+t)*span*slopes[index]
            +(-2*t**3+3*t**2)*p[index+1,1]+(t**3-t**2)*span*slopes[index+1])


def polygon_mask(points):
    # Supersample the hand-traced outline; do not blur across foreground hair.
    scale = 4
    mask = np.zeros((1080*scale,1920*scale),np.uint8)
    cv2.fillPoly(mask,[np.round(np.array(points)*scale).astype(np.int32)],255)
    return cv2.resize(mask,(1920,1080),interpolation=cv2.INTER_AREA)


def sampled_skin(rgb, points, mask):
    """Smooth 2D skin color field from clean surrounding face patches."""
    ys,xs = np.where(mask > 0)
    color_sum = np.zeros((len(xs),3),np.float32)
    weight_sum = np.zeros(len(xs),np.float32)
    for x,y in points:
        color = np.median(rgb[y-2:y+3,x-2:x+3].reshape(-1,3),axis=0)
        weight = 1.0/((xs-x)**2+(ys-y)**2+400.0)
        color_sum += weight[:,None]*color
        weight_sum += weight
    field = rgb.copy()
    field[ys,xs] = np.uint8(np.clip(np.round(color_sum/weight_sum[:,None]),0,255))
    # Solve a smooth continuation from the actual surrounding pixels. A sampled
    # color field alone leaves a visible pasted oval against the original shade.
    x0,x1 = max(0,xs.min()-3),min(rgb.shape[1],xs.max()+4)
    y0,y1 = max(0,ys.min()-3),min(rgb.shape[0],ys.max()+4)
    patch = field[y0:y1,x0:x1].astype(np.float32)
    unknown = mask[y0:y1,x0:x1] > 0
    kernel = np.float32([[0,.25,0],[.25,0,.25],[0,.25,0]])
    for iteration in range(2500):
        averaged = cv2.filter2D(patch,-1,kernel)
        difference = np.max(np.abs(averaged[unknown]-patch[unknown]))
        patch[unknown] = averaged[unknown]
        if difference < .02:
            break
    field[y0:y1,x0:x1] = np.uint8(np.clip(np.round(patch),0,255))
    return field


def build():
    definitions = json.loads((PROJECT / "eyes.json").read_text(encoding="utf-8"))
    yy, xx = np.mgrid[:1080,:1920].astype(np.float32)
    manifests = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for family, definition in definitions.items():
        rgb = np.array(Image.open(ASSETS / (definition["open_source"]+".png")).convert("RGB"))
        reference = definition["skin_reference"]
        closed = np.array(Image.open(SOURCE / (reference+".png")).convert("RGB")) if reference else None
        upper_alpha = np.zeros((1080,1920), np.uint8)
        lower_alpha = upper_alpha.copy()
        upper_rgb = rgb.copy()
        lower_rgb = rgb.copy()
        original_upper = np.zeros_like(upper_alpha)
        original_lower = np.zeros_like(lower_alpha)
        removal = upper_alpha.copy()
        foreground = upper_alpha.copy()
        reference_lash = upper_alpha.copy()
        generated_skin = rgb.copy()
        # One opaque data row per curve. Alpha must not store a coordinate byte:
        # Godot repairs transparent borders and can change those RGB data bytes.
        curves = np.zeros((6,512,4),np.uint8)
        curves[:,:,3] = 255
        eyes = []
        ink_colors = []
        for index, eye in enumerate(definition["eyes"]):
            angle = math.radians(eye["angle"])
            axis = np.array([math.cos(angle),math.sin(angle)])
            cx, cy = eye["center"]
            local_x = (xx-cx)*axis[0] + (yy-cy)*axis[1]
            local_y = -(xx-cx)*axis[1] + (yy-cy)*axis[0]
            xmin = max(min(p[0] for p in eye["upper"]),min(p[0] for p in eye["lower"]))
            xmax = min(max(p[0] for p in eye["upper"]),max(p[0] for p in eye["lower"]))
            top, bottom = curve(eye["upper"],local_x), curve(eye["lower"],local_x)
            width = eye["lash_width"]
            upper_detail = np.zeros_like(removal)
            for polygon in eye.get("upper_detail", []):
                # Small eyelid creases crossing bangs belong to the moving lid,
                # not the fixed hair. The foreground traces still cut out hair.
                upper_detail = np.maximum(upper_detail,polygon_mask(polygon))
            if eye.get("source_lids"):
                r,g,b = [rgb[:,:,c].astype(np.float32) for c in range(3)]
                # Warm original ink, including its soft antialiased edge. Green
                # iris/white and the hand-traced front hair cannot enter lashes.
                ink_alpha = ((r < 215) & (g < 160) & (r > g+4)).astype(np.float32)
                source_upper = (local_x >= xmin-10) & (local_x <= xmax+5)
                source_upper &= (local_y >= top-width-8) & (local_y <= top+2)
                if eye.get("lash_outline"):
                    points = np.array(eye["lash_outline"])
                    world = np.column_stack([cx+points[:,0]*axis[0]-points[:,1]*axis[1],cy+points[:,0]*axis[1]+points[:,1]*axis[0]])
                    source_upper &= polygon_mask(world) > 0
                source_lower = (local_x >= xmin) & (local_x <= xmax)
                source_lower &= np.abs(local_y-bottom) <= 4
                original_upper = np.maximum(original_upper,np.uint8(np.round(255*ink_alpha*source_upper)))
                # Thin crease fringes need gradual coverage; the main lash's
                # binary ink threshold breaks them into isolated moving dots.
                detail_ink = np.clip((180-g)/40,0,1)*np.clip((235-r)/35,0,1)
                original_upper = np.maximum(original_upper,np.uint8(np.round(upper_detail*detail_ink)))
                original_lower = np.maximum(original_lower,np.uint8(np.round(255*ink_alpha*source_lower)))
            in_width = (local_x >= xmin-12) & (local_x <= xmax+12)
            lash_color = (rgb[:,:,0] < 145) & (rgb[:,:,1] < 105)
            dark_sample = in_width & (local_y >= top-width) & (local_y <= top+3) & lash_color
            ink = np.median(rgb[dark_sample],axis=0) if np.any(dark_sample) else np.array([76,39,45])
            if eye.get("source_lids"):
                warm_ink = source_upper & (ink_alpha > 0) & (g < 100)
                if np.any(warm_ink):
                    ink = np.median(rgb[warm_ink],axis=0)
            ink_colors.append(np.uint8(ink))
            u = np.clip((local_x-xmin)/(xmax-xmin),0,1)
            taper = np.sin(np.pi*u)**.45
            thickness = width*.65*taper
            up = np.uint8(in_width & (local_y >= top-thickness) & (local_y <= top+1.2*taper))*255
            low = np.uint8(in_width & (local_y >= bottom-1.1*taper) & (local_y <= bottom+1.1*taper))*255
            upper_rgb[up > 0] = np.uint8(ink)
            lower_rgb[low > 0] = np.uint8(ink)
            full = np.uint8(in_width & (local_y >= top-width-5) & (local_y <= bottom+7))*255
            if eye.get("edit_polygon"):
                full = polygon_mask(eye["edit_polygon"])
                # Include the original lash silhouette, including antialiasing,
                # rather than leaving its outer ink edge as a stationary rim.
                lash_band = (local_x >= xmin-5) & (local_x <= xmax+5)
                lash_band &= (local_y >= top-width-12) & (local_y <= top+5)
                lash_band &= (rgb[:,:,0] < 160) & (rgb[:,:,1] < 110)
                lash_pixels = cv2.dilate(np.uint8(lash_band)*255,np.ones((3,3),np.uint8))
                full = np.maximum(full,lash_pixels)
                full = np.maximum(full,upper_detail)
                # Cover the source eye's antialiased fringe as well, otherwise
                # its iris/white contaminates the boundary color continuation.
                full = cv2.dilate(full,np.ones((5,5),np.uint8))
            for polygon in eye.get("foreground",[]):
                traced = polygon_mask(polygon)
                # The traced tips touch the eye white at subpixel boundaries;
                # protect the hair colors, not fixed white/iris remnants.
                r,g,b = [rgb[:,:,c].astype(np.int16) for c in range(3)]
                hair_color = ((r > g+8) & (g > b+8)) | ((r > g+15) & (g < 110))
                foreground = np.maximum(foreground,traced*np.uint8(hair_color))
            for polygon in eye.get("foreground_hair_only", []):
                # At a lash/hair crossing the broad dark-ink test also selects
                # maroon eyelashes. Keep only the golden/brown hair pigment.
                traced = polygon_mask(polygon)
                hair_color = (r > g+8) & (g > b+8)
                foreground = np.maximum(foreground,traced*np.uint8(hair_color))
            upper_alpha = np.maximum(upper_alpha,up)
            lower_alpha = np.maximum(lower_alpha,low)
            removal = np.maximum(removal,full)
            if reference:
                # Restrict reference cleanup to its closed lash ribbon, preserving
                # the bangs and tear rings surrounding the eye.
                points = eye["skin_lash"]
                reference_y = curve(points,local_x)
                band = (local_x >= points[0][0]-4) & (local_x <= points[-1][0]+4)
                band &= np.abs(local_y-reference_y) <= width+4
                darkness = band & (closed[:,:,0] < 215) & (closed[:,:,1] < 155)
                reference_lash = np.maximum(reference_lash,np.uint8(darkness)*255)
            if not reference:
                field = sampled_skin(rgb,eye["skin_samples"],full)
                generated_skin[full > 0] = field[full > 0]
            values_x = np.linspace(xmin,xmax,512)
            values_top, values_bottom = curve(eye["upper"],values_x),curve(eye["lower"],values_x)
            values_top = cv2.GaussianBlur(values_top.reshape(1,-1),(11,1),2).ravel()
            values_bottom = cv2.GaussianBlur(values_bottom.reshape(1,-1),(11,1),2).ravel()
            # Both curves meet at the hand-placed corners throughout the blink.
            for endpoint in [0,-1]:
                corner = .5*(eye["upper"][endpoint][1]+eye["lower"][endpoint][1])
                values_top[endpoint] = values_bottom[endpoint] = corner
            # Two channels per curve retain subpixel precision with a PNG sampler.
            encoded = np.uint16(np.clip(np.round((np.stack([values_top,values_bottom],axis=-1)+128)*256),0,65535))
            curves[index*3,:,0] = encoded[:,0] >> 8
            curves[index*3,:,1] = encoded[:,0] & 255
            curves[index*3+1,:,0] = encoded[:,1] >> 8
            curves[index*3+1,:,1] = encoded[:,1] & 255
            values_closed = smooth_curve(eye["closed"],values_x) if eye.get("closed") else values_top*.22+values_bottom*.78
            values_closed = cv2.GaussianBlur(values_closed.reshape(1,-1),(11,1),2).ravel()
            values_closed[0],values_closed[-1] = values_top[0],values_top[-1]
            encoded_closed = np.uint16(np.clip(np.round((values_closed+128)*256),0,65535))
            curves[index*3+2,:,0] = encoded_closed >> 8
            curves[index*3+2,:,1] = encoded_closed & 255
            eyes.append(dict(basis=[cx,cy,*axis], bounds=[xmin,xmax,width,int(eye.get("source_lids",False))]))
        # Closed art supplies skin only. Remove its lash line offline, so no closed
        # CG or blink-difference texture is sampled by the animation shader.
        if closed is not None:
            darkness = cv2.dilate(reference_lash,np.ones((5,5),np.uint8))
            skin = cv2.inpaint(closed,darkness,5,cv2.INPAINT_TELEA)
        else:
            skin = generated_skin
        precise_outline = any(eye.get("edit_polygon") for eye in definition["eyes"])
        feather = removal if precise_outline else cv2.GaussianBlur(removal,(5,5),.7)
        plate = rgb.copy()
        alpha = feather[...,None].astype(float)/255
        plate = np.uint8(np.clip(np.round(skin*alpha + rgb*(1-alpha)),0,255))
        if any(eye.get("source_lids") for eye in definition["eyes"]):
            # Transport actual ink only; skin stays on the clean underlay. Moving
            # whole original skin ribbons would drag nearby bangs and shadows.
            protection = (1-foreground.astype(np.float32)/255)*(removal.astype(np.float32)/255)
            upper_rgb = lower_rgb = rgb
            upper_alpha = np.uint8(np.round(original_upper*protection))
            lower_alpha = np.uint8(np.round(original_lower*protection))
        directory = ASSETS / family
        Image.fromarray(plate).save(directory / "eye-skin.png")
        Image.fromarray(feather).save(directory / "eye-region.png")
        Image.fromarray(foreground).save(directory / "eye-foreground.png")
        Image.fromarray(curves).save(directory / "eye-curves.png")
        Image.fromarray(np.array(ink_colors,dtype=np.uint8)[None,:,:]).save(directory / "eye-ink.png")
        for name, mask, colors in [("upper-lid",upper_alpha,upper_rgb),("lower-lid",lower_alpha,lower_rgb)]:
            if not any(eye.get("source_lids") for eye in definition["eyes"]):
                mask = cv2.GaussianBlur(mask,(3,3),.45)
            rgba = np.dstack([colors,mask])
            rgba[mask == 0,:3] = 0
            Image.fromarray(rgba).save(directory / (name+".png"))
        Image.fromarray(plate).resize((1280,720)).save(OUT / (family+"-skin.jpg"),quality=95)
        manifests[family] = eyes
        print(f"EYELIDS_BUILT {family}: {len(eyes)} eyes, continuous upper/lower strips")
    (PROJECT / "eye-rigs.json").write_text(json.dumps(manifests,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    build()
