"""Resolve the live installed fourth-shot frames overlapped by the early entry."""
from pathlib import Path
import json,shutil

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'godot/chorus-five'
PREVIOUS=Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ/sb/chorus-four')

def main():
    timeline=json.loads((PROJECT/'timeline.json').read_text(encoding='utf8'))
    rows=[r.split('\t') for r in (PREVIOUS/'frames.tsv').read_text().splitlines()]
    out=PROJECT/'assets/entry-previous';out.mkdir(parents=True,exist_ok=True)
    frames=[]
    for name,start,end in rows:
        if float(end)/1000<=timeline['song_start']:continue
        shutil.copy2(PREVIOUS/name,out/name)
        frames.append({'song_start':float(start)/1000,'texture':f'res://assets/entry-previous/{name}'})
    (out/'manifest.json').write_text(json.dumps({'previous_tsv':str(PREVIOUS/'frames.tsv'),
        'previous_end':float(rows[-1][2])/1000,'song_start':timeline['song_start'],'frames':frames},
        ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Prepared {len(frames)} installed preceding frames from {timeline["song_start"]:.3f}s; tail holds after {float(rows[-1][2])/1000:.3f}s')

if __name__=='__main__':main()
