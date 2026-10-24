"""Reuse the neutral low-contrast paper on the photograph margins, below the original CG."""
from pathlib import Path
import argparse,hashlib,json,shutil
from paper_material import MEMORY_OPACITY, SPARSE_OPACITY
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MAPSET=Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
def build(mapset):
    source=ROOT/'assets/books-editorial/paper.png'
    paper=Image.open(source).convert('RGB')
    paper=paper.resize((round(paper.width*1.2),round(paper.height*1.2)),Image.Resampling.LANCZOS)
    x,y=(paper.width-670)//2,(paper.height-424)//2
    out=ROOT/'assets/sequence-editorial'
    out.mkdir(parents=True,exist_ok=True)
    target=out/'photo-paper-grain.png'
    paper.crop((x,y,x+670,y+424)).save(target)
    (out/'manifest.json').write_text(json.dumps(dict(source='assets/books-editorial/paper.png',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),size=[670,424],texture_scale=1.2,
        title_paper_opacity=SPARSE_OPACITY,memory_paper_opacity=MEMORY_OPACITY,photo_margin_opacity=MEMORY_OPACITY,global_warm_opacity=0,
        print_mass_saturation=.92,print_mass_brightness=1.03,
        output_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf-8')
    dest=mapset/'sb/sequence-editorial'
    dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(target,dest/target.name)
    assert target.read_bytes()==(dest/target.name).read_bytes()
    print('Installed neutral photo-margin grain; CG and title textures untouched')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--mapset',type=Path,default=MAPSET)
    build(p.parse_args().mapset)
