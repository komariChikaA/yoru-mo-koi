"""Regenerate only editorial paper resources; never rebuild original art or animation masks."""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
from PIL import Image
from paper_material import stock, enlarged, opening_stock, CONTRAST, MEMORY_OPACITY, SPARSE_OPACITY
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[1]
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')

def install(path, mapset, folder):
    dest = mapset/'sb'/folder/path.name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,dest)
    assert path.read_bytes()==dest.read_bytes()

def build(mapset):
    paper = stock()
    path = ROOT/'assets/books-editorial/paper.png'
    paper.save(path)
    install(path,mapset,'books-editorial')
    manifest = path.parent/'manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    data.update(paper_contrast=CONTRAST,paper_contrast_increase=1.15,paper_opacity=.10)
    manifest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    tile,page = opening_stock((243,221,129))
    for name,image in [('tile.png',tile),('paper.png',page)]:
        path=ROOT/'assets/title-bumper'/name
        image.save(path)
        install(path,mapset,'title-bumper')
    manifest=path.parent/'manifest.json'
    data=json.loads(manifest.read_text(encoding='utf-8'))
    data.pop('seed',None)
    data.update(paper_source='imagetexture_00049.jpg',paper_opacity=SPARSE_OPACITY)
    manifest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    # Fixed world-space crop: flowing bounds change but the grain does not crawl.
    full = enlarged()
    flow_dir=ROOT/'assets/paper-material/flow'
    flow_dir.mkdir(parents=True,exist_ok=True)
    layout=ROOT/'assets/memory-flow/layout.txt'
    for line in layout.read_text().splitlines():
        name,_,cx,cy=line.split()
        original=Image.open(ROOT/'assets/memory-flow'/name).convert('RGBA')
        w,h=original.size
        x=round(float(cx)-w/2+192.5)
        y=round(float(cy)-h/2-681+19)
        # Periodically extend the same stock for the long liquid neck above the page.
        yy,xx=np.mgrid[y:y+h,x:x+w]
        grain=np.asarray(full)[yy%full.height,xx%full.width].astype(float)
        a=np.array(original)
        a[...,:3]=np.rint(255*(1-MEMORY_OPACITY)+grain*MEMORY_OPACITY).astype('uint8')
        result=Image.fromarray(a)
        result.save(flow_dir/name)
        install(flow_dir/name,mapset,'paper-material/flow')
        assert np.array_equal(a[...,3],np.array(original)[...,3])
    # Photo-space grain for cached reveal masks and the temporary full-plane wash.
    out=ROOT/'assets/paper-material'
    for name,size in [('print-grain.png',(640,403)),('fill-grain.png',(854,538))]:
        w,h=size
        x,y=(full.width-w)//2,(full.height-h)//2
        full.crop((x,y,x+w,y+h)).save(out/name)
        install(out/name,mapset,'paper-material')
    (out/'manifest.json').write_text(json.dumps(dict(source='imagetexture_00049.jpg',
        contrast=CONTRAST,contrast_increase=1.15,scale=1.2,background_opacity=.10,
        sparse_opacity=SPARSE_OPACITY,memory_opacity=MEMORY_OPACITY,
        flow_frames=len(layout.read_text().splitlines()),alpha_preserved=True),indent=2)+'\n',encoding='utf-8')
    for name in ['build-band-paper','build-sequence-paper']:
        spec=spec_from_file_location(name,ROOT/'tools'/f'{name}.py')
        module=module_from_spec(spec);spec.loader.exec_module(module);module.build(mapset)
    print('Installed shared paper only; original artwork, mask alpha and layouts preserved')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mapset',type=Path,default=MAPSET)
    build(p.parse_args().mapset)
