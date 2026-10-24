"""Register and color-match the generated eye-free plate to the native CGC06 a."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/'assets/chorus-cgc06'
EYES=ROOT/'godot/chorus-cgc06/assets/eyes'


def compose():
    metadata=json.loads((SOURCES/'eye-clean-plate.json').read_text(encoding='utf-8'))
    generated=np.array(Image.open(SOURCES/'eye-clean-plate-generated.png').convert('RGB')
                       .resize((1152,1536),Image.Resampling.LANCZOS))
    aligned=cv2.warpAffine(generated,np.array(metadata['generated_to_input_affine']),
                          (1152,1536),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_REFLECT)
    patch=np.array(Image.fromarray(aligned).resize((285,380),Image.Resampling.LANCZOS))
    original=np.array(Image.open(EYES.parent/'a-plate.png').convert('RGB'))
    region=np.array(Image.open(EYES/'eye-region.png')).max(2)
    mask=cv2.dilate(np.uint8(region>0)*255,np.ones((9,9),np.uint8))
    for name in ['edge-detail-1.png','edge-detail-2.png']:
        alpha=np.array(Image.open(EYES/name))[:,:,3]
        mask=np.maximum(mask,cv2.dilate(np.uint8(alpha>0)*255,np.ones((13,13),np.uint8)))
    fringe=np.zeros_like(mask)
    cv2.fillPoly(fringe,[np.array([(914,198),(920,200),(925,216),(919,231),
                                  (910,231),(909,214)],np.int32)],255)
    mask=np.maximum(mask,fringe)
    local_mask=mask[60:440,770:1055].copy()
    x,y,w,h=cv2.boundingRect(local_mask)
    native=original[60:440,770:1055]
    # OpenCV mutates its mask argument. Keep the original mask for exact
    # exterior restoration; otherwise removed eyes are copied back in.
    matched=cv2.seamlessClone(patch,native,local_mask.copy(),
                              (x+w//2,y+h//2),cv2.NORMAL_CLONE)
    matched[local_mask==0]=native[local_mask==0]
    result=original.copy()
    result[60:440,770:1055]=matched
    Image.fromarray(result).save(SOURCES/'eye-clean-plate.png')
    Image.fromarray(mask).save(SOURCES/'eye-clean-plate-mask.png')
    metadata['outside_edit_mask_max_rgb']=int(np.abs(result.astype(int)-original.astype(int))[mask==0].max())
    metadata['composition']='Complete generated eye-free footprints, registered to native a; gradient matching to native lighting, exact original outside edit mask. No manual skin fills.'
    (SOURCES/'eye-clean-plate.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('Eye-free plate composed; exterior max RGB delta:',metadata['outside_edit_mask_max_rgb'])


if __name__=='__main__':
    compose()
