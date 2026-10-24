"""Native palm cutout, fixed wrist, and imagegen-repaired hidden blossom plate.

Run after the existing hair preparer. The selected repair is a local input;
this script never calls a generation service or changes the source CG.
"""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'godot/chorus-five/assets'
OUT=A/'hand'; INPUT=A/'hand-repairs/hand-background-generated.png'
CROP=(350,420,950,1020)
PALM=[(566,588),(568,587),(572,588),(580,593),(592,603),(604,611),
      (617,617),(637,621),(650,625),(660,631),(666,638),(672,649),
      (679,660),(681,670),(680,680),(676,690),(670,700),(667,704),
      (662,700),(648,701),(627,701),(610,700),(595,701),(581,705),
      (570,708),(564,709),(559,708),(555,704),(548,696),(542,688),
      (535,686),(529,682),(521,674),(513,666),(505,658),(499,652),
      (494,647),(492,643),(491,640),(492,638),(489,637),(488,634),
      (489,631),(491,629),(496,630),(498,626),(501,624),(507,624),
      (519,627),(531,631),(541,637),(544,640),(559,640),(577,639),
      (589,633),(594,632),(594,628),(585,619),(575,611),(570,605),
      (567,599),(565,593),(565,590)]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=Image.open(A/'source-clean.png').convert('RGB')
    scale=4
    mask=Image.new('L',(1920*scale,1080*scale))
    ImageDraw.Draw(mask).polygon([(x*scale,y*scale) for x,y in PALM],fill=255)
    mask=mask.resize(source.size,Image.Resampling.LANCZOS)
    alpha=np.asarray(mask)
    # Native RGB and a subpixel silhouette retain the painted hand linework.
    rect=(482,580,690,718)
    rgb=np.asarray(source)
    # The hand's cream/pink skin and brown ink have G >= B; the adjacent
    # magenta blossoms have B > G. Refine only the outer three-pixel band.
    solid=cv2.erode(alpha,np.ones((7,7),np.uint8))>250
    colour=np.clip((rgb[...,1].astype(float)-rgb[...,2].astype(float)+1)/5,0,1)
    # The warm red wrist shadow legitimately has B > G. Keep its native
    # silhouette at the cuff; colour rejection applies to the fingers only.
    colour[:,635:]=1.0
    native_alpha=np.rint(alpha*np.where(solid,1.0,colour)).astype('uint8')
    contours,_=cv2.findContours((native_alpha>127).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour=cv2.approxPolyDP(max(contours,key=cv2.contourArea),.55,True).reshape(-1,2)
    smooth=Image.new('L',(1920*scale,1080*scale))
    ImageDraw.Draw(smooth).polygon([(int(x)*scale,int(y)*scale) for x,y in contour],fill=255)
    native_alpha=np.asarray(smooth.resize(source.size,Image.Resampling.LANCZOS))
    local_rgb=rgb[rect[1]:rect[3],rect[0]:rect[2]].copy()
    local_alpha=native_alpha[rect[1]:rect[3],rect[0]:rect[2]]
    _,nearest=distance_transform_edt(local_alpha<240,return_indices=True)
    local_rgb[local_alpha<128]=local_rgb[nearest[0],nearest[1]][local_alpha<128]
    Image.fromarray(np.dstack([local_rgb,local_alpha]),'RGBA').save(OUT/'palm.png')

    clean=Image.open(A/'hair/source-hair-clean.png').convert('RGB')
    target=np.asarray(clean.crop(CROP))
    generated=np.asarray(Image.open(INPUT).convert('RGB').resize((600,600),Image.Resampling.LANCZOS))
    support=np.ones((600,600),np.uint8)*255
    support[155:310,125:340]=0
    warp=np.eye(2,3,dtype=np.float32)
    score,warp=cv2.findTransformECC(cv2.cvtColor(target,cv2.COLOR_RGB2GRAY),
        cv2.cvtColor(generated,cv2.COLOR_RGB2GRAY),warp,cv2.MOTION_AFFINE,
        (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,120,1e-6),support,5)
    registered=cv2.warpAffine(generated,warp,(600,600),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REFLECT)
    Image.fromarray(registered).save(OUT/'registered-background.png')
    background=np.asarray(clean).copy();background[420:1020,350:950]=registered
    # Clear the full native footprint plus its antialiased edge. The join
    # inside the dark cuff is pinned; no invented moving sleeve is needed.
    removal=cv2.dilate(alpha,np.ones((5,5),np.uint8))
    removal=cv2.GaussianBlur(removal,(0,0),.55)/255.0
    removal[:,681:]=0
    def repaired(im):
        pixels=np.asarray(im.convert('RGB'))
        return Image.fromarray(np.rint(pixels*(1-removal[...,None])+background*removal[...,None]).clip(0,255).astype('uint8'))
    repaired(clean).save(OUT/'source-hand-clean.png')
    repaired(source).save(OUT/'foreground-hand-clean.png')
    for name,original in [('occlusion','occlusion'),('foreground','foreground')]:
        occ=np.asarray(Image.open(A/f'hair/{original}.png').convert('L')).copy()
        occ[removal>.02]=0
        Image.fromarray(occ).save(OUT/f'{name}.png')
    mask.save(OUT/'palm-mask.png')
    previous=Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ/sb/chorus-four')
    last=(previous/'frames.tsv').read_text().splitlines()[-1].split('\t')[0]
    Image.open(previous/last).convert('RGB').save(OUT/'entry-previous.png')
    data={'rect':list(rect),'pivot':[673,669],'texture':'res://assets/hand/palm.png',
          'previous_installed':str(previous/last),'repair_input':str(INPUT.relative_to(ROOT)),
          'repair_crop':list(CROP),'registration_affine':warp.tolist(),'registration_score':float(score),
          'skin_outline':PALM,'motion':'fixed-wrist, smooth palm rotation and delayed finger follow'}
    (OUT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Prepared native hand / fixed wrist (673,669); hidden-background registration {score:.5f}')

if __name__=='__main__':main()
