extends Node2D

@export var eye_controls:Resource=preload("res://eye_controls.tres")
@export_enum("None", "Wash", "Cocoa Rectangle", "White Rectangle") var border_style:int=3:
	set(value):
		border_style=value
		if is_instance_valid(border_sprite): update_border()
@export_group("Soft White Particles")
@export_range(0,160,1) var particle_count:int=104
@export_range(0.0,2.0,0.05) var particle_opacity:float=0.65
@export_range(0.0,3.0,0.05) var particle_fall_speed:float=1.0
@export_range(0.0,3.0,0.05) var particle_drift:float=1.0

const DURATION:=6.3
const PAD:=Vector2(128,192)
const CloseupMotion=preload("res://closeup_motion.gd")
var clock:=0.0
var frame:=0
var rendering:=false
var fps:=60.0
var frame_limit:=378
var fixed_time:=-1.0
var paused:=false
var close_world:Node2D
var wide_world:Node2D
var eye_material:=ShaderMaterial.new()
var lid_puppet:Node2D
var horizontal:=ShaderMaterial.new()
var vertical:=ShaderMaterial.new()
var border_sprite:Sprite2D
var particle_layers:Array[Node2D]=[]

func add_particles(world:Node2D,is_closeup:bool=false) -> void:
	var layer:Node2D=load("res://atmosphere.gd").new()
	layer.name="SceneSpaceSoftParticles"
	layer.particle_count=particle_count
	layer.closeup_fill=is_closeup
	world.add_child(layer)
	particle_layers.append(layer)

func update_border() -> void:
	border_sprite.visible=border_style>0
	if border_style>0:
		border_sprite.texture=load("res://assets/frames/%s.png" % ["wash","cocoa-rectangle","white-rectangle"][border_style-1])

func viewport() -> SubViewport:
	var v:=SubViewport.new()
	v.size=Vector2i(1920,1080)
	v.disable_3d=true
	v.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	v.canvas_item_default_texture_filter=Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_LINEAR
	add_child(v)
	return v

func plate(parent:Node,path:String) -> Sprite2D:
	var s:=Sprite2D.new()
	s.centered=false
	s.texture=load(path)
	parent.add_child(s)
	return s

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg=="--render": rendering=true
		elif arg.begins_with("--time="): fixed_time=float(arg.trim_prefix("--time="))
		elif arg.begins_with("--frames="): frame_limit=int(arg.trim_prefix("--frames="))
		elif arg.begins_with("--fps="): fps=float(arg.trim_prefix("--fps="))
		elif arg=="--border=wash": border_style=1
		elif arg=="--border=cocoa-rectangle": border_style=2
		elif arg=="--border=white-rectangle": border_style=3
	var close_view:=viewport()
	close_world=Node2D.new();close_view.add_child(close_world)
	plate(close_world,"res://assets/e-overscan.png").position=-PAD
	add_particles(close_world,true)
	var wide_view:=viewport()
	wide_world=Node2D.new();wide_view.add_child(wide_world)
	plate(wide_world,"res://assets/a-overscan.png").position=-PAD
	var face:=plate(wide_world,"res://assets/a-plate.png")
	eye_material.shader=load("res://eyes.gdshader")
	face.material=eye_material
	for part in ["face_base","eye_body","eye_iris","eye_skin","eye_region","eye_foreground","native_opening"]:
		eye_material.set_shader_parameter(part,load("res://assets/eyes/%s.png" % part.replace("_","-")))
	var rig:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://rig.json"))
	var bases:=PackedVector4Array();var centers:=PackedVector2Array()
	for eye in rig.eyes:
		bases.append(Vector4(eye.basis[0],eye.basis[1],eye.basis[2],eye.basis[3]))
		centers.append(Vector2(eye.iris_center[0],eye.iris_center[1]))
	eye_material.set_shader_parameter("eye_basis",bases)
	eye_material.set_shader_parameter("iris_centers",centers)
	eye_material.set_shader_parameter("eye_count",2)
	lid_puppet=load("res://lid_puppet.gd").new()
	lid_puppet.name="NativeLidMeshes"
	wide_world.add_child(lid_puppet)
	lid_puppet.configure(eye_material)
	add_particles(wide_world)
	var blur_view:=viewport()
	var mix_rect:=ColorRect.new();mix_rect.size=Vector2(1920,1080);blur_view.add_child(mix_rect)
	horizontal.shader=load("res://mix-horizontal.gdshader");mix_rect.material=horizontal
	horizontal.set_shader_parameter("closeup",close_view.get_texture())
	horizontal.set_shader_parameter("overview",wide_view.get_texture())
	var final_rect:=ColorRect.new();final_rect.size=Vector2(1920,1080);add_child(final_rect)
	vertical.shader=load("res://vertical.gdshader");final_rect.material=vertical
	vertical.set_shader_parameter("image",blur_view.get_texture())
	border_sprite=Sprite2D.new()
	border_sprite.name="EagleMaterialBorder"
	border_sprite.centered=false
	add_child(border_sprite)
	update_border()
	pose()
	print("CGC06_SCENE3_READY 66.000–72.300 seconds")

func transform_view(world:Node2D,source:Vector2,screen:Vector2,zoom:float,angle:float) -> void:
	world.scale=Vector2.ONE*zoom
	world.rotation=angle
	world.position=screen-(source*zoom).rotated(angle)

func set_eye_blink(amount:Vector2) -> void:
	lid_puppet.deform(amount,eye_controls)

func opening_progress(t:float) -> float:
	# Close in 0.15s, reopen to 70% in 0.15s: the whole fast blink is 0.30s.
	# The last 30% takes 1.70s, with matched nonzero join velocity.
	if t<=4.45: return 0.0
	if t<4.60:
		var u:=clampf((t-4.45)/0.15,0.0,1.0)
		var join_velocity:=0.60/1.70
		return 0.70*u*u*(3.0-2.0*u)+0.15*join_velocity*u*u*(u-1.0)
	var u:=clampf((t-4.60)/1.70,0.0,1.0)
	return 0.70+0.30*(2.0*u-u*u)

func blink_at(t:float) -> float:
	return smoothstep(4.30,4.45,t)*(1.0-opening_progress(t))

func rotation_at(t:float) -> float:
	# Ease into an ordinary slow turn during the dissolve, then keep that
	# speed through the quick blink. Only decelerate during the slow reopen.
	var elapsed:=maxf(0.0,t-2.55)
	var distance:float
	if elapsed<0.55:
		var u:=elapsed/0.55
		distance=0.55*(u*u*u-0.5*u*u*u*u)
	elif t<4.60:
		distance=elapsed-0.275
	else:
		var u:=clampf((t-4.60)/1.70,0.0,1.0)
		distance=1.775+1.70*(u-u*u*u+0.5*u*u*u*u)
	return distance/2.625

func pose() -> void:
	var t:=fixed_time if fixed_time>=0.0 else clock
	for layer in particle_layers:
		layer.particle_opacity=particle_opacity
		layer.fall_speed=particle_fall_speed
		layer.drift_amount=particle_drift
		layer.update_at(t,1.0,false)
	transform_view(close_world,CloseupMotion.center(t),Vector2(960,540),CloseupMotion.zoom(t),0.0)
	var rotation_progress:=rotation_at(t)
	transform_view(wide_world,Vector2(900,270),Vector2(1400,420),1.65,deg_to_rad(-10)*rotation_progress)
	if eye_controls.inspect_face and not rendering:
		transform_view(wide_world,Vector2(890,265),Vector2(960,540),2.5,0.0)
	var blink:=blink_at(t)
	set_eye_blink(Vector2.ZERO if eye_controls.manual else Vector2(blink,blink))
	eye_material.set_shader_parameter("iris_offsets",Vector4(eye_controls.iris_left_offset.x,eye_controls.iris_left_offset.y,eye_controls.iris_right_offset.x,eye_controls.iris_right_offset.y))
	eye_material.set_shader_parameter("iris_scale",eye_controls.iris_scale)
	eye_material.set_shader_parameter("parts_visible",Vector4(float(eye_controls.eyebrows_visible),float(eye_controls.iris_visible),float(eye_controls.eye_body_visible),float(eye_controls.lower_lids_visible)))
	var blend:=1.0 if eye_controls.inspect_face and not rendering else smoothstep(2.55,3.10,t)
	var transition:=sin(PI*clampf((t-2.55)/.55,0.0,1.0))
	var blur:=22.0*pow(maxf(transition,0),1.25)
	horizontal.set_shader_parameter("blend_amount",blend)
	horizontal.set_shader_parameter("blur_px",blur)
	vertical.set_shader_parameter("blur_px",blur)

func _process(delta:float) -> void:
	if rendering:
		if frame>=frame_limit:
			get_tree().quit()
			return
		clock=float(frame)/fps
		frame+=1
	elif not paused:
		clock=minf(clock+delta,DURATION)
	pose()

func _unhandled_key_input(event:InputEvent) -> void:
	if event.is_action_pressed("ui_accept"): paused=not paused
	elif event.is_action_pressed("ui_home"): clock=0.0;paused=false
