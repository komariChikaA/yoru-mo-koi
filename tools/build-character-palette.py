"""Recolor character art while retaining its authored screen geometry.

Original mapset assets remain untouched. Shelf edges are drawn directly with
coverage AA; cards/arcs are supersampled with matching scale compensation.
Other assets retain their alpha. Design colors use the palette,
with only antialiasing interpolating endpoint colors.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/character-palette'
PALETTE = dict(blue='#C5DFE5', cream='#F3E7CC', ivory='#FAF3E4',
               mustard='#ECCB72', mist='#A5CED5', ink='#496F84',
               pink='#E5A0B5', wood='#C2A686', dark='#76503E')


def rgb(key):
    return tuple(bytes.fromhex(PALETTE[key][1:]))


def stroke():
    # Tintable stroke with straight ends; adjacent arcs must not accumulate
    # semi-transparent end caps into darker nodes.
    image = np.full((16,64,4),255,np.uint8)
    dy = np.abs(np.arange(16)-7.5)
    alpha = np.where(dy<=5.2,1,np.maximum(0,1-(dy-5.2)/2.2)**2)
    image[...,3] = np.round(255*alpha[:,None]).astype(np.uint8)
    OUT.mkdir(parents=True,exist_ok=True)
    Image.fromarray(image).save(OUT/'arc-stroke.png')
    spec = importlib.util.spec_from_file_location('character_arcs', ROOT/'tools/character-arcs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(OUT)


def nearest(data, pairs, antialias=False):
    """Map old semantic swatches in bounded chunks, preserving alpha verbatim."""
    old = np.array([p[0] for p in pairs], np.float32)
    new = np.array([rgb(p[1]) for p in pairs], np.uint8)
    flat = data[..., :3].reshape(-1, 3)
    if antialias:
        # Retain the source's coverage on internal book/rim edges. Find the
        # closest old endpoint segment, then interpolate only its new palette
        # endpoints. This preserves print edges instead of quantizing AA pixels.
        packed = (flat[:,0].astype(np.uint32)<<16) | (flat[:,1].astype(np.uint32)<<8) | flat[:,2]
        keys, inverse = np.unique(packed, return_inverse=True)
        values = np.column_stack((keys>>16, (keys>>8)&255, keys&255)).astype(np.float32)
        output = np.empty((len(keys),3),np.uint8)
        for start in range(0,len(keys),8192):
            v = values[start:start+8192]
            distance = ((v[:,None,:]-old[None,:,:])**2).sum(axis=2)
            near = np.argsort(distance,axis=1)[:,:4]
            best = distance[np.arange(len(v)),near[:,0]]
            colors = new[near[:,0]].astype(np.float32)
            for a in range(4):
                for b in range(a+1,4):
                    ai, bi = near[:,a], near[:,b]
                    origin, vector = old[ai], old[bi]-old[ai]
                    t = np.clip(((v-origin)*vector).sum(axis=1)/np.maximum(1,(vector**2).sum(axis=1)),0,1)
                    residual = ((v-origin-vector*t[:,None])**2).sum(axis=1)
                    use = residual < best-0.01
                    best[use] = residual[use]
                    colors[use] = new[ai[use]] + (new[bi[use]].astype(float)-new[ai[use]])*t[use,None]
            output[start:start+len(v)] = np.round(colors).astype(np.uint8)
        flat[:] = output[inverse]
        return data
    for start in range(0, len(flat), 65536):
        values = flat[start:start+65536].astype(np.float32)
        distances = ((values[:, None, :] - old[None, :, :])**2).sum(axis=2)
        flat[start:start+len(values)] = new[distances.argmin(axis=1)]
    return data


def shelf(data):
    spec = importlib.util.spec_from_file_location('character_shelf', ROOT/'tools/character-shelf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render(PALETTE,(data.shape[1],data.shape[0]))


def legacy_books(data):
    # Deterministic hue families of the old baked strip, retaining every pixel.
    arr = data[..., :3].astype(np.int16)
    hi, lo = arr.max(axis=2), arr.min(axis=2)
    red, green, blue = arr[..., 0], arr[..., 1], arr[..., 2]
    result = np.empty_like(data[..., :3])
    result[:] = rgb('mist')
    result[(red >= green) & (red >= blue)] = rgb('pink')
    result[(red > blue * 1.25) & (green > blue * 1.25)] = rgb('mustard')
    result[(blue >= red) & (blue >= green) & (green < blue*.65)] = rgb('ink')
    result[(hi-lo < 35) & (hi > 190)] = rgb('ivory')
    result[hi < 125] = rgb('dark')
    data[..., :3] = result
    return data


def glyph(data, main):
    old_fill = np.array((255,216,32) if main else (255,228,110), np.float32)
    old_ink = np.array((28,122,206) if main else (78,156,214), np.float32)
    new_fill = np.array(rgb('mustard' if main else 'ivory'), np.float32)
    new_ink = np.array(rgb('ink' if main else 'dark'), np.float32)
    vector = old_fill - old_ink
    coverage = np.clip(((data[..., :3]-old_ink)*vector).sum(axis=2)/np.dot(vector,vector), 0, 1)
    data[..., :3] = np.round(new_ink + coverage[..., None]*(new_fill-new_ink)).astype(np.uint8)
    return data


def build(mapset):
    OUT.mkdir(parents=True, exist_ok=True)
    records = []

    def save(relative, transform, original=None, preserve_alpha=True):
        source = mapset / (original or 'sb/'+relative)
        data = np.array(Image.open(source).convert('RGBA'))
        alpha = data[..., 3].copy()
        size = data.shape
        modified = transform(data)
        assert modified.shape == size
        if preserve_alpha:
            assert np.array_equal(modified[..., 3], alpha)
        dest = OUT / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(modified).save(dest)
        records.append(dict(source=str(source), file=relative,
                            size=[size[1],size[0]], alpha_sha256=hashlib.sha256(alpha.tobytes()).hexdigest(),
                            output_alpha_sha256=hashlib.sha256(modified[...,3].tobytes()).hexdigest(),
                            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                            output_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))

    def bg(data):
        # Same 4×480 placement; the requested upper and lower background colors.
        data[:240, :, :3] = rgb('blue')
        data[240:, :, :3] = rgb('cream')
        return data

    def solid_blue(data):
        data[..., :3] = rgb('blue')
        return data

    save('intro-bg.png', bg)
    save('bluebg.png', solid_blue, 'bluebg.jpg')
    save('arc-shelf.png', shelf, preserve_alpha=False)
    for name in ['books-up.png', 'books-down.png']:
        save(name, legacy_books)
    for source in sorted((mapset/'sb/flip').glob('*.png')):
        # Pink profile blocks paired with dark ink; neighboring blanks are ivory.
        field = 'pink' if source.stem in ('b00','b02','b06','b09') else 'mist'
        pairs = [((248,252,255),'ivory'), ((255,255,255),'ivory'),
                 ((186,224,242),field), ((255,232,160),'mustard'),
                 ((232,176,48),'ink'), ((32,108,176),'ink')]
        save('flip/'+source.name, lambda a, p=pairs: nearest(a, p, antialias=True))
    for source in sorted((mapset/'sb/ren-name').glob('*.png')):
        save('ren-name/'+source.name, lambda a, main=source.name.startswith('m-'): glyph(a,main))
    stroke()
    spec = importlib.util.spec_from_file_location('character_aa', ROOT/'tools/character-aa.py')
    aa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aa)
    # Supersampled cards use the same palette as the shelf and name, not stale defaults.
    aa.COLORS.update({key: PALETTE[key] for key in aa.COLORS})
    aa.build(OUT)
    manifest = dict(palette=PALETTE, paper=dict(file='sb/books-editorial/paper.png',
                   opacity=.09, scale=1.2, placement='behind character and name'), assets=records)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    aa.manifest(OUT)
    dest = mapset/'sb/character-palette'
    shutil.copytree(OUT,dest,dirs_exist_ok=True)
    print(f'Installed {len(records)} assets; 3x padded cards, 2x arcs; shelf geometry unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path, required=True)
    build(parser.parse_args().mapset)
