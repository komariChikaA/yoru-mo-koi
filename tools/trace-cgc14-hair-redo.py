import argparse,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fontTools.svgLib.path import parse_path
from fontTools.pens.basePen import BasePen
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r'../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆/CGC14')
J=ROOT/'godot/chorus-four/hair-redo/CGC14-traces.json'
class Flatten(BasePen):
 def __init__(self): super().__init__(None); self.polys=[];self.points=[]
 def _moveTo(self,p):
  if self.points:self.polys.append(self.points)
  self.points=[p]
 def _lineTo(self,p):self.points.append(p)
 def _curveToOne(self,p1,p2,p3):
  p0=self.points[-1];n=max(10,int(sum(math.dist(a,b) for a,b in [(p0,p1),(p1,p2),(p2,p3)])/1.0))
  for i in range(1,n+1):
   t=i/n;s=1-t;self.points.append((s**3*p0[0]+3*s*s*t*p1[0]+3*s*t*t*p2[0]+t**3*p3[0],s**3*p0[1]+3*s*s*t*p1[1]+3*s*t*t*p2[1]+t**3*p3[1]))
 def _closePath(self):self.polys.append(self.points);self.points=[]
 def _endPath(self):
  if self.points:self.polys.append(self.points);self.points=[]
def polygons(d):
 p=Flatten();parse_path(d,p);p._endPath();return p.polys
parser=argparse.ArgumentParser()
parser.add_argument('--ids',nargs='+',help='Export only the named authored clumps')
args=parser.parse_args()
doc=json.loads(J.read_text(encoding='utf-8'))
im=Image.open(ROOT/doc['source']).convert('RGBA')
OUT.mkdir(parents=True,exist_ok=True)
over=im.copy();od=ImageDraw.Draw(over)
colors=[(0,255,255),(255,0,255),(90,255,50),(255,210,0),(70,130,255)]
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27)
for i,item in enumerate(doc['front_to_back']):
 if args.ids and item['id'] not in args.ids:continue
 if not item.get('ready_for_extract',False) or not item.get('outline'):continue
 assert not item.get('prior_repaired_required') or item.get('extraction_source'), (item['id'],'Use the preceding repaired plate for this layer')
 source=Path(item.get('extraction_source',str(ROOT/doc['source'])))
 if not source.is_absolute():source=ROOT/source
 part_im=Image.open(source).convert('RGBA')
 polys=[p for d in item.get('outlines',[item['outline']]) for p in polygons(d)];mask=Image.new('L',(1920*4,1080*4));md=ImageDraw.Draw(mask)
 for p in polys:md.polygon([(x*4,y*4) for x,y in p],fill=255)

 for d in item.get('exclude',[]):
  for p in polygons(d):md.polygon([(x*4,y*4) for x,y in p],fill=0)
 mask=mask.resize((1920,1080),Image.Resampling.LANCZOS);mask.save(OUT/(item['id']+'-mask.png'))
 piece=part_im.copy();piece.putalpha(mask);piece.save(OUT/(item['id']+'-native.png'))
 b=mask.getbbox();x0=max(0,b[0]-20);y0=max(0,b[1]-20);x1=min(1920,b[2]+20);y1=min(1080,b[3]+20)
 checker=Image.new('RGBA',(x1-x0,y1-y0),(75,75,75,255));cd=ImageDraw.Draw(checker)
 for y in range(0,checker.height,16):
  for x in range(0,checker.width,16):
   if (x//16+y//16)%2:cd.rectangle((x,y,x+15,y+15),fill=(115,115,115))
 checker.alpha_composite(piece.crop((x0,y0,x1,y1)));checker.resize((checker.width*2,checker.height*2)).convert('RGB').save(OUT/(item['id']+'-check.png'))
 context=part_im.crop((x0,y0,x1,y1)).resize(((x1-x0)*4,(y1-y0)*4)).convert('RGB');bd=ImageDraw.Draw(context)
 for p in polys:bd.line([((x-x0)*4,(y-y0)*4) for x,y in p+[p[0]]],fill=(0,255,240),width=1)
 cut=item.get('fixed_transition',{}).get('cut_line')
 if cut:bd.line([((x-x0)*4,(y-y0)*4) for x,y in cut],fill=(255,80,30),width=4)
 context.save(OUT/(item['id']+'-boundary-4x.png'))
 for p in polys:od.line(p+[p[0]],fill=colors[i%len(colors)],width=3)
 p=item.get('label_at',item['chain'][-1]);od.text((p[0],p[1]),item['id'].split('_')[1],fill=colors[i%len(colors)],stroke_fill='black',stroke_width=2,font=font)
over.save(OUT/'CGC14-native-boundaries.png')
print(str(OUT))
