"""Prepare only the separately authored CGC14 face follow-up hair parts.

The shared contour/compose utilities are reused, while central traces, runtime,
and production policy stay untouched. Subsequent extraction always uses a
preceding repaired plate passed with --prior.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT/'godot/chorus-four/hair-redo/CGC14-face-followup.json'
OUT = Path('../../工作文件夹/output/CGC14-15_scene4/头发逐层重拆/CGC14/face-followup')
spec = importlib.util.spec_from_file_location('layered_hair', ROOT/'tools/prepare-layered-hair.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def review(definition):
    image = Image.open(Path(definition['starting_prior'])/'repaired-plate.png').convert('RGBA')
    overlay = image.copy()
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    for i, part in enumerate(definition['front_to_back']):
        mask = helper.part_mask(part)
        native = image.copy()
        native.putalpha(mask)
        native.save(OUT/(part['id']+'-candidate-native.png'))
        x1,y1,x2,y2=mask.getbbox()
        box=(x1-15,y1-15,x2+15,y2+15)
        crop=native.crop(box)
        check=Image.alpha_composite(Image.new('RGBA',crop.size,'#394654'),crop)
        check.resize((check.width*4,check.height*4)).convert('RGB').save(OUT/(part['id']+'-candidate-check.png'))
        colour=['#00ffff','#70ff20','#ff00ff'][i]
        edge=Image.new('RGBA',image.size,colour)
        edge.putalpha(mask.filter(ImageFilter.FIND_EDGES))
        overlay=Image.alpha_composite(overlay,edge)
        draw=ImageDraw.Draw(overlay)
        draw.line([tuple(v) for v in part['fixed_root_seam']],fill='red',width=3)
        x,y=part['label_at']
        draw.text((x,y),part['label'],font=font,fill=colour,stroke_width=2,stroke_fill='#202020')
    overlay.convert('RGB').save(OUT/'all-candidate-contours.png')
    overlay.crop((1190,185,1765,355)).resize((1725,510)).convert('RGB').save(OUT/'face-candidate-contours-detail.png')
    print(OUT/'face-candidate-contours-detail.png')


def prepare(definition, selected, prior, variant):
    part = next(p for p in definition['front_to_back'] if p['id']==selected)
    assert part['ready_for_extract'], 'Root contour review is pending'
    prior=Path(prior)
    old=read(prior/'stage.json')
    assert set(part.get('occluded_by',[])).issubset(old['removed_ids']), 'Remove and repair actual foreground first'
    stage=OUT/('stage-'+selected+'-'+variant)
    stage.mkdir(exist_ok=True)
    image=Image.open(prior/'repaired-plate.png').convert('RGB')
    image.save(stage/'before.png')
    mask=helper.part_mask(part)
    mask.save(stage/(selected+'-mask.png'))
    native=image.convert('RGBA');native.putalpha(mask);native.save(stage/(selected+'-native.png'))
    edit=cv2.dilate(np.uint8(np.array(mask)>6)*255,np.ones((13,13),np.uint8))
    edit=helper.clip_supported_side(edit,part)
    Image.fromarray(edit).save(stage/'allowed-edit.png')
    x,y,w,h=cv2.boundingRect(edit)
    side=max(384,max(w,h)+64)
    left=max(0,min(1920-side,x+w//2-side//2));top=max(0,min(1080-side,y+h//2-side//2))
    box=[left,top,left+side,top+side]
    image.crop(box).resize((1024,1024),Image.Resampling.LANCZOS).save(stage/'edit-input.png')
    alpha=Image.fromarray(255-edit).crop(box).resize((1024,1024),Image.Resampling.NEAREST)
    request=Image.new('RGBA',(1024,1024),'white');request.putalpha(alpha);request.save(stage/'edit-mask.png')
    overlays=[]
    for value in old.get('static_overlays',[]):
        assert isinstance(value,str)
        value=Path(value);overlays.append(str(value if value.is_absolute() else prior/value))
    record=dict(cg=14,input=str(prior/'repaired-plate.png'),ids=[selected],
        removed_ids=old['removed_ids']+[selected],static_overlays=overlays,crop=box,
        request_size=[1024,1024],parts=[part],state='root-contour-approved-awaiting-hidden-plate',
        amplitude_reference=dict(old_multiplier=16,perceived_percent=100))
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    prompt=('Use case: precise-object-edit. Make ONE static hidden surface for a 2D anime hair puppet. '
        'Remove ONLY the foreground hair part in the transparent mask: '+part['label']+'. '+part['notes']+' '
        'Continue the actual underlying surfaces: '+part['hidden_reconstruction']+'. '
        'Remove the whole selected native golden and dark-brown volume, every selected same-cluster tip, '
        'its outline and its attached cast-shadow rim. Keep the support cut and firmly supported upstream hair fixed. '
        'Preserve ALL unmasked native face, eyes, eyelashes, eyebrows, nose, mouth, skin, clothing, jewellery, '
        'other hair, coordinates, light and composition. No new hair, detached tips, flat patches, blur, '
        'mosaic, smears, text, labels or borders. Opaque image, original anime linework and shading. '
        'This is a hidden surface reconstruction, not an animation frame or redesign.')
    (stage/'prompt.txt').write_text(prompt,encoding='utf-8')
    print(stage)


def clean_texture(stage):
    stage=Path(stage)
    record=read(stage/'stage.json')
    assert len(record['parts'])==1 and record['ids']==[record['parts'][0]['id']]
    part=record['parts'][0]
    image=Image.open(stage/'before.png').convert('RGB')
    rgb=np.array(image)
    coverage=np.array(helper.part_mask(part))
    native=Image.open(stage/(part['id']+'-native.png')).convert('RGBA')
    native.save(stage/(part['id']+'-native-before-texture-clean.png'))
    record['static_overlays']=[value for value in record['static_overlays'] if str(stage/'static-face-crossing-') not in value]
    masks=[]
    for i,path in enumerate(part.get('static_crossings',[])):
        mask=np.array(helper.contour_mask(path))
        masks.append(mask)
        overlay=image.convert('RGBA');overlay.putalpha(Image.fromarray(mask))
        name='static-face-crossing-'+str(i)+'.png'
        overlay.save(stage/name)
        record['static_overlays'].append(str(stage/name))
    local=part.get('local_texture_repair_regions',[])
    masks += [np.array(helper.contour_mask(path)) for path in local]
    if not masks and not part.get('tail_sections'):
        return
    full=np.maximum.reduce(masks) if masks else np.zeros(coverage.shape,dtype=np.uint8)
    padding=part.get('crossing_repair_padding',0)
    if padding:full=cv2.dilate(full,np.ones((padding*2+1,padding*2+1),np.uint8))
    blocked=cv2.dilate(np.uint8(full>4)*255,np.ones((3,3),np.uint8))
    target=np.minimum(full,coverage)
    yy,xx=np.mgrid[:1080,:1920].astype(np.float32)
    first,last=np.array(part['chain'][0]),np.array(part['chain'][-1])
    axis=np.asarray((last-first)/np.linalg.norm(last-first),dtype=np.float32)
    values=[];distances=[];found_values=[]
    for sign in [-1,1]:
        distance=np.zeros_like(xx);pending=target>0
        for step in range(1,49):
            mx,my=xx+axis[0]*step*sign,yy+axis[1]*step*sign
            good=(cv2.remap(blocked,mx,my,cv2.INTER_NEAREST)==0)&(cv2.remap(coverage,mx,my,cv2.INTER_NEAREST)>64)
            found=pending&good;distance[found]=step+0.5;pending[found]=False
        mx,my=xx+axis[0]*distance*sign,yy+axis[1]*distance*sign
        values.append(cv2.remap(rgb,mx,my,cv2.INTER_CUBIC).astype(float));distances.append(distance)
        found_values.append((target>0)&~pending)
    both=found_values[0]&found_values[1]
    amount=np.zeros_like(xx);amount[both]=distances[0][both]/(distances[0][both]+distances[1][both])
    amount[~found_values[0]&found_values[1]]=1
    replacement=values[0]*(1-amount[:,:,None])+values[1]*amount[:,:,None]
    weight=target.astype(float)/255
    weight[~(found_values[0]|found_values[1])]=0
    clean=np.uint8(np.clip(rgb*(1-weight[:,:,None])+replacement*weight[:,:,None],0,255))
    # A two-pixel taper mixes with the horizontal lower hair in the source.
    # Continue its own clean cross-section, rather than moving that lower band.
    for section in part.get('tail_sections',[]):
        own=np.array(helper.contour_mask(part['outlines'][section['outline_index']]))
        ref_y=section['reference_y'];ref_x=np.flatnonzero(own[ref_y]>64)
        assert len(ref_x)>2
        colours=rgb[ref_y,ref_x].astype(float)
        for row in range(section['start_y'],1080):
            selected=np.flatnonzero(own[row]>6)
            if not len(selected):continue
            span=np.flatnonzero(own[row]>64)
            if not len(span):span=selected
            u=np.clip((selected-span[0])/max(1,span[-1]-span[0]),0,1)
            value=np.column_stack([np.interp(u,np.linspace(0,1,len(ref_x)),colours[:,k]) for k in range(3)])
            amount=min(1,(row-section['start_y'])/max(1,section['full_y']-section['start_y']))
            clean[row,selected]=np.uint8(np.clip(clean[row,selected]*(1-amount)+value*amount,0,255))
    result=Image.fromarray(clean).convert('RGBA');result.putalpha(Image.fromarray(coverage))
    result.save(stage/(part['id']+'-native.png'))
    box=helper.part_mask(part).getbbox();box=(box[0]-15,box[1]-15,box[2]+15,box[3]+15)
    check=Image.alpha_composite(Image.new('RGBA',result.crop(box).size,'#394654'),result.crop(box))
    check.resize((check.width*4,check.height*4)).convert('RGB').save(stage/'native-texture-clean-check.png')
    record['native_texture_cleanup']={'method':'nearest clean native points along the actual free-lock axis, only authored crossing footprints; alpha unchanged',
        'static_crossing_count':len(part.get('static_crossings',[])),
        'edited_native_pixels':int(np.any(clean!=rgb,axis=2)[coverage>0].sum()),
        'missing_same_hair_sources':int(((target>0)&~(found_values[0]|found_values[1])).sum())}
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


def compose_local(stage, generated):
    stage=Path(stage)
    helper.compose(stage,generated,'seam')
    record=read(stage/'stage.json')
    if record['ids']==['CGC14_FACE_CENTRAL_FRINGE']:
        compose_fringe_skin(stage,record)
        return
    before=np.array(Image.open(stage/'before.png').convert('RGB'))
    repaired=np.array(Image.open(stage/'repaired-plate.png').convert('RGB'))
    edit=np.array(Image.open(stage/'composite-mask.png').convert('L'))
    actual=np.zeros(before.shape[:2],dtype=np.uint8)
    for part in record['parts']:
        actual=np.maximum(actual,np.array(helper.part_mask(part)))
    yy,xx=np.mgrid[:1080,:1920]
    # The seam may move through neighbouring hair, but native visible ears,
    # skin and eyes must survive. The selected hair footprint takes precedence.
    ear=helper.contour_mask('M1484,232 C1476,236 1472,242 1473,249 C1475,257 1481,264 1485,266 L1500,232 Z')
    ear=ear.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.1))
    preserve=np.array(ear).astype(float)/255
    preserve[(xx>=1503)&(yy>=180)&(yy<=440)]=1
    preserve[cv2.dilate(np.uint8(actual>6)*255,np.ones((3,3),np.uint8))>0]=0
    repaired=np.uint8(np.clip(before*preserve[:,:,None]+repaired*(1-preserve[:,:,None]),0,255))
    edit[preserve==1]=0
    Image.fromarray(edit).save(stage/'composite-mask.png')
    Image.fromarray(repaired).save(stage/'composited-plate.png')
    Image.fromarray(repaired).save(stage/'repaired-plate.png')
    record.update(state='local-plate-awaiting-puppet-review',blend='hair-seam-with-native-face-restoration',
        outside_composite_mask_max_rgb=int(np.abs(repaired.astype(int)-before.astype(int))[edit==0].max()),
        protected_native_regions={})
    for label,box in {'left_eye_lash':[1503,187,1592,277],'right_eye_lash':[1620,314,1740,420],
                      'nose':[1527,325,1553,344],'mouth':[1498,355,1537,390]}.items():
        x1,y1,x2,y2=box
        record['protected_native_regions'][label]={'box':box,'max_rgb_difference':int(np.abs(
            repaired[y1:y2,x1:x2].astype(int)-before[y1:y2,x1:x2].astype(int)).max())}
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    helper.save_review(stage,record,before,repaired,edit)


def compose_fringe_skin(stage, record):
    before=np.array(Image.open(stage/'before.png').convert('RGB'))
    generated=np.array(Image.open(stage/'generated-aligned.png').convert('RGB'))
    part=record['parts'][0]
    actual=np.array(helper.part_mask(part))
    # Clear the original edge antialias as well; a partly opaque extraction
    # alpha must not leave a second ink line or peach rim on the static plate.
    edit=np.uint8(actual>32)*255
    yy,xx=np.mgrid[:1080,:1920]
    first,last=np.asarray(part['chain'][0]),np.asarray(part['chain'][-1]);axis=(last-first)/np.linalg.norm(last-first)
    downstream=(xx-first[0])*axis[0]+(yy-first[1])*axis[1]
    # The peach wedges are cast shadows on skin, not moving hair volume.
    # Their outer edges were read from the native plate, including both tips.
    shadow=np.zeros_like(actual)
    for path in part['attached_cast_shadows']:
        shadow=np.maximum(shadow,np.array(helper.contour_mask(path)))
    peach=(before[:,:,0].astype(int)-before[:,:,1].astype(int)>40)&(before[:,:,1].astype(int)-before[:,:,2].astype(int)<42)
    shadow_edge=(cv2.dilate(np.uint8(shadow>32)*255,np.ones((7,7),np.uint8))>0)&peach
    edit=np.maximum(edit,np.maximum(np.uint8(shadow>32)*255,np.uint8(shadow_edge)*255))
    edge_remnants=np.zeros_like(edit)
    for x1,y1,x2,y2 in [(1538,281,1556,292),(1559,295,1570,303),(1585,307,1601,315)]:
        native_patch=before[y1:y2,x1:x2].astype(int)
        coloured=(native_patch[:,:,0]<249)|(native_patch[:,:,0]-native_patch[:,:,1]>45)
        edge_remnants[y1:y2,x1:x2]=np.uint8(coloured)*255
    edit=np.maximum(edit,edge_remnants)
    edit=helper.clip_supported_side(edit,part)
    native=before.astype(float)
    samples=(xx>=1525)&(xx<=1740)&(yy>=215)&(yy<=340)
    samples&=cv2.dilate(np.uint8(edit>2)*255,np.ones((7,7),np.uint8))==0
    samples&=(native[:,:,0]>249)&(native[:,:,1]>200)&(native[:,:,2]>170)
    samples&=(native[:,:,1]-native[:,:,2]<38.5)&(native[:,:,0]-native[:,:,1]<55)
    def basis(x,y):
        x=(x.ravel()-1600)/100;y=(y.ravel()-270)/100
        return np.column_stack((np.ones(x.size),x,y,x*x,x*y,y*y))
    design=basis(xx[samples],yy[samples]);values=before[samples].astype(float)
    weights=np.ones(values.shape[0])
    for _ in range(4):
        coefficients=np.linalg.lstsq(design*weights[:,None],values*weights[:,None],rcond=None)[0]
        error=np.linalg.norm(values-design@coefficients,axis=1)
        weights=np.minimum(1,3/np.maximum(error,1e-5))
    y,x=np.nonzero(edit)
    from scipy.interpolate import LinearNDInterpolator
    # Native skin shading bends around the eye. Interpolate the nearby clean
    # skin rather than flattening it to one global complexion plane.
    sample_y,sample_x=np.nonzero(samples)
    selected=np.arange(0,len(sample_x),3)
    native_tone=LinearNDInterpolator(np.column_stack((sample_x[selected],sample_y[selected])),
        before[sample_y[selected],sample_x[selected]].astype(float))(np.column_stack((x,y)))
    missing=~np.isfinite(native_tone).all(axis=1)
    native_tone[missing]=basis(x[missing],y[missing])@coefficients
    # The API supplies the hidden skin; retain its very fine residual while
    # matching the existing native skin light, rather than importing a new tan.
    residual=generated.astype(float)-cv2.GaussianBlur(generated.astype(float),(0,0),6)
    reconstructed=np.uint8(np.clip(native_tone+np.clip(residual[y,x],-2,2)*.25,0,255))
    repaired=before.copy();repaired[y,x]=reconstructed
    alpha=edit.astype(float)/255
    repaired=np.uint8(np.clip(before*(1-alpha[:,:,None])+repaired*alpha[:,:,None],0,255))
    for index,path_outline in enumerate(part['static_crossings']):
        overlay=Image.fromarray(before).convert('RGBA')
        overlay.putalpha(helper.contour_mask(path_outline))
        overlay.save(stage/('static-face-crossing-'+str(index)+'.png'))
    Image.fromarray(edit).save(stage/'composite-mask.png')
    Image.fromarray(repaired).save(stage/'repaired-plate.png')
    Image.fromarray(repaired).save(stage/'composited-plate.png')
    record.update(state='local-plate-awaiting-puppet-review',blend='native-clean-skin-linear-interpolation-generated-fine-residual',
        skin_tone_fit={'native_clean_sample_pixels':int(samples.sum()),'quadratic_rgb_coefficients':coefficients.tolist(),'generated_high_frequency_gain':.25,'attached_peach_shadow_pixels':int((shadow>0).sum()),'shadow_edges':'two authored continuous native cast-shadow silhouettes; no eye-side dilation'},
        outside_composite_mask_max_rgb=int(np.abs(repaired.astype(int)-before.astype(int))[edit==0].max()))
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    helper.save_review(stage,record,before,repaired,edit)


def refine_material(definition, prior):
    part=next(p for p in definition['front_to_back'] if p['id']=='CGC14_FACE_LEFT_SIDE_BAND')
    scaffold=dict(part)
    scaffold['outlines']=part.get('authored_scaffold_before_material_boundary',part['outlines'])
    scaffold.pop('exclude',None)
    authored=helper.part_mask(scaffold)
    x1,y1,x2,y2=authored.getbbox();box=(x1-3,y1-3,x2+3,y2+3);scale=4
    width,height=(box[2]-box[0])*scale,(box[3]-box[1])*scale
    image=np.array(Image.open(Path(prior)/'repaired-plate.png').convert('RGB').crop(box).resize((width,height),Image.Resampling.BICUBIC)).astype(np.int16)
    authored=np.array(authored.crop(box).resize((width,height),Image.Resampling.BICUBIC))
    # Hair gold and all brown shaded volume have G>B here; the pink collar
    # has B>G. This follows the material edge inside the authored silhouette.
    keep=np.uint8((image[:,:,1]>image[:,:,2])&(authored>32))*255
    keep=cv2.morphologyEx(keep,cv2.MORPH_CLOSE,np.ones((2,2),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(keep,8)
    largest=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    keep[labels!=largest]=0
    contours,hierarchy=cv2.findContours(keep,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    outlines=[];holes=[]
    for i,contour in enumerate(contours):
        if cv2.contourArea(contour)<2*scale*scale:continue
        points=cv2.approxPolyDP(contour,.7,True).reshape(-1,2)
        path='M'+' L'.join(f'{x/scale+box[0]:.2f},{y/scale+box[1]:.2f}' for x,y in points)+' Z'
        (outlines if hierarchy[0,i,3]<0 else holes).append(path)
    part['authored_scaffold_before_material_boundary']=scaffold['outlines']
    part['outlines']=outlines;part['outline']=outlines[0];part['exclude']=holes
    part['material_edge_note']='Frozen native gold/brown-versus-pink boundary inside the authored complete cluster; dark brown volume kept; clothing fork gaps transparent.'
    part['ready_for_extract']=True;part['status']='material-silhouette-retraced-on-preceding-repaired-plate'
    DEFINITION.write_text(json.dumps(definition,ensure_ascii=False,indent=2),encoding='utf-8')
    print({'outlines':len(outlines),'holes':len(holes),'pixels':int((keep>0).sum())})


def finish_fringe_texture(stage):
    """Continue crossing surfaces inside their own native hair domain."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import spsolve
    stage=Path(stage);record=read(stage/'stage.json');part=record['parts'][0]
    assert part['id']=='CGC14_FACE_CENTRAL_FRINGE'
    rgb=np.array(Image.open(stage/'before.png').convert('RGB'))
    coverage=np.array(helper.part_mask(part))
    colours=rgb.astype(int)
    peach_edge=(colours[:,:,0]>247)&(colours[:,:,0]-colours[:,:,1]>45)&(colours[:,:,1]-colours[:,:,2]<39)
    yy,xx=np.mgrid[:1080,:1920]
    # This is only the verified skin gap above the middle fork, never a
    # global colour key over the golden hair's similarly coloured edges.
    peach_edge&=(xx>=1582)&(xx<=1604)&(yy>=291)&(yy<=298)
    coverage[peach_edge]=0
    crossing=np.maximum.reduce([np.array(helper.contour_mask(p)) for p in part['static_crossings']])
    crossing=cv2.dilate(crossing,np.ones((5,5),np.uint8));crossing=np.minimum(crossing,coverage)
    generated=Image.open(stage/'generated-moving-hair-crossing.png').resize((384,384),Image.Resampling.LANCZOS)
    aligned=rgb.copy();aligned[140:524,1460:1844]=np.array(generated.convert('RGB'))
    amount=crossing.astype(float)/255
    result=np.uint8(np.clip(rgb*(1-amount[:,:,None])+aligned*amount[:,:,None],0,255))
    # Only the upper cream surface needed further continuation. All solver
    # neighbours are within this same hair, so skin never becomes a white cut.
    blocked=cv2.dilate(np.array(helper.contour_mask(part['static_crossings'][0])),np.ones((7,7),np.uint8))>4
    target=blocked&(coverage>8);domain=coverage>8
    ys,xs=np.nonzero(target);index=np.full(target.shape,-1,int);index[ys,xs]=np.arange(len(xs))
    rows=[];columns=[];values=[];rhs=np.zeros((len(xs),3))
    for n,(y,x) in enumerate(zip(ys,xs)):
        count=0
        for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
            yy,xx=y+dy,x+dx
            if not domain[yy,xx]:continue
            count+=1
            if target[yy,xx]:rows.append(n);columns.append(index[yy,xx]);values.append(-1)
            else:rhs[n]+=rgb[yy,xx]
        rows.append(n);columns.append(n);values.append(count)
    solved=spsolve(csr_matrix((values,(rows,columns)),shape=(len(xs),len(xs))),rhs)
    result[ys,xs]=np.uint8(np.clip(solved,0,255))
    native=Image.fromarray(result).convert('RGBA');native.putalpha(Image.fromarray(coverage))
    native.save(stage/(part['id']+'-native.png'))
    Image.fromarray(coverage).save(stage/(part['id']+'-mask.png'))
    box=(1534,222,1720,319);detail=native.crop(box)
    Image.alpha_composite(Image.new('RGBA',detail.size,'#394654'),detail).resize((1116,582)).convert('RGB').save(stage/'native-texture-clean-check.png')
    record['native_texture_cleanup']={'method':'gpt-image-2 precise crossing repair; upper cream surface continued from native boundaries strictly inside same hair domain; residual native peach cast-shadow edge alpha removed after vector antialias','harmonic_pixels':len(xs),'alpha_expansion_px':0,'generated_crop':[1460,140,1844,524]}
    (stage/'stage.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['review','prepare','clean-texture','compose-local','refine-material','finish-fringe-texture'])
    parser.add_argument('--id')
    parser.add_argument('--prior')
    parser.add_argument('--variant',default='v1')
    parser.add_argument('--stage')
    parser.add_argument('--generated')
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    definition=read(DEFINITION)
    if args.mode=='review':review(definition)
    elif args.mode=='clean-texture':clean_texture(args.stage)
    elif args.mode=='compose-local':compose_local(args.stage,args.generated)
    elif args.mode=='refine-material':refine_material(definition,args.prior)
    elif args.mode=='finish-fringe-texture':finish_fringe_texture(args.stage)
    else:prepare(definition,args.id,args.prior,args.variant)
