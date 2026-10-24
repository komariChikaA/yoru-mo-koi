extends Node3D

# Entry and hand-camera anticipation overlap; formal hand/full sections are 5s.
# Absolute timing is shared with the preparer and renderer in timeline.json.
const NATIVE_PETAL_SPEED := 1.6
const HairRig := preload("res://hair-rig.gd")
const HandRig := preload("res://hand-rig.gd")
const HeroineEnding := preload("res://heroine-ending.gd")
const EndingTitle := preload("res://ending-title.gd")
var timeline: Dictionary
var duration := 11.9
var clock := 0.0
var fixed_time := -1.0
var capture_start := 0.0
var capture := false
var frame := 0
var frame_count := 714
var fps := 60.0
var lighting := 1.0
var petal_strength := 1.0
var hair_strength := 1.0
var hair_visible := true
var hair_metrics := ""
var hair_manifest: Dictionary
var hair: Node3D
var plate_materials: Array[ShaderMaterial] = []
var petal_materials: Array[ShaderMaterial] = []
var petals: Array[Dictionary] = []
var native_petals: Array[Dictionary] = []
var sunlight: ShaderMaterial
var key: DirectionalLight3D
var camera: Camera3D
var hand: MeshInstance3D
var finish: ShaderMaterial
var entry_previous: MeshInstance3D
var entry_material: ShaderMaterial
var entry_previous_frames: Array[Dictionary] = []
var entry_petals: Array[Dictionary] = []
var entry_view: SubViewport
var entry_camera: Camera3D
var entry_overlay: TextureRect
var focus: CameraAttributesPractical
var hand_strength := 1.0
var face_overlay
var title_overlay
var finish_overlay:ColorRect
var ending_only:=false
var ending_visibility:Array[Dictionary]=[]

func _ready() -> void:
	timeline=JSON.parse_string(FileAccess.get_file_as_string("res://timeline.json"))
	duration=float(timeline.song_end)-float(timeline.song_start)
	for arg in OS.get_cmdline_user_args():
		if arg == "--render": capture = true
		elif arg.begins_with("--time="): fixed_time = float(arg.get_slice("=",1))
		elif arg.begins_with("--start-time="): capture_start = float(arg.get_slice("=",1))
		elif arg.begins_with("--frames="): frame_count = int(arg.get_slice("=",1))
		elif arg.begins_with("--fps="): fps = float(arg.get_slice("=",1))
		elif arg.begins_with("--lighting="): lighting = float(arg.get_slice("=",1))
		elif arg.begins_with("--petals="): petal_strength = float(arg.get_slice("=",1))
		elif arg.begins_with("--hair="): hair_strength = float(arg.get_slice("=",1))
		elif arg.begins_with("--hair-visible="): hair_visible = int(arg.get_slice("=",1)) != 0
		elif arg.begins_with("--hair-metrics="): hair_metrics = arg.trim_prefix("--hair-metrics=")
		elif arg.begins_with("--hand="): hand_strength = float(arg.get_slice("=",1))
	hair_manifest = JSON.parse_string(FileAccess.get_file_as_string("res://assets/hair/manifest.json"))
	build_lighting()
	build_plates()
	hair = HairRig.new()
	hair.name = "NativeHairPuppet"
	add_child(hair)
	hair.build(hair_manifest,lighting)
	hand=HandRig.new()
	hand.name="NativePalmPuppet"
	add_child(hand)
	hand.build(lighting)
	build_petals()
	build_native_petals()
	build_camera()
	build_entry()
	build_finish()
	build_face_frame()
	pose(maxf(fixed_time,0.0))
	print("SCENE5 stage=early-overlap duration=",duration," song_start=",timeline.song_start," petals=",petals.size()," native_petals=",native_petals.size()," curtain_petals=",entry_petals.size()," camera_start=",timeline.camera_start," full_start=",timeline.full_start)
	if not hair_metrics.is_empty():
		var metrics_file := FileAccess.open(hair_metrics,FileAccess.WRITE)
		metrics_file.store_string(JSON.stringify(hair.review_motion(),"\t"))
		metrics_file.close()
		get_tree().quit()

func build_camera() -> void:
	camera = Camera3D.new()
	camera.name = "SceneReviewCamera"
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 9.0
	# Original-image centre (800,520), width 1600px. Trim the supporting figure.
	camera.position = Vector3(-1.60,0.20,10.0)
	camera.current = true
	focus = CameraAttributesPractical.new()
	focus.dof_blur_near_enabled = true
	focus.dof_blur_near_distance = 8.5
	focus.dof_blur_near_transition = 1.6
	focus.dof_blur_far_enabled = true
	focus.dof_blur_far_distance = 10.45
	focus.dof_blur_far_transition = 2.0
	focus.dof_blur_amount = 0.045
	camera.attributes = focus
	add_child(camera)

func build_finish() -> void:
	var layer:=CanvasLayer.new()
	layer.layer=10
	add_child(layer)
	var overlay:=ColorRect.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.mouse_filter=Control.MOUSE_FILTER_IGNORE
	finish=ShaderMaterial.new()
	finish.shader=load("res://warm-finish.gdshader")
	overlay.material=finish
	finish_overlay=overlay
	layer.add_child(overlay)

func build_entry() -> void:
	# Finish the CG first, then composite the already-finished previous shot
	# and foreground petal shower. Their alpha gaps reveal the lit CG directly.
	entry_view=SubViewport.new()
	entry_view.name="PreviousShotAndPetalShower"
	entry_view.size=Vector2i(get_viewport().get_visible_rect().size)
	entry_view.world_3d=World3D.new()
	entry_view.transparent_bg=true
	entry_view.msaa_3d=get_viewport().msaa_3d
	entry_view.scaling_3d_scale=get_viewport().scaling_3d_scale
	entry_view.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	add_child(entry_view)
	entry_view.world_3d.environment=get_world_3d().environment.duplicate()
	entry_view.world_3d.environment.background_mode=Environment.BG_CLEAR_COLOR
	for node in get_children():
		if node is DirectionalLight3D:entry_view.add_child(node.duplicate())
	entry_camera=Camera3D.new()
	entry_camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	entry_camera.current=true
	entry_view.add_child(entry_camera)
	var entry_layer:=CanvasLayer.new()
	entry_layer.layer=11
	add_child(entry_layer)
	entry_overlay=TextureRect.new()
	entry_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	entry_overlay.mouse_filter=Control.MOUSE_FILTER_IGNORE
	entry_overlay.texture=entry_view.get_texture()
	var composite:=ShaderMaterial.new()
	composite.shader=load("res://entry-composite.gdshader")
	entry_overlay.material=composite
	entry_layer.add_child(entry_overlay)
	entry_previous=MeshInstance3D.new()
	var plane:=QuadMesh.new()
	plane.size=Vector2(16,9)
	entry_previous.mesh=plane
	entry_material=ShaderMaterial.new()
	entry_material.shader=load("res://entry-previous.gdshader")
	var previous: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/entry-previous/manifest.json"))
	for item in previous.frames:
		entry_previous_frames.append({"song_start":float(item.song_start),"image":load(item.texture)})
	entry_material.set_shader_parameter("source_image",entry_previous_frames[0].image)
	entry_previous.material_override=entry_material
	entry_previous.position=Vector3(0,0,-2.5)
	entry_camera.add_child(entry_previous)
	var rng:=RandomNumberGenerator.new()
	rng.seed=795008100
	var mesh:=petal_mesh()
	# A short shower, sampled per petal. No tiled sheet, common vertical
	# translation, forward approach or scale-up. They keep falling after entry.
	for layer in 3:
		for i in [1800,1400,240][layer]:
			var node:=MeshInstance3D.new()
			node.mesh=mesh
			node.material_override=petal_materials[rng.randi_range(0,3)]
			entry_camera.add_child(node)
			var size_ranges: Array=[Vector2(.035,.065),Vector2(.06,.095),Vector2(.10,.145)]
			var limits: Vector2=size_ranges[layer]
			var crossing_x:=rng.randf_range(-1.22,1.22)
			var initial_y:=rng.randf_range(.59,1.55)
			var size:=rng.randf_range(limits.x,limits.y)
			var speed:=rng.randf_range(1.02,1.58)
			var drift:=rng.randf_range(-1.35,-.90)
			# Distribute the centre crossings, so the stronger diagonal wind
			# does not empty the right side before the transition is covered.
			var initial_x:=crossing_x-drift*entry_wind_distance(initial_y/speed)
			entry_petals.append({"node":node,"x":initial_x,
				"y":initial_y,"size":size,"speed":speed,"drift":drift,
				"flutter":rng.randf_range(1.8,3.4),"spin":rng.randf_range(-1.35,1.35),
				"depth":rng.randf_range(-1.95,-1.25),"phase":rng.randf()*TAU})

func entry_wind_distance(t: float) -> float:
	# Analytic gust integral: petals share a breeze, with individual drag.
	return t+.075*(sin(t*3.8-.4)-sin(-.4))

func build_face_frame() -> void:
	var layer:=CanvasLayer.new()
	layer.layer=20
	add_child(layer)
	face_overlay=HeroineEnding.new()
	layer.add_child(face_overlay)
	title_overlay=EndingTitle.new()
	layer.add_child(title_overlay)

func pose_camera(t: float) -> void:
	var song: float=t+float(timeline.song_start)
	var camera_song:=minf(song,float(timeline.cg_end))
	if song<float(timeline.full_start):
		var p:=clampf((song-float(timeline.camera_start))/(float(timeline.full_start)-float(timeline.camera_start)),0.0,1.0)
		# Shorter travel slows the pan throughout, including under the petal entry.
		p=lerpf(p,smoothstep(0.0,1.0,p),.3)
		camera.position=Vector3((615.0-960)*.01,(540.0-lerpf(535.0,625.0,p))*.01,10.0)
		camera.size=lerpf(4.17,4.29,p)
	else:
		var full_p:=clampf((camera_song-float(timeline.full_start))/(float(timeline.cg_end)-float(timeline.full_start)),0.0,1.0)
		full_p=lerpf(full_p,smoothstep(0.0,1.0,full_p),.2)
		# A tighter, left-biased portrait drifts right, keeping the boy cropped.
		camera.position=Vector3((lerpf(660.0,750.0,full_p)-960.0)*.01,1.10,10.0)
		camera.size=7.2
		var ending:=clampf(camera_song-(float(timeline.cg_end)-1.0),0.0,1.0)
		# A zero-acceleration ease starts the last-second pullback naturally.
		var pullback:=ending*ending*ending*(ending*(ending*6.0-15.0)+10.0)
		camera.size+=pullback
	focus.dof_blur_near_enabled=song>=float(timeline.entry_end)
	finish.set_shader_parameter("clock",maxf(song-float(timeline.art_motion_start),0.0))
	var f: Array=timeline.flash
	var flash:=smoothstep(float(f[0]),float(f[1]),song)*(1.0-smoothstep(float(f[2]),float(f[3]),song))
	finish.set_shader_parameter("flash",flash)
	var native_ending:=str(face_overlay.settings.get("ending_backend","godot"))=="storybrew"
	if is_instance_valid(face_overlay):
		if native_ending and song>=float(face_overlay.settings.capture_end):face_overlay.visible=false
		else:face_overlay.pose(song,camera)
	if is_instance_valid(title_overlay):
		if native_ending:title_overlay.visible=false
		else:title_overlay.pose(song)
	if song>=float(timeline.cg_end):
		entry_overlay.visible=false
		entry_view.render_target_update_mode=SubViewport.UPDATE_DISABLED
		return
	var blend: Array=timeline.previous_blend
	if is_instance_valid(entry_camera):entry_camera.size=camera.size
	if is_instance_valid(entry_overlay):
		entry_overlay.visible=t<3.2
		entry_view.render_target_update_mode=SubViewport.UPDATE_ALWAYS if t<3.2 else SubViewport.UPDATE_DISABLED
	entry_previous.visible=song<float(blend[1])+.03
	# A short overlap beneath the dense shower avoids an exposed hard cut
	# through the naturally varying gaps between petals.
	entry_material.set_shader_parameter("opacity",1.0-smoothstep(float(blend[0]),float(blend[1]),song))
	var previous_image: Texture2D=entry_previous_frames[0].image
	for item in entry_previous_frames:
		if song>=float(item.song_start):previous_image=item.image
	entry_material.set_shader_parameter("source_image",previous_image)
	entry_previous.scale=Vector3.ONE*camera.size/9.0
	for petal in entry_petals:
		var p: float=petal.phase
		var rate: float=petal.flutter
		var y: float=petal.y-petal.speed*t+.018*(sin(t*rate+p)-sin(p))
		petal.node.visible=y>-.70 and y<.70 and t<3.2
		if not petal.node.visible: continue
		var x: float=petal.x+petal.drift*entry_wind_distance(t)+.025*(sin(t*1.7+p)-sin(p))
		petal.node.position=Vector3(x*camera.size,y*camera.size,petal.depth)
		petal.node.scale=Vector3.ONE*petal.size*camera.size
		petal.node.rotation=Vector3(.65*sin(t*rate+p),.9*sin(t*rate*.7+p),p+t*petal.spin)

func build_lighting() -> void:
	var world_environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("fff1f5")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("f6e4ee")
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.glow_enabled = false
	world_environment.environment = env
	add_child(world_environment)
	key = DirectionalLight3D.new()
	key.name = "WarmCanopySun"
	key.rotation_degrees = Vector3(-32,-28,-18)
	key.light_color = Color("fff0da")
	key.light_energy = 0.9 * lighting
	key.shadow_enabled = false
	add_child(key)
	var fill := DirectionalLight3D.new()
	fill.name = "CoolSkyFill"
	fill.rotation_degrees = Vector3(24,146,12)
	fill.light_color = Color("dfebff")
	fill.light_energy = 0.25 * lighting
	add_child(fill)

func quad(material: Material, z: float, label: String) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = label
	var mesh := QuadMesh.new()
	mesh.size = Vector2(19.2,10.8)
	node.mesh = mesh
	node.material_override = material
	node.position.z = z
	add_child(node)
	return node

func build_plates() -> void:
	for is_character in [false,true]:
		var material := ShaderMaterial.new()
		material.shader = load("res://plate.gdshader")
		material.set_shader_parameter("source_image",load("res://assets/hand/source-hand-clean.png"))
		material.set_shader_parameter("occlusion",load("res://assets/hand/occlusion.png"))
		material.set_shader_parameter("receiver",load("res://assets/light-receiver.png"))
		material.set_shader_parameter("character_layer",is_character)
		material.set_shader_parameter("lighting",lighting)
		# Alpha-cutout receiver goes in front of the rear-petal volume.
		material.render_priority = 2 if is_character else -10
		plate_materials.append(material)
		quad(material,0.0 if is_character else -1.8,"Characters" if is_character else "PaintedCanopy")
	# Hands/sleeves stay ahead of hair while the boy's jacket remains behind it.
	var foreground := ShaderMaterial.new()
	foreground.shader = load("res://plate.gdshader")
	foreground.set_shader_parameter("source_image",load("res://assets/hand/foreground-hand-clean.png"))
	foreground.set_shader_parameter("occlusion",load("res://assets/hand/foreground.png"))
	foreground.set_shader_parameter("receiver",load("res://assets/light-receiver.png"))
	foreground.set_shader_parameter("character_layer",true)
	foreground.set_shader_parameter("lighting",lighting)
	plate_materials.append(foreground)
	quad(foreground,0.2,"FixedHandsAndSleeves")
	sunlight = ShaderMaterial.new()
	sunlight.shader = load("res://sunlight.gdshader")
	sunlight.render_priority = -8
	sunlight.set_shader_parameter("lighting",lighting)
	quad(sunlight,-1.65,"CanopySunlight")

func bezier(a: Vector2,b: Vector2,c: Vector2,d: Vector2,t: float) -> Vector2:
	return a * pow(1-t,3) + b * 3*t*pow(1-t,2) + c * 3*t*t*(1-t) + d*t*t*t

func petal_mesh() -> ArrayMesh:
	# A notched petal silhouette, with five rings of real cupped geometry.
	var curves := [
		[Vector2(0,-0.54),Vector2(0.27,-0.34),Vector2(0.48,-0.11),Vector2(0.44,0.15)],
		[Vector2(0.44,0.15),Vector2(0.42,0.40),Vector2(0.24,0.56),Vector2(0.09,0.48)],
		[Vector2(0.09,0.48),Vector2(0.06,0.46),Vector2(0.02,0.43),Vector2(0,0.43)],
		[Vector2(0,0.43),Vector2(-0.03,0.44),Vector2(-0.06,0.47),Vector2(-0.12,0.49)],
		[Vector2(-0.12,0.49),Vector2(-0.31,0.55),Vector2(-0.49,0.27),Vector2(-0.42,0.08)],
		[Vector2(-0.42,0.08),Vector2(-0.36,-0.19),Vector2(-0.16,-0.44),Vector2(0,-0.54)]]
	var outline: Array[Vector2] = []
	for c in curves:
		for j in 10: outline.append(bezier(c[0],c[1],c[2],c[3],float(j)/10.0))
	var vertices := PackedVector3Array([Vector3.ZERO])
	var normals := PackedVector3Array([Vector3(0,0,1)])
	var uvs := PackedVector2Array([Vector2(0.5,0.5)])
	var indices := PackedInt32Array()
	for ring in range(1,6):
		for point in outline:
			var p: Vector2 = point * float(ring)/5.0
			p.x*=0.82
			var z := -0.36*p.x*p.x + 0.10*p.y*p.y + 0.028*sin(p.y*4.0)
			vertices.append(Vector3(p.x,p.y,z))
			normals.append(Vector3(0.72*p.x,-0.20*p.y-0.112*cos(p.y*4),1).normalized())
			uvs.append(Vector2(p.x+0.5,p.y+0.54))
	var count := outline.size()
	for j in count:
		indices.append_array(PackedInt32Array([0,1+j,1+(j+1)%count]))
	for ring in 4:
		for j in count:
			var a := 1 + ring*count+j
			var b := 1 + ring*count+(j+1)%count
			var c := a+count
			var d := b+count
			indices.append_array(PackedInt32Array([a,c,b,b,c,d]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_TEX_UV]=uvs
	arrays[Mesh.ARRAY_INDEX]=indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh

func build_petals() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1619500
	var mesh := petal_mesh()
	for color in [Color("ffdae5"),Color("ffeaf0"),Color("f5b9cf"),Color("fff0ed")]:
		var material := ShaderMaterial.new()
		material.shader = load("res://petal.gdshader")
		material.set_shader_parameter("petal_color",color)
		material.set_shader_parameter("lighting",lighting)
		petal_materials.append(material)
	# Append another 500 after the original population so its paths stay fixed.
	# Totals by depth: 628 rear, 280 middle, 92 near; not all visible at once.
	for layer in [0,1,2,0,1,2]:
		var count: int = [314,140,46][layer]
		for i in count:
			var node := MeshInstance3D.new()
			node.name = "Petal_%d_%04d" % [layer,petals.size()]
			node.mesh = mesh
			node.material_override = petal_materials[rng.randi_range(0,3)]
			var s := rng.randf_range(0.055,0.115) if layer==0 else (rng.randf_range(0.11,0.22) if layer==1 else rng.randf_range(0.28,0.51))
			node.scale = Vector3.ONE*s
			node.visible = petal_strength>0.0
			add_child(node)
			petals.append({"node":node,"layer":layer,"x":rng.randf_range(-12,10),"y":rng.randf_range(-7,7),
				"z":rng.randf_range(-1.45,-0.25) if layer==0 else (rng.randf_range(0.25,1.35) if layer==1 else rng.randf_range(2.4,3.4)),
				"speed":rng.randf_range(0.30,0.60) * [0.75,1.0,1.25][layer],"phase":rng.randf()*TAU,
				"spin":Vector3(rng.randf_range(0.28,0.65),rng.randf_range(0.5,1.3),rng.randf_range(-0.65,0.65))})

func native_petal_mesh(size: Vector2) -> ArrayMesh:
	# Preserve the artist's UV/soft silhouette while giving each cutout curvature.
	var vertices := PackedVector3Array()
	var uvs := PackedVector2Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	const STEPS := 12
	for y in range(STEPS+1):
		for x in range(STEPS+1):
			var uv := Vector2(float(x)/STEPS,float(y)/STEPS)
			var fold := 0.035*size.x*pow(uv.x*2-1,2)+0.015*size.y*sin(uv.y*PI)
			vertices.append(Vector3((uv.x-0.5)*size.x,(0.5-uv.y)*size.y,fold))
			uvs.append(uv)
			normals.append(Vector3.FORWARD)
	for y in STEPS:
		for x in STEPS:
			var a := y*(STEPS+1)+x
			var b := a+1
			var c := a+STEPS+1
			indices.append_array(PackedInt32Array([a,c,b,b,c,c+1]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_TEX_UV]=uvs
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_INDEX]=indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh

func build_native_petals() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/native-petals/manifest.json"))
	var i := 0
	for item in data.petals:
		var material := ShaderMaterial.new()
		material.shader = load("res://native-petal.gdshader")
		material.set_shader_parameter("petal_image",load(item.texture))
		material.set_shader_parameter("lighting",lighting)
		var node := MeshInstance3D.new()
		node.name = "Native_"+str(item.id)
		var size := Vector2(float(item.rect[2]),float(item.rect[3]))*0.01
		node.mesh = native_petal_mesh(size)
		node.material_override = material
		add_child(node)
		var origin := Vector3((float(item.center[0])-960)*0.01,(540-float(item.center[1]))*0.01,float(item.depth))
		native_petals.append({"node":node,"material":material,"origin":origin,"size":size,
			"phase":float(i)*1.73,"speed":Vector2(0.24+float(i%4)*0.035,0.58+float(i%5)*0.055),
			"edge_clipped":bool(item.get("edge_clipped",false)),"completed":bool(item.get("completed",false)),
			"clip_edge":str(item.get("clip_edge",""))})
		i+=1

func pose(capture_time: float) -> void:
	pose_camera(capture_time)
	# The slower rectangular capture still needs the live, lit CG after the
	# camera has stopped. Hide 3D only when the portrait handoff is complete.
	var only_cards:=capture_time+float(timeline.song_start)>=float(face_overlay.settings.capture_end)
	if only_cards!=ending_only:
		if only_cards:
			ending_visibility.clear()
			for child in get_children():
				if child is Node3D and not child is Camera3D:
					ending_visibility.append({"node":child,"visible":child.visible})
					child.visible=false
		else:
			for item in ending_visibility:item.node.visible=item.visible
		finish_overlay.visible=not only_cards
		ending_only=only_cards
	if only_cards:return
	# Preserve the hand/hair/native-petal phases at the same song timestamps.
	var t:=maxf(capture_time+float(timeline.song_start)-float(timeline.art_motion_start),0.0)
	hair.pose(t,hair_strength,hair_visible)
	hand.pose(t if hand_strength>0 else 0.0)
	for material in plate_materials: material.set_shader_parameter("clock",t)
	sunlight.set_shader_parameter("clock",t)
	for petal in petals:
		var p: float = petal.phase
		var speed: float = petal.speed * petal_strength
		var x := wrapf(float(petal.x) - t*speed*0.64 + 0.24*sin(t*0.62+p),-12.0,10.0)
		var y := wrapf(float(petal.y) - t*speed + 0.12*sin(t*1.13+p),-7.0,7.0)
		var z: float = petal.z + 0.12*sin(t*0.65+p)
		# Smoothly bend foreground trajectories around the eyes/palm, never pop
		# individual petals on/off when they enter a protected screen rectangle.
		var face := exp(-pow((x+0.7)/1.15,2.0)-pow((y-2.35)/1.1,2.0))
		var hand := exp(-pow((x+3.75)/0.75,2.0)-pow((y+1.0)/0.65,2.0))
		if petal.layer>0:
			x-=1.1*face+0.7*hand
			y-=0.4*face
		petal.node.position = Vector3(x,y,z)
		petal.node.rotation = Vector3(0.42*sin(t*0.8+p),0.5,p) + petal.spin*t
	for petal in native_petals:
		var motion_time := t * NATIVE_PETAL_SPEED
		var p: float = petal.phase
		var s: Vector2 = petal.speed * petal_strength
		var origin: Vector3 = petal.origin
		# Start at the native coordinates, then release into the existing wind.
		var move := Vector3(-motion_time*s.x+0.13*(sin(motion_time*0.64+p)-sin(p)),
			-motion_time*s.y+0.07*(sin(motion_time*0.91+p)-sin(p)),0.10*(sin(motion_time*0.57+p)-sin(p)))
		var position_now := origin+move
		if petal.edge_clipped and not petal.completed:
			# Faster wind must not pull the source's right crop into this view.
			if petal.clip_edge == "right": position_now.x=origin.x+absf(move.x)
			elif petal.clip_edge == "top": position_now.x=origin.x+absf(move.x)
		# Native painted petals leave the shot once. Never wrap them back into
		# the frame or pin them to their original positions over the portrait.
		var eye_now := exp(-pow((position_now.x+0.6)/1.6,2)-pow((position_now.y-2.8)/1.6,2))
		var eye_start := exp(-pow((origin.x+0.6)/1.6,2)-pow((origin.y-2.8)/1.6,2))
		position_now.x+=1.1*(eye_now-eye_start)
		petal.node.position=position_now
		petal.node.rotation=Vector3(0.18*(sin(motion_time*0.65+p)-sin(p)),
			0.25*(sin(motion_time*0.46+p*0.7)-sin(p*0.7)),0.13*(sin(motion_time*0.56+p)-sin(p)))
		petal.material.set_shader_parameter("clock",t)
		petal.node.visible=petal_strength>0.0

func _process(delta: float) -> void:
	if capture:
		if frame>=frame_count:
			get_tree().quit()
			return
		pose(fixed_time if fixed_time>=0.0 else capture_start+float(frame)/fps)
		frame+=1
	else:
		clock+=delta
		pose(fixed_time if fixed_time>=0.0 else fmod(clock,duration))
