extends Control

# Geometric suusiki glyph masks; 恋 keeps native 亦 over four clear 心 strokes.
# Detached extensions echo the long geometric horizontals without hiding type.
const TEAL:=Color("00a1b8")
const YELLOW:=Color("fff14b")
const INK:=Color("ffffff")
const DESIGN_SIZE:=Vector2(1920,1080)
const COLOURS:Array[Color]=[Color("ed4387"),Color("647581"),Color("749dcc"),Color("ae9cc1"),Color("f5bf35"),Color("69aab8"),Color("e44e94"),Color("91a9c7")]
class TitleArt extends Control:
    var host:Control
    func _draw() -> void:
        host.draw_front(self)
var settings:Dictionary={}
var state:Dictionary={}
var song_time:=0.0
var start_time:=105.4
var feng_texture:Texture2D
var feng_opacity:=0.0
var subtitle_font:Font
var glyph_textures:Array[Texture2D]=[]
var glyph_info:Array=[]
var font_details:Dictionary={}
var glyph_origins:Array[Vector2]=[]
var glyph_scales:Array[Vector2]=[]
var cast_stage:Control
var cast_nodes:Array[TextureRect]=[]
var cast_materials:Array[ShaderMaterial]=[]
var art:TitleArt
var title_scale:=1.0
var title_phase:="feng"
var cast_hit:=106.266666
var silhouette_hit:=106.483333
var settle_hit:=106.683333
var cast_info:Array=[]

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    z_index=50
    settings=JSON.parse_string(FileAccess.get_file_as_string("res://ending.json"))
    start_time=float(settings.get("title_start",105.4))
    feng_texture=load("res://assets/ending-title/feng-logo.png")
    var font:=SystemFont.new()
    font.font_names=PackedStringArray(["Yu Gothic","Microsoft YaHei UI"])
    subtitle_font=font
    build_title()
    build_cast()
    art=TitleArt.new()
    art.host=self
    art.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
    art.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    art.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(art)
    visible=false

func build_cast() -> void:
    cast_info=JSON.parse_string(FileAccess.get_file_as_string("res://assets/ending-title/cast.json"))
    cast_stage=Control.new()
    cast_stage.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(cast_stage)
    for row in cast_info:
        var portrait:=TextureRect.new()
        portrait.texture=load(row.texture)
        portrait.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
        portrait.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
        portrait.mouse_filter=Control.MOUSE_FILTER_IGNORE
        var material:=ShaderMaterial.new()
        material.shader=load("res://ending-title.gdshader")
        material.set_shader_parameter("silhouette_colour",TEAL)
        portrait.material=material
        cast_stage.add_child(portrait)
        cast_nodes.append(portrait)
        cast_materials.append(material)

func smooth_curve(p:float) -> float:
    p=clampf(p,0.0,1.0)
    return p*p*p*(p*(6.0*p-15.0)+10.0)

func build_title() -> void:
    font_details=JSON.parse_string(FileAccess.get_file_as_string("res://assets/ending-title/title-glyphs.json"))
    glyph_info=font_details.glyphs
    for row in glyph_info:
        var image:Image=load(row.texture).get_image()
        image.generate_mipmaps()
        glyph_textures.append(ImageTexture.create_from_image(image))
    # Flatten the three large kanji while retaining the native kana proportions.
    # Optical gaps leave room for the detached geometric horizontals.
    var gaps:Array[float]=[42.0,24.0,22.0,22.0,46.0,52.0,42.0]
    var total_width:=0.0
    for i in glyph_textures.size():
        var large:=i==0 or i==5 or i==6
        var height:=240.0 if large else (150.0 if i==7 else 145.0)
        var source:=glyph_textures[i].get_size()
        var width:=source.x/source.y*height*(1.85 if large else 1.0)
        glyph_scales.append(Vector2(width,height)/100.0)
        total_width+=width+(gaps[i] if i<gaps.size() else 0.0)
    var x:=(DESIGN_SIZE.x-total_width)*.5
    for i in glyph_scales.size():
        var size:=glyph_scales[i]*100.0
        glyph_origins.append(Vector2(x,650.0-size.y))
        x+=size.x+(gaps[i] if i<gaps.size() else 0.0)
func pose(song:float) -> void:
    song_time=song
    visible=song>=start_time
    if not visible:
        state={"song":song,"visible":false,"title":"夜もすがら君恋ふ","phase":"hidden","title_scale":0.0}
        return
    cast_hit=float(settings.get("title_cast_hit",106.266666))
    silhouette_hit=float(settings.get("title_silhouette_hit",106.483333))
    settle_hit=float(settings.get("title_settle_hit",106.683333))
    title_phase="feng" if song<cast_hit else ("cast" if song<silhouette_hit else ("silhouette" if song<settle_hit else "settle"))
    feng_opacity=smooth_curve((song-start_time)/float(settings.feng_fade_seconds))
    # Each title shot has a fixed layout; the beat changes it with a hard cut.
    title_scale=1.0 if song<settle_hit else .50
    cast_stage.visible=song>=cast_hit and song<settle_hit
    var screen:=get_viewport_rect().size/DESIGN_SIZE
    cast_stage.scale=screen
    for i in cast_nodes.size():
        var height:=720.0 if i!=1 else 680.0
        var width:=height*float(cast_info[i].width)/float(cast_info[i].height)
        var centre:=Vector2(360.0+float(i)*300.0,550.0)
        cast_nodes[i].position=centre-Vector2(width,height)*.5
        cast_nodes[i].size=Vector2(width,height)
        cast_materials[i].set_shader_parameter("silhouette",1.0 if song>=silhouette_hit else 0.0)
    state={"song":song,"visible":visible,"title":"夜もすがら君恋ふ","phase":title_phase,"feng_opacity":feng_opacity,"title_scale":title_scale,"cast_hit":cast_hit,"silhouette_hit":silhouette_hit,"settle_hit":settle_hit,"font_family":font_details.font_family,"font_source":font_details.font_source}
    queue_redraw()
    art.queue_redraw()

func _draw() -> void:
    if not visible:return
    var screen:=get_viewport_rect().size/DESIGN_SIZE
    draw_set_transform(Vector2.ZERO,0.0,screen)
    if title_phase=="feng":
        # Fade the native white-backed logo over the still-running information
        # page. Its original framing and proportions remain unchanged.
        draw_texture_rect(feng_texture,Rect2(Vector2.ZERO,DESIGN_SIZE),false,Color(1,1,1,feng_opacity))
        draw_set_transform(Vector2.ZERO,0.0,Vector2.ONE)
        return
    draw_rect(Rect2(Vector2.ZERO,DESIGN_SIZE),TEAL if title_phase=="cast" else INK)
    # The original OP's white/cyan polarity cuts survive; the wire mesh,
    # monoline construction and yellow diamonds come from the MAD reference.
    if title_phase=="cast":
        # Keep the approved mesh pose when the separate feng lead-in moves.
        draw_backdrop(self,song_time-cast_hit+.466666,1.0)
    draw_set_transform(Vector2.ZERO,0.0,Vector2.ONE)

func draw_front(target:CanvasItem) -> void:
    if not visible or title_phase=="feng":return
    var screen:=get_viewport_rect().size/DESIGN_SIZE
    var centre:=Vector2(960,540)
    var scale_value:=title_scale
    var shift:=Vector2.ZERO
    if title_phase=="settle":
        shift.y=-14.0
    target.draw_set_transform((centre*(1.0-scale_value)+shift)*screen,0.0,screen*scale_value)
    var reveal:=1.0
    var white_letters:=title_phase=="cast"
    for i in 8:
        var colour:=INK if white_letters else COLOURS[i]
        if title_phase=="cast":
            draw_logo_glyph(target,i,glyph_origins[i],glyph_scales[i],1.0,11.0,Color(TEAL,.88))
        elif title_phase=="silhouette":
            draw_logo_glyph(target,i,glyph_origins[i],glyph_scales[i],1.0,11.0,Color(1,1,1,.92))
        draw_logo_glyph(target,i,glyph_origins[i],glyph_scales[i],reveal,7.0,colour)
    draw_accents(target,1.0)
    draw_subtitle(target,1.0,white_letters)
    target.draw_set_transform(Vector2.ZERO,0.0,Vector2.ONE)

func draw_backdrop(target:CanvasItem,local:float,opacity:float) -> void:
    var drift:=Vector2(-local*2.0,local*.7)
    var points:Array[Vector2]=[Vector2(-150,50),Vector2(320,-90),Vector2(610,200),Vector2(1030,-80),Vector2(1460,190),Vector2(1980,0),Vector2(2100,650),Vector2(1660,1050),Vector2(1230,800),Vector2(920,1170),Vector2(440,860),Vector2(-180,1020)]
    var pairs:Array=[[0,2],[1,2],[2,3],[2,8],[2,10],[3,4],[4,5],[4,8],[4,6],[6,7],[7,8],[8,9],[8,10],[10,11],[0,11]]
    for pair in pairs:
        target.draw_line(points[pair[0]]+drift,points[pair[1]]+drift,Color(.35,.86,.90,.095*opacity),2.0,true)
    for i in 20:
        var x:=fmod(float(i*311+73)+local*(8.0+float(i%5)*2.0),2080.0)-80.0
        var y:=fmod(float(i*173+40)+local*(13.0+float(i%4)*3.0),1200.0)-60.0
        var pos:=Vector2(x,y)
        var triangle:=PackedVector2Array([pos+Vector2(-4,-7),pos+Vector2(7,0),pos+Vector2(-2,8)])
        target.draw_colored_polygon(triangle,Color(1,1,1,(.15+float(i%3)*.12)*opacity))

func draw_accents(target:CanvasItem,p:float) -> void:
    for i in [0,5,6]:
        var size:=glyph_scales[i]*100.0
        var local:=Vector2(.58,.61) if i==0 else (Vector2(.43,.76) if i==5 else Vector2(.52,.85))
        draw_diamond(target,glyph_origins[i]+size*local,23.0*p,YELLOW,0.0)
    for centre in [glyph_origins[3]+Vector2(20,-40),glyph_origins[7]+Vector2(50,-75),glyph_origins[1]+Vector2(-28,185)]:
        for offset in [Vector2(-10,0),Vector2(10,0),Vector2(0,-10),Vector2(0,10)]:
            draw_diamond(target,centre+offset*1.25,6.0*p,YELLOW,0.0)

func draw_subtitle(target:CanvasItem,p:float,white_letters:bool) -> void:
    if p<=.001:return
    var text:="夢と色でできている"
    var width:=subtitle_font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,25).x
    var left:=960.0-width*.5
    var colour:=INK if white_letters else Color("6d8b96")
    target.draw_string(subtitle_font,Vector2(left,800),text,HORIZONTAL_ALIGNMENT_LEFT,-1,25,colour)
    target.draw_line(Vector2(720,839),Vector2(1200,839),colour*.65,1.5,true)

func draw_logo_glyph(target:CanvasItem,index:int,origin:Vector2,glyph_scale:Vector2,reveal:float,width:float,colour:Color) -> void:
    if reveal<=0.0:return
    var texture:Texture2D=glyph_textures[index]
    var source_size:=texture.get_size()
    var ink_size:=glyph_scale*100.0
    var ink_origin:=origin
    var source:=Rect2(Vector2.ZERO,Vector2(source_size.x*reveal,source_size.y))
    var destination:=Rect2(ink_origin,Vector2(ink_size.x*reveal,ink_size.y))
    # A narrow, clean halo protects type on the two brief cast states. It is
    # drawn from the same exact mask, with no second copy of the font's strokes.
    if width>7.1:
        var spread:=(width-7.0)*.5
        for i in 12:
            var offset:=Vector2.from_angle(TAU*float(i)/12.0)*spread
            target.draw_texture_rect_region(texture,Rect2(destination.position+offset,destination.size),source,colour)
    target.draw_texture_rect_region(texture,destination,source,colour)
    if glyph_info[index].horizontal_guide!=null:
        var guide:Array=glyph_info[index].horizontal_guide
        var left:=ink_origin+Vector2(float(guide[0]),float(guide[1]))*ink_size
        var right:=ink_origin+Vector2(float(guide[2]),float(guide[3]))*ink_size
        var line_width:=3.4+maxf(width-7.0,0.0)
        # The 10px gaps preserve every font contour while the extensions echo
        # the title reference's long horizontals and small broken-line details.
        draw_trace(target,PackedVector2Array([left-Vector2(38,0),left-Vector2(10,0)]),reveal,colour,line_width)
        draw_trace(target,PackedVector2Array([right+Vector2(10,0),right+Vector2(40,0)]),reveal,colour,line_width)
        draw_trace(target,PackedVector2Array([left-Vector2(28,-9),left-Vector2(10,-9)]),reveal,Color(colour,.65*colour.a),1.5+maxf(width-7.0,0.0))
func draw_trace(target:CanvasItem,points:PackedVector2Array,progress:float,colour:Color,width:float) -> void:
    if progress<=0.0 or points.size()<2:return
    var total:=0.0
    for i in range(1,points.size()):total+=points[i-1].distance_to(points[i])
    var remaining:=total*clampf(progress,0.0,1.0)
    var shown:=PackedVector2Array([points[0]])
    for i in range(1,points.size()):
        var segment:=points[i-1].distance_to(points[i])
        if remaining>=segment:
            shown.append(points[i])
            remaining-=segment
        else:
            shown.append(points[i-1].lerp(points[i],remaining/maxf(segment,.001)))
            break
    if shown.size()>1:
        target.draw_polyline(shown,colour,width,true)
        for point in shown:target.draw_circle(point,width*.5,colour,true,-1.0,true)

func draw_diamond(target:CanvasItem,centre:Vector2,radius:float,colour:Color,angle:float) -> void:
    if radius<=0.01:return
    var points:=PackedVector2Array()
    for i in 4:points.append(centre+Vector2.from_angle(angle+PI*.5*float(i))*radius)
    target.draw_colored_polygon(points,colour)
