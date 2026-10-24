"""Register gpt-image-2 repairs; preserve native pixels outside edit masks."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'godot/chorus-four/assets';WORK=A/'cleanplate-work'

def rgb(path):return np.array(Image.open(path).convert('RGB'))

def register(source,target,mask):
    source=cv2.resize(source,(target.shape[1],target.shape[0]),interpolation=cv2.INTER_LANCZOS4)
    detector=cv2.SIFT_create(nfeatures=5000)
    ka,da=detector.detectAndCompute(cv2.cvtColor(source,cv2.COLOR_RGB2GRAY),None)
    kb,db=detector.detectAndCompute(cv2.cvtColor(target,cv2.COLOR_RGB2GRAY),255-mask)
    matches=cv2.BFMatcher().knnMatch(da,db,k=2)
    good=[m for m,n in matches if m.distance<n.distance*.67]
    if len(good)<8:raise ValueError('Too few clean-plate registration features')
    start=np.float32([ka[m.queryIdx].pt for m in good]);end=np.float32([kb[m.trainIdx].pt for m in good])
    matrix,inliers=cv2.estimateAffinePartial2D(start,end,method=cv2.RANSAC,ransacReprojThreshold=2.5)
    aligned=cv2.warpAffine(source,matrix,(target.shape[1],target.shape[0]),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_REFLECT)
    return aligned,dict(affine=matrix.tolist(),matches=len(good),inliers=int(inliers.sum()))

def compose():
    original=rgb(A/'CGC14_a.png')
    hair_mask=np.array(Image.open(A/'CGC14-wind/selection.png'))
    edit=cv2.dilate(np.uint8(hair_mask>127)*255,np.ones((5,5),np.uint8))
    aligned,hair_record=register(rgb(WORK/'hair-generated-v2.png'),original,cv2.dilate(edit,np.ones((25,25),np.uint8)))
    # Blend the registered hidden painting using Poisson boundary conditions;
    # native roots and intersection caps are restored separately below.
    x,y,w,h=cv2.boundingRect(edit)
    blended=cv2.seamlessClone(aligned,original,edit.copy(),(x+w//2,y+h//2),cv2.NORMAL_CLONE)
    alpha=edit/255.0
    yy,xx=np.mgrid[:1080,:1920]
    for definition in json.loads((ROOT/'godot/chorus-four/cgc14-hair-regions.json').read_text()):
        for key,anchor in [('root_pin',definition['chain'][0]),('tip_pin',definition['chain'][-1])]:
            if key not in definition:continue
            x,y=anchor;radius=definition[key][1]+42
            distance=np.hypot(xx-x,yy-y)
            fade=np.clip((distance-radius)/24,0,1);fade=fade*fade*(3-2*fade)
            alpha*=fade
    plate=np.uint8(np.clip(original*(1-alpha[:,:,None])+blended*alpha[:,:,None],0,255))
    eye_native=original[110:500,1400:1790]
    eye_mask=np.array(Image.open(A/'CGC14-eyes/edit-region.png'))[110:500,1400:1790]
    generated,eye_record=register(rgb(WORK/'eye-generated.png'),eye_native,eye_mask)
    x,y,w,h=cv2.boundingRect(eye_mask)
    matched=cv2.seamlessClone(generated,eye_native,eye_mask.copy(),(x+w//2,y+h//2),cv2.NORMAL_CLONE)
    matched[eye_mask==0]=eye_native[eye_mask==0]
    region=plate[110:500,1400:1790]
    region[eye_mask>0]=matched[eye_mask>0]
    mouth_mask=np.zeros((1080,1920),np.uint8)
    cv2.ellipse(mouth_mask,(1528,366),(13,8),54,0,360,255,-1)
    donor=cv2.warpAffine(original,np.float32([[1,0,18],[0,1,0]]),(1920,1080),borderMode=cv2.BORDER_REFLECT)
    mouth_clean=cv2.seamlessClone(donor,plate,mouth_mask.copy(),(1528,366),cv2.NORMAL_CLONE)
    plate[mouth_mask>0]=mouth_clean[mouth_mask>0]
    Image.fromarray(plate).save(A/'CGC14-native-clean.png')
    Image.fromarray(plate[110:500,1400:1790]).resize((1024,1024)).save(WORK/'eye-composite-review.png')
    changed=np.maximum.reduce([edit,np.pad(eye_mask,((110,580),(1400,130))),mouth_mask])
    record=dict(model='gpt-image-2',hair=hair_record,eyes=eye_record,
      outside_edit_max_rgb=int(np.abs(plate.astype(int)-original.astype(int))[changed==0].max()),
      process='Registered generated hidden plates + native exterior restoration; native moving parts are unchanged.')
    (WORK/'registration.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':compose()
