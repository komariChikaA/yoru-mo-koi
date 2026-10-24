"""Existing character focus and the shared LightingFx resources."""
from pathlib import Path
import argparse,shutil
import numpy as np
from PIL import Image
from lighting_fx_assets import build as build_lighting

ROOT=Path(__file__).resolve().parents[1]


def build(mapset):
    out=ROOT/'assets/character-palette/effects'
    out.mkdir(parents=True,exist_ok=True)
    y,x=np.mgrid[:480,:854]
    a=np.exp(-(((x-500)/235)**2+((y-310)/180)**2)*1.8)
    data=np.empty((480,854,4),np.uint8)
    data[...,:3]=(230,199,165)  # #E6C7A5, below the original character art
    data[...,3]=np.round(a*255).astype(np.uint8)
    Image.fromarray(data).save(out/'focus.png')
    target=mapset/'sb/character-palette/effects'
    target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(out/'focus.png',target/'focus.png')
    build_lighting(mapset)
    print('Installed existing character focus')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mapset',type=Path,required=True)
    build(parser.parse_args().mapset)
