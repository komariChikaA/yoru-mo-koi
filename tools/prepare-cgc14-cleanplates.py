"""Preserve native targets, masks and prompts for static underlay painting."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'godot/chorus-four/assets'
OUT=ASSETS/'cleanplate-work'
OUT.mkdir(exist_ok=True)
original=Image.open(ASSETS/'CGC14_a.png').convert('RGB')
original.save(OUT/'hair-input.png')
union=np.array(Image.open(ASSETS/'CGC14-wind/selection.png'))
erase=cv2.dilate(np.uint8(union>0)*255,np.ones((9,9),np.uint8))
rgba=np.full((1080,1920,4),255,np.uint8);rgba[:,:,3]=255-erase
Image.fromarray(rgba).save(OUT/'hair-mask.png')
(OUT/'hair-prompt.txt').write_text('Edit this anime illustration as a static animation clean plate. Remove ONLY the individual long hair ribbons and flyaway strands in the transparent edit-mask regions, and reconstruct the hidden warm sunset bokeh background, remaining adjacent fixed golden hair, or pink sleeve fabric beneath them. Preserve the hairstyle silhouette of all unmasked hair. In particular continue the smooth ink outlines of adjacent remaining hair and the pink sleeve, without smeared strands, cut-off stubs, ghost hair, blur patches, or new isolated locks. The selected upper left arcs and lower right loop will be restored later as native animated cutouts: remove them fully within the mask. Preserve the exact character, face, eyes, clothes, lighting, original coordinates, sharp anime linework and composition everywhere else. No new objects, no text, no border. This is a hidden static background repair, not a redesigned image.',encoding='utf-8')
box=(1400,110,1790,500)
original.crop(box).resize((1024,1024),Image.Resampling.LANCZOS).save(OUT/'eye-input.png')
mask=np.zeros((1080,1920),np.uint8)
for center,axes,angle in [((1547,239),(62,60),52),((1665,366),(69,64),54)]:
    cv2.ellipse(mask,center,axes,angle,0,360,255,-1)
rgba=np.full((1080,1920,4),255,np.uint8);rgba[:,:,3]=255-mask
Image.fromarray(rgba).crop(box).resize((1024,1024),Image.Resampling.LANCZOS).save(OUT/'eye-mask.png')
Image.fromarray(mask).save(OUT/'eye-edit-region.png')
(OUT/'eye-prompt.txt').write_text('Make a static hidden clean plate for native 2D puppet animation. Remove BOTH entire eyes (all eyelashes, eyelid outlines, sclera, irises, pupils and highlights), eyebrows and short eyelid crease lines, leaving complete naturally painted uninterrupted skin where those features used to be. Carefully reconstruct the exact warm peach skin light and shadow gradient, fine blush hatching and the tapered golden hair strands that overlap the eye regions. Preserve and continue each foreground golden strand, its original thin dark outline and its sharp tapered tip. Do not draw closed eyes, eyelid lines, replacement eyes or any new facial feature. Keep the nose, mouth, face contour, earrings, clothing, golden bangs and lighting exactly in their original positions. The blank skin under the eyes will be hidden behind the original native eye cutouts. Match original anime rendering and linework, no broad smears, no blurry skin blocks. Preserve the entire composition and coordinates.',encoding='utf-8')
print(OUT)
