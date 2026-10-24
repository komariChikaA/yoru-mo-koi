"""Reconstruct the soft native sunset exposed by the complete U-shaped lock.

Only the expanded removal envelope is changed.  Native sky supplies its
boundary colours; firm gold upstream sections are replaced by adjacent sky in
the solve and are restored by their original fixed root bands/overlays.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import cv2
import numpy as np
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆/CGC15')
PART = '15-R13-left-returned-tail'


def repair(stage):
    spec = importlib.util.spec_from_file_location('layered_prepare', ROOT/'tools/prepare-layered-hair.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    record = json.loads((stage/'stage.json').read_text('utf-8'))
    part = next(p for p in record['parts'] if p['id'] == PART)
    before = np.array(Image.open(stage/'before.png').convert('RGB'))
    original = np.array(Image.open(BASE/'stage-15-F14-over-clothes-tail-circled-native-v2/repaired-plate.png').convert('RGB'))
    alpha = np.array(Image.open(stage/f'{PART}-mask.png').convert('L'))
    edit = cv2.dilate(np.uint8(alpha>3)*255, np.ones((43,43),np.uint8))
    edit = helper.clip_supported_side(edit, part)
    inside = edit>0
    boundary = before.astype(float)
    edge = cv2.dilate(np.uint8(inside),np.ones((3,3),np.uint8)).astype(bool)&~inside
    fixed = np.maximum(
        np.array(helper.contour_mask('M618,820 L624,820 L627,865 L621,865 Z')),
        np.array(helper.contour_mask('M630,820 L686,820 L694,863 L636,866 Z')))
    fixed = np.maximum(fixed, np.array(Image.open(BASE/'stage-15-S13-U-tip-hidden-under-long-lock/static-long-hair-fixed-root.png'))[:,:,3])
    root_edge = edge & (fixed>0)
    for y in range(1080):
        if root_edge[y].any():
            boundary[y,root_edge[y]] = np.median(original[max(0,y-2):min(1080,y+3),788:795].reshape(-1,3),axis=0)
    coords = np.argwhere(inside)
    ids = np.full(inside.shape,-1,int)
    ids[inside] = np.arange(len(coords))
    rr,cc,vv = [],[],[]
    rhs = np.zeros((len(coords),3))
    for k,(y,x) in enumerate(coords):
        rr.append(k);cc.append(k);vv.append(4.)
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny,nx = y+dy,x+dx
            if ny<0 or ny>=1080 or nx<0 or nx>=1920:
                rr.append(k);cc.append(k);vv.append(-1.)
            elif inside[ny,nx]:
                rr.append(k);cc.append(int(ids[ny,nx]));vv.append(-1.)
            else:
                rhs[k] += boundary[ny,nx]
    matrix = coo_matrix((vv,(rr,cc)),shape=(len(coords),len(coords))).tocsc()
    result = before.copy()
    result[inside] = np.clip(splu(matrix).solve(rhs),0,255).astype('uint8')
    # The root band is held still by the rig. Preserve its original first
    # pixels so a fractional cutout alpha never exposes a one-pixel dark seam.
    a,b = np.array(part['fixed_root_seam'],dtype=float)
    normal = np.array([-(b-a)[1],(b-a)[0]])
    normal /= np.linalg.norm(normal)
    if np.dot(np.array(part['chain'][1])-a,normal)<0:
        normal = -normal
    yy,xx = np.mgrid[:1080,:1920]
    distance = (xx-a[0])*normal[0]+(yy-a[1])*normal[1]
    join_shape = cv2.GaussianBlur(cv2.dilate(alpha,np.ones((7,7),np.uint8)),(0,0),1.0)/255.
    join_weight = join_shape*np.clip((42-distance)/12.,0,1)
    join_weight[(distance<0)|(xx>=715)|~inside] = 0
    result = np.round(result*(1-join_weight[:,:,None])+before*join_weight[:,:,None]).astype('uint8')
    Image.fromarray(result).save(stage/'repaired-plate.png')
    Image.fromarray(edit).save(stage/'allowed-edit-final.png')
    Image.fromarray(result).crop((580,825,1020,1080)).resize((1320,765)).save(stage/'exposed-sunset-final.png')
    record['state'] = 'native-layers-hidden-background-ready-for-animation'
    record['final_method'] = 'Native sunset harmonic interpolation in the complete expanded removal envelope; only actual firm gold root boundaries use adjacent native sky. Fixed native root bands and overlay restore those supports.'
    record['final_repair_command'] = f'python tools/repair-cgc15-u-sunset.py --stage "{stage}"'
    record['outside_final_edit_max_rgb'] = int(np.abs(before.astype(int)-result.astype(int))[~inside].max())
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps({'unknown_pixels':len(coords),'outside_final_edit_max_rgb':record['outside_final_edit_max_rgb']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,default=BASE/'stage-15-R13-left-returned-tail-circled-native-v2')
    repair(parser.parse_args().stage)
