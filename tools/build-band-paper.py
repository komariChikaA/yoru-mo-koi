"""Crop the existing low-contrast paper to the diagonal-band sprite; no new texture source."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
from paper_material import BACKGROUND_OPACITY
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')

def build(mapset):
    source = ROOT / 'assets/books-editorial/paper.png'
    mask_source = mapset / 'sb/band.png'
    mask = Image.open(mask_source).convert('RGBA')
    paper = Image.open(source).convert('RGB')
    # Same 120% enlargement as the books/character page, then a crop, not a stretched strip.
    paper = paper.resize((round(paper.width * 1.2), round(paper.height * 1.2)), Image.Resampling.LANCZOS)
    w, h = mask.size
    x, y = (paper.width-w)//2, (paper.height-h)//2
    if x < 0 or y < 0:
        raise ValueError('The enlarged paper must cover the band before cropping')
    band = paper.crop((x,y,x+w,y+h)).convert('RGBA')
    band.putalpha(mask.getchannel('A'))
    out = ROOT / 'assets/band-editorial'
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'paper-band.png'
    band.save(path)
    (out / 'manifest.json').write_text(json.dumps(dict(
        source='assets/books-editorial/paper.png', source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        mask='sb/band.png', mask_sha256=hashlib.sha256(mask_source.read_bytes()).hexdigest(),
        size=[w,h], texture_scale=1.2, overlay_opacity=BACKGROUND_OPACITY,
        output_sha256=hashlib.sha256(path.read_bytes()).hexdigest()), indent=2)+'\n', encoding='utf-8')
    dest = mapset / 'sb/band-editorial'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dest / path.name)
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256((dest/path.name).read_bytes()).digest()
    print(f'Built and installed {w}x{h} band paper at 10% opacity; hashes match')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapset', type=Path, default=DEFAULT_MAPSET)
    build(parser.parse_args().mapset)
