extends Node2D

# Native CG coordinates: both cameras see the same drifting field at their zoom.
# A zero-particle instance is used only for the previous shot's screen-fixed frame.
@export_range(0,160,1) var particle_count:int=104
@export_range(0.0,2.0,0.05) var particle_opacity:float=0.65
@export_range(0.0,3.0,0.05) var fall_speed:float=1.0
@export_range(0.0,3.0,0.05) var drift_amount:float=1.0
@export var closeup_fill:bool=false
const CLOSEUP_POINTS:=[Vector2(300,680),Vector2(425,555),Vector2(615,475),Vector2(800,350),Vector2(940,505)]
var bodies:Array[Sprite2D]=[]
var halos:Array[Sprite2D]=[]
var seeds:Array[Vector4]=[]
var border:Sprite2D
var character_mask:Image

func _ready() -> void:
	var random:=RandomNumberGenerator.new()
	random.seed=60617
	var additive:=CanvasItemMaterial.new()
	additive.blend_mode=CanvasItemMaterial.BLEND_MODE_ADD
	if particle_count>0:
		character_mask=load("res://assets/particles/character-exclusion.png").get_image()
	for i in range(particle_count+(CLOSEUP_POINTS.size() if closeup_fill and particle_count>0 else 0)):
		var data:=Vector4(random.randf_range(-128,1504),random.randf_range(-192,944),random.randf_range(10,18),random.randf_range(0,TAU))
		if i>=particle_count:
			var point:Vector2=CLOSEUP_POINTS[i-particle_count]
			data=Vector4(point.x,point.y,5.0,0.7*float(i-particle_count))
		seeds.append(data)
		# Keep one random size draw per particle, preserving the original field's
		# positions/phases while distributing sizes into visibly different bands.
		var size_sample:=random.randf()
		var diameter:float
		if i>=particle_count: diameter=lerpf(7.0,11.0,size_sample)
		elif size_sample<0.30: diameter=lerpf(4.5,7.0,size_sample/0.30)
		elif size_sample<0.80: diameter=lerpf(8.0,12.0,(size_sample-0.30)/0.50)
		else: diameter=lerpf(15.0,20.0,(size_sample-0.80)/0.20)
		diameter*=1.0 if closeup_fill else 1.3
		var halo:=Sprite2D.new()
		halo.texture=load("res://assets/particles/snow-glow.png")
		halo.scale=Vector2.ONE*diameter/32.0*1.8
		halo.material=additive
		add_child(halo);halos.append(halo)
		var body:=Sprite2D.new()
		body.texture=load("res://assets/particles/snow-soft.png")
		body.scale=Vector2.ONE*diameter/32.0
		add_child(body);bodies.append(body)
	if particle_count==0:
		border=Sprite2D.new()
		border.name="SelectedWhiteRectangle"
		border.centered=false
		border.texture=load("res://assets/frames/white-rectangle.png")
		add_child(border)
	update_at(0.0)

func update_at(t:float,entry:float=1.0,show_border:bool=true) -> void:
	modulate.a=entry
	for i in range(bodies.size()):
		var data:=seeds[i]
		var x:=fposmod(data.x+128+drift_amount*(9.0*sin(t*0.38+data.w)+3.5*sin(t*0.71+data.w*1.7)),1632)-128
		var y:=fposmod(data.y+192+t*data.z*fall_speed+1.2*sin(t*0.42+data.w),1136)-192
		var location:=Vector2(x,y)
		bodies[i].position=location;halos[i].position=location
		# The sparse closeup foreground also passes over hands/clothing naturally.
		# Keep the shared background field's character attenuation unchanged.
		var coverage:=0.0
		if x>=0 and y>=0 and x<character_mask.get_width() and y<character_mask.get_height():
			coverage=character_mask.get_pixel(int(x),int(y)).r
		var character_gain:=0.8 if i>=particle_count else 1.0-0.98*coverage
		# Thin only the closeup background field; keep its sparse foreground.
		var camera_gain:=1.0 if closeup_fill else 1.35
		if closeup_fill and i<particle_count and i%3!=0: camera_gain=0.0
		bodies[i].modulate.a=particle_opacity*character_gain*camera_gain*(0.72+0.18*sin(data.w))
		halos[i].modulate.a=particle_opacity*character_gain*camera_gain*0.22
	if is_instance_valid(border): border.visible=show_border
