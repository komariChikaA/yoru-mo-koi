extends Node

# Song time = local time + 59.200. All animation can be sampled deterministically.
const START := 59.2
const DURATION := 7.5
const SIZE := Vector2(1920, 1080)
var scene_view: SubViewport
var puppet_view: SubViewport
var puppet_entry: Node2D
var incoming_world: Node2D
var incoming_motion: Script
var incoming_atmosphere:Node2D
var incoming_particles:Node2D
var transition: ShaderMaterial
var clock := 0.0
var fixed_time := -1.0
var start_time := 0.0
var capture_fps:=0.0
var capture_frame:=0
var room: SubViewport
var world: Node3D
var camera: Camera3D
var focus: CameraAttributesPractical
var room_image: TextureRect
var backdrop: TextureRect
var wash: ColorRect
var flash: ColorRect
var photos: SubViewport
var photo_world: Node3D
var photo_camera: Camera3D
var photo_image: TextureRect
var photo_finish: ShaderMaterial
var first_photo: Node3D
var central_ink: StandardMaterial3D
var central_reverse: MeshInstance3D
var ring_root: Node3D
var ring_ink: ShaderMaterial
var ring_decor_ink: StandardMaterial3D
var orbit_ring: MeshInstance3D
var orbit_marker: MeshInstance3D
var spin_particles: Array[MeshInstance3D] = []
var spin_lines: Array[MeshInstance3D] = []
var sms_view: SubViewport
var sms_phone: Node3D
var sms_brake_y := 0.25
var sms_image: TextureRect
var sms_finish: ShaderMaterial
var silhouette_call: Node2D
var silhouette_style := "simple"
var blue_hold: ColorRect
var side_photos: Array[Node3D] = []
var finish: ShaderMaterial
var bg_finish: ShaderMaterial
var phone: Node3D
var phone_point := Vector2(700, 570)

func unit(a: float, b: float, t: float) -> float:
	return clampf((t - a) / (b - a), 0, 1)

func smooth01(q: float) -> float:
	return q * q * (3 - 2 * q)

func in_out_cubic(q: float) -> float:
	return 4 * q * q * q if q < 0.5 else 1 - pow(-2 * q + 2, 3) / 2

func out_cubic(q: float) -> float:
	return 1 - pow(1-q,3)

func sms_drop_y(t: float) -> float:
	# Rapid entry, then a visible long OutQuad tail from the lower-quarter boundary.
	var end_y := -0.055
	if t < 4.05:
		var q := unit(3.85,4.05,t)
		var distance := 1.22-sms_brake_y
		var join_speed := 2*(sms_brake_y-end_y)/0.85
		# Hermite entry matches the tail speed, avoiding a sudden stop at the join.
		var moved := (-2*q*q*q+3*q*q)*distance+(q*q*q-2*q*q+q)*2.0+(q*q*q-q*q)*join_speed*0.20
		return 1.22-moved
	return lerpf(sms_brake_y,end_y,1-pow(1-unit(4.05,4.90,t),2))

func out_back(q: float) -> float:
	var v := q-1
	return 1+2.70158*v*v*v+1.70158*v*v

func out_sine(q: float) -> float:
	return sin(q*PI/2)

func in_out_sine(q: float) -> float:
	return (1-cos(PI*q))/2

func spin_in_out(q: float) -> float:
	# Short sine acceleration, then a longer sine deceleration with matching speed.
	var split := 0.28
	return split*(1-cos(PI*0.5*q/split)) if q < split else split+(1-split)*sin(PI*0.5*(q-split)/(1-split))

func bezier3(a: Vector3, b: Vector3, c: Vector3, d: Vector3, q: float) -> Vector3:
	return a*pow(1-q,3)+3*b*pow(1-q,2)*q+3*c*(1-q)*q*q+d*q*q*q

func mat(color: Color, rough: float = 0.6) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	return m

func box(parent: Node3D, size: Vector3, pos: Vector3, material: Material) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	n.mesh = mesh
	n.material_override = material
	n.position = pos
	parent.add_child(n)
	return n

func cylinder(parent: Node3D, radius: float, height: float, pos: Vector3, material: Material) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 24
	n.mesh = mesh
	n.material_override = material
	n.position = pos
	parent.add_child(n)
	return n

func atlas(n: Node, tex: Texture2D) -> void:
	if n is MeshInstance3D:
		for i in n.mesh.get_surface_count():
			var original: Material = n.get_active_material(i)
			var m: StandardMaterial3D = original.duplicate() if original is StandardMaterial3D else mat(Color.WHITE)
			m.albedo_texture = tex
			m.albedo_color = Color.WHITE
			m.vertex_color_use_as_albedo = false
			m.roughness = 0.57
			n.set_surface_override_material(i, m)
	for c in n.get_children():
		atlas(c, tex)

func mesh_bounds(node: Node3D, transform: Transform3D) -> AABB:
	var tr := transform * node.transform
	var result := AABB()
	if node is MeshInstance3D:
		result = tr * node.get_aabb()
	for child in node.get_children():
		if child is Node3D:
			var sub := mesh_bounds(child,tr)
			if sub.size.length() > 0:
				result = sub if result.size.length() == 0 else result.merge(sub)
	return result

func mesh_lowest_y(node: Node3D, transform: Transform3D) -> float:
	var tr := transform * node.transform
	var lowest := INF
	if node is MeshInstance3D:
		for vertex in node.mesh.get_faces():
			lowest = minf(lowest,(tr*vertex).y)
	for child in node.get_children():
		if child is Node3D:
			lowest = minf(lowest,mesh_lowest_y(child,tr))
	return lowest

func furniture(name: String, pos: Vector3, color_atlas: String, turn: float, width: float) -> Node3D:
	var wrapper := Node3D.new()
	world.add_child(wrapper)
	wrapper.position = pos
	wrapper.rotation.y = turn
	var n: Node3D = load("res://assets/bedroom-kit/FBX/Furniture/" + name + ".fbx").instantiate()
	var bounds := mesh_bounds(n,Transform3D.IDENTITY)
	var scale_value := width / bounds.size.x
	# Imported meshes have different origins. Centre their footprint and ground them.
	n.position = n.position*scale_value - Vector3(bounds.get_center().x,bounds.position.y,bounds.get_center().z)*scale_value
	n.scale *= scale_value
	wrapper.add_child(n)
	atlas(n,load("res://assets/" + color_atlas + ".png"))
	print("ROOM_FURNITURE ",name," size=",bounds.size*scale_value," centre=",pos)
	return wrapper

func flat_slab(parent: Node3D, size: Vector3, pos: Vector3, radius: float, material: Material) -> MeshInstance3D:
	var n := rounded_slab(parent,Vector3(size.x,size.z,size.y),radius,pos,material)
	n.rotation.x = -PI/2
	return n

func window(parent: Node3D, centre_x: float, width: float) -> void:
	var cream := mat(Color("eadbd5"))
	var frame := mat(Color("a9acc5"))
	box(parent,Vector3(width+0.12,0.08,0.16),Vector3(centre_x,1.03,0.03),cream)
	box(parent,Vector3(width+0.12,0.08,0.12),Vector3(centre_x,2.51,0.01),cream)
	for x in [-width/2,0.0,width/2]:
		box(parent,Vector3(0.045,1.43,0.09),Vector3(centre_x+x,1.77,0),frame)
	var view := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(width,1.40)
	view.mesh = quad
	var sky := mat(Color("dcecff"))
	sky.albedo_texture = load("res://assets/window-sky.png")
	sky.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	view.material_override = sky
	view.position = Vector3(centre_x,1.77,-0.065)
	parent.add_child(view)
	var pole := cylinder(parent,0.014,width+0.72,Vector3(centre_x,2.57,0.13),cream)
	pole.rotation.z = PI/2
	for side in [-1,1]:
		for i in 6:
			var c := cylinder(parent,0.040,1.62,Vector3(centre_x+side*(width/2+0.07+i*0.049),1.75,0.11),mat(Color("edc2a4")))
			c.scale.z = 0.60
		box(parent,Vector3(0.28,0.055,0.07),Vector3(centre_x+side*(width/2+0.19),1.31,0.15),mat(Color("d2a489")))
	var sheer := mat(Color(0.65,0.72,0.9,0.13))
	sheer.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	for i in 14:
		box(parent,Vector3(0.020,1.40,0.012),Vector3(centre_x-width/2+0.05+i*(width-0.10)/13,1.77,0.095),sheer)

func make_room() -> void:
	room = SubViewport.new()
	room.size = Vector2i(1920, 1080)
	room.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	room.msaa_3d = Viewport.MSAA_4X
	room.own_world_3d = true
	add_child(room)
	world = Node3D.new()
	room.add_child(world)
	var env_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("fff4e8")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("fff0df")
	env.ambient_light_energy = 0.56
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_intensity = 0.30
	env.glow_hdr_threshold = 1.15
	env.ssao_enabled = true
	env.ssao_intensity = 0.35
	env_node.environment = env
	world.add_child(env_node)
	var wall := mat(Color("f3e6dc"))
	var wood := mat(Color("a88367"),0.40)
	var cream := mat(Color("f2dfc5"),0.55)
	var pink := mat(Color("d59dbc"))
	var plum := mat(Color("9f8cae"))
	var colors := [Color("dbadc5"),Color("a2b9ca"),Color("edd3a4"),Color("b6a1bf")]
	# A compact 4.8m bedroom, with rear and right windows like the reference.
	box(world,Vector3(4.8,0.10,4.8),Vector3(0,-0.065,0),wood)
	for row in 16:
		for col in 4:
			var tone := 0.02*sin(row*1.6+col)
			box(world,Vector3(1.19,0.012,0.295),Vector3(-1.8+col*1.2,-0.010,-2.25+row*0.30),mat(Color(0.58+tone,0.43+tone,0.32+tone),0.40))
	for side in [0,1]:
		var panel := Node3D.new()
		world.add_child(panel)
		panel.position = Vector3(0,0,-2.40) if side == 0 else Vector3(2.40,0,0)
		panel.rotation.y = 0 if side == 0 else -PI/2
		var window_x: float = -0.65 if side == 0 else -0.55
		var window_w: float = 1.60 if side == 0 else 1.45
		box(panel,Vector3(4.8,1.02,0.10),Vector3(0,0.49,0),wall)
		box(panel,Vector3(4.8,0.30,0.10),Vector3(0,2.66,0),wall)
		var left_width := 2.4+window_x-window_w/2
		var right_width := 2.4-window_x-window_w/2
		box(panel,Vector3(left_width,1.48,0.10),Vector3(-2.4+left_width/2,1.77,0),wall)
		box(panel,Vector3(right_width,1.48,0.10),Vector3(2.4-right_width/2,1.77,0),wall)
		window(panel,window_x,window_w)
		box(panel,Vector3(4.8,0.085,0.08),Vector3(0,0.04,0.08),mat(Color("756056")))
	box(world,Vector3(0.10,2.8,4.8),Vector3(-2.40,1.35,0),wall)
	box(world,Vector3(0.08,0.085,4.8),Vector3(-2.31,0.04,0),mat(Color("756056")))
	# Mesh footprints, rather than asset pivots, define the wall clearances.
	furniture("Bed_01",Vector3(-1.59,0,-0.99),"bed-atlas",0.0,1.50)
	furniture("Table_01",Vector3(1.22,0,-1.90),"pink-atlas",0.0,2.02)
	furniture("Chair_03",Vector3(1.18,0,-0.86),"pink-atlas",PI,0.53)
	furniture("Cupboard_01",Vector3(2.09,0,0.62),"pink-atlas",-PI/2,1.32)
	# Soft bedding and a quilt seam pattern, with bedside storage against the wall.
	flat_slab(world,Vector3(1.35,0.10,1.90),Vector3(-1.59,0.64,-0.76),0.10,mat(Color("f3e7ce")))
	flat_slab(world,Vector3(0.66,0.13,0.37),Vector3(-1.59,0.75,-1.77),0.09,mat(Color("fff1db")))
	for i in 4:
		box(world,Vector3(1.24,0.003,0.008),Vector3(-1.59,0.692,-1.38+i*0.40),mat(Color("ded1b5")))
	for x in [-1.91,-1.27]:
		box(world,Vector3(0.008,0.003,1.76),Vector3(x,0.692,-0.76),mat(Color("ded1b5")))
	box(world,Vector3(0.46,0.48,0.45),Vector3(-0.54,0.24,-2.07),cream)
	box(world,Vector3(0.47,0.035,0.46),Vector3(-0.54,0.497,-2.07),mat(Color("d8b999")))
	for y in [0.16,0.34]:
		box(world,Vector3(0.40,0.16,0.015),Vector3(-0.54,y,-1.836),mat(Color("e6c8a8")))
		box(world,Vector3(0.09,0.018,0.022),Vector3(-0.54,y,-1.816),plum)
	# Desk hutch sits on the model's 83cm desktop, with books and desk accessories.
	box(world,Vector3(1.98,0.06,0.29),Vector3(1.22,1.21,-2.18),plum)
	for x in [0.25,2.19]:
		box(world,Vector3(0.055,0.38,0.31),Vector3(x,1.01,-2.18),pink)
	for i in 20:
		var h: float = 0.20+0.035*sin(i)
		box(world,Vector3(0.060,h,0.18),Vector3(0.37+i*0.083,1.24+h/2,-2.18),mat(colors[i%4]))
		box(world,Vector3(0.042,0.009,0.006),Vector3(0.37+i*0.083,1.30,-2.086),cream)
	for i in 3:
		box(world,Vector3(0.31,0.025,0.22),Vector3(1.82,0.848+i*0.026,-1.68),mat(colors[i]))
	cylinder(world,0.043,0.10,Vector3(0.54,0.881,-1.67),mat(Color("e3be86")))
	for i in 5:
		var pencil := cylinder(world,0.003,0.15,Vector3(0.52+i*0.01,0.96,-1.67),mat(colors[i%4]))
		pencil.rotation.z = -0.13+i*0.05
	var clock_face := cylinder(world,0.070,0.024,Vector3(0.91,0.912,-1.65),cream)
	clock_face.rotation.x = PI/2
	box(world,Vector3(0.003,0.040,0.004),Vector3(0.91,0.928,-1.635),plum)
	box(world,Vector3(0.032,0.003,0.004),Vector3(0.922,0.912,-1.634),plum)
	cylinder(world,0.09,0.022,Vector3(1.98,0.846,-1.96),cream)
	cylinder(world,0.012,0.32,Vector3(1.98,1.01,-1.96),plum)
	var shade := cylinder(world,0.10,0.10,Vector3(1.98,1.20,-1.96),mat(Color("efc4ba")))
	shade.rotation.z = -0.26
	# Low drawer chest along the right wall, plus a small plant and wall pinboard.
	box(world,Vector3(0.43,0.61,0.56),Vector3(2.125,0.305,-0.38),pink)
	for y in [0.13,0.31,0.49]:
		box(world,Vector3(0.025,0.16,0.51),Vector3(1.90,y,-0.38),plum)
		box(world,Vector3(0.033,0.019,0.11),Vector3(1.879,y,-0.38),cream)
	cylinder(world,0.07,0.11,Vector3(2.12,0.67,-0.38),mat(Color("e5ba9d")))
	for i in 5:
		var leaf := cylinder(world,0.019,0.17,Vector3(2.12+0.018*sin(i*2),0.79,-0.38+0.018*cos(i*2)),mat(Color("a5b295")))
		leaf.rotation.z = -0.40+0.20*i
	box(world,Vector3(0.66,0.47,0.035),Vector3(1.40,1.85,-2.32),mat(Color("c6a886")))
	for i in 4:
		box(world,Vector3(0.22,0.15,0.008),Vector3(1.24+(i%2)*0.30,1.74+(i/2)*0.20,-2.294),mat(colors[i]))
	# Calendar grid on the left wall and a framed keepsake above the bed.
	box(world,Vector3(0.025,0.48,0.34),Vector3(-2.325,1.52,0.28),cream)
	box(world,Vector3(0.028,0.13,0.34),Vector3(-2.309,1.69,0.28),pink)
	for row in 4:
		for col in 7:
			box(world,Vector3(0.005,0.014,0.015),Vector3(-2.309,1.56-row*0.058,0.15+col*0.042),plum)
	# Right-wall AC has its long side along the wall, not projecting into the room.
	box(world,Vector3(0.24,0.28,0.90),Vector3(2.23,2.46,-1.76),mat(Color("f4f2fa")))
	for y in [2.37,2.39,2.41]:
		box(world,Vector3(0.008,0.008,0.72),Vector3(2.105,y,-1.76),plum)
	# Larger centre table and rug anchor the photograph's composition.
	flat_slab(world,Vector3(1.93,0.014,1.48),Vector3(0,0.005,0.61),0.12,mat(Color("d9bdc6")))
	flat_slab(world,Vector3(1.40,0.045,0.90),Vector3(0,0.4375,0.60),0.075,mat(Color("e5ceb0"),0.48))
	for x in [-0.56,0.56]:
		for z in [0.27,0.93]:
			cylinder(world,0.032,0.415,Vector3(x,0.2075,z),mat(Color("c6a789")))
	# A magazine and ceramic cup provide scale without crowding the floating phone.
	for i in 2:
		box(world,Vector3(0.23,0.012,0.16),Vector3(-0.37,0.469+i*0.013,0.53),mat(colors[i]))
	cylinder(world,0.032,0.071,Vector3(0.39,0.497,0.41),cream)
	var rim := cylinder(world,0.026,0.003,Vector3(0.39,0.534,0.41),mat(Color("b39178")))
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-36,-32,0)
	sun.light_color = Color("fff2dc")
	sun.light_energy = 1.00
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 20
	world.add_child(sun)
	var fill := OmniLight3D.new()
	fill.position = Vector3(-1,2.6,2)
	fill.light_color = Color("f4d7e9")
	fill.light_energy = 0.38
	fill.omni_range = 8
	world.add_child(fill)
	make_phone()
	camera = Camera3D.new()
	camera.fov = 47
	camera.near = 0.025
	camera.current = true
	world.add_child(camera)
	focus = CameraAttributesPractical.new()
	focus.dof_blur_far_enabled = true
	focus.dof_blur_far_transition = 1.5
	focus.dof_blur_amount = 0.09
	camera.attributes = focus

func rounded_slab(parent: Node3D, size: Vector3, radius: float, pos: Vector3, material: Material) -> MeshInstance3D:
	var ring: Array[Vector2] = []
	for corner in 4:
		var centre := Vector2((1 if corner in [0,3] else -1)*(size.x/2-radius), (1 if corner in [0,1] else -1)*(size.y/2-radius))
		for step in 6:
			var angle := PI/2*corner + PI/2*step/5
			ring.append(centre + Vector2(cos(angle),sin(angle))*radius)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in ring.size():
		var j := (i+1)%ring.size()
		for z_sign in [-1,1]:
			var tri := [Vector3(0,0,z_sign*size.z/2),Vector3(ring[i].x,ring[i].y,z_sign*size.z/2),Vector3(ring[j].x,ring[j].y,z_sign*size.z/2)]
			if z_sign == 1: tri.reverse()
			for v in tri: st.add_vertex(v)
		var a := Vector3(ring[i].x,ring[i].y,-size.z/2)
		var b := Vector3(ring[j].x,ring[j].y,-size.z/2)
		var c := Vector3(ring[j].x,ring[j].y,size.z/2)
		var d := Vector3(ring[i].x,ring[i].y,size.z/2)
		for v in [a,d,c,a,c,b]: st.add_vertex(v)
	st.generate_normals()
	var n := MeshInstance3D.new()
	n.mesh = st.commit()
	n.material_override = material
	n.position = pos
	parent.add_child(n)
	return n

func make_phone() -> void:
	phone = phone_model(world,load("res://assets/ren-call-screen.png"))
	phone.position = Vector3(0,0.512,0.60)
	phone.rotation = Vector3(deg_to_rad(30),-0.09,0)

func phone_model(parent: Node3D, screen_texture: Texture2D) -> Node3D:
	var handset := Node3D.new()
	parent.add_child(handset)
	# Downloaded CC0 Smartphone by smallbigsquare: keep its casing and side-button mesh.
	var body: Node3D = load("res://assets/public-smartphone/smartphone.glb").instantiate()
	var bounds := mesh_bounds(body,Transform3D.IDENTITY)
	var scale_value := 0.068/bounds.size.x
	body.scale *= scale_value
	body.position = -bounds.get_center()*scale_value
	handset.add_child(body)
	atlas(body,load("res://assets/public-smartphone/reference-colors.png"))
	print("PUBLIC_PHONE size=",bounds.size*scale_value," source=https://poly.pizza/m/4DRZmTs3jq CC0")
	var dark := mat(Color("222830"),0.45)
	var face := Node3D.new()
	face.rotation.x = -PI/2
	# Front normal is +Y in the source model, before the whole-phone held tilt.
	face.position.y = bounds.size.y*scale_value/2+0.00015
	handset.add_child(face)
	# Fit all supplied call content inside the display without stretching the source image.
	rounded_slab(face,Vector3(0.061,0.117,0.0004),0.0010,Vector3(0,0.002,0),dark)
	var screen := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(0.060,0.116)
	screen.mesh = quad
	var m := mat(Color.WHITE)
	m.albedo_texture = screen_texture
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	screen.material_override = m
	screen.position = Vector3(0,0.002,0.0003)
	face.add_child(screen)
	rounded_slab(face,Vector3(0.012,0.0015,0.0005),0.0006,Vector3(0,0.067,0),dark)
	var aperture := cylinder(face,0.0011,0.0005,Vector3(0.016,0.067,0),dark)
	aperture.rotation.x = PI/2
	var home := cylinder(face,0.004,0.0004,Vector3(0,-0.066,0),mat(Color("d3bfd8"),0.4))
	home.rotation.x = PI/2
	return handset

func rect(tex: Texture2D) -> TextureRect:
	var r := TextureRect.new()
	r.texture = tex
	r.size = SIZE
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	return r

func poly(points: PackedVector2Array, color: Color, texture: Texture2D = null) -> Polygon2D:
	var p := Polygon2D.new()
	p.polygon = points
	p.color = color
	p.texture = texture
	return p

func photo(tex: Texture2D) -> Node3D:
	var n := Node3D.new()
	photo_world.add_child(n)
	# Real paper thickness, a shaded reverse and a front print in the 3D world.
	box(n,Vector3(4.14,2.70,0.018),Vector3.ZERO,mat(Color("fff8ea"),0.86))
	var image_mesh := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(3.78,2.12625)
	image_mesh.mesh = quad
	var ink := mat(Color.WHITE,0.90)
	ink.albedo_texture = tex
	ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ink.cull_mode = BaseMaterial3D.CULL_BACK
	image_mesh.material_override = ink
	image_mesh.position = Vector3(0,0.114,0.012)
	n.add_child(image_mesh)
	# A plain inset on the reverse makes face-down cards visibly different.
	box(n,Vector3(3.72,2.25,0.002),Vector3(0,0.075,-0.011),mat(Color("e6ddcb"),0.93))
	return n

func make_photos() -> void:
	photos = SubViewport.new()
	photos.size = Vector2i(1920,1080)
	photos.transparent_bg = false
	photos.own_world_3d = true
	photos.msaa_3d = Viewport.MSAA_4X
	photos.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(photos)
	photo_world = Node3D.new()
	photos.add_child(photo_world)
	var env_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("fff8ed")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("fff5e7")
	env.ambient_light_energy = 0.85
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env_node.environment = env
	photo_world.add_child(env_node)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-28,-18,0)
	light.light_color = Color("fff3e3")
	light.light_energy = 0.75
	light.shadow_enabled = true
	photo_world.add_child(light)
	photo_camera = Camera3D.new()
	photo_camera.position = Vector3(0,0,8)
	photo_camera.fov = 36
	photo_camera.near = 0.04
	photo_camera.current = true
	var depth := CameraAttributesPractical.new()
	depth.dof_blur_far_enabled = true
	depth.dof_blur_far_distance = 7.6
	depth.dof_blur_far_transition = 3.4
	depth.dof_blur_amount = 0.055
	photo_camera.attributes = depth
	photo_world.add_child(photo_camera)
	# The photo field uses the plain warm environment background. Room content
	# belongs only inside the central print until the camera enters that print.
	# The rejected Ren CG is absent. Different cards may reveal their plain reverse.
	var actors := ["hiiro-01","hiiro-02","hiiro-03","hiiro-04","hiiro-05","hiiro-06","shiori-01","shiori-02","shiori-03","kumo-01","kumo-02","kumo-03","kumo-04","kamome-01","kamome-02","kamome-03","kamome-04"]
	for i in 64:
		side_photos.append(photo(load("res://assets/photo-"+actors[i%actors.size()]+".png")))
	first_photo = photo(load("res://assets/gate-snapshot.png"))
	central_ink = first_photo.get_child(1).material_override
	# The same live print is present on both sides after the switch, including reverse views.
	first_photo.get_child(2).queue_free()
	central_reverse = MeshInstance3D.new()
	var reverse_quad := QuadMesh.new()
	reverse_quad.size = Vector2(3.78,2.12625)
	central_reverse.mesh = reverse_quad
	central_reverse.material_override = central_ink
	central_reverse.position = Vector3(0,0.114,-0.012)
	central_reverse.rotation.y = PI
	first_photo.add_child(central_reverse)
	ring_root = Node3D.new()
	photo_world.add_child(ring_root)
	orbit_ring = MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.370
	torus.outer_radius = 0.376
	torus.rings = 96
	torus.ring_segments = 8
	orbit_ring.mesh = torus
	ring_ink = ShaderMaterial.new()
	ring_ink.shader = load("res://orbit_ring.gdshader")
	orbit_ring.material_override = ring_ink
	ring_root.add_child(orbit_ring)
	ring_ink.set_shader_parameter("ink",Color("bdaabd"))
	ring_decor_ink = mat(Color("bdaabd"))
	ring_decor_ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring_decor_ink.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	orbit_marker = MeshInstance3D.new()
	var bead := SphereMesh.new()
	bead.radius = 0.014
	bead.height = 0.028
	orbit_marker.mesh = bead
	orbit_marker.material_override = ring_decor_ink
	ring_root.add_child(orbit_marker)
	# Small airborne specks and short rays launch from the rotating paper edges.
	for i in 36:
		var speck := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.020+0.006*(i%3)
		sphere.height = sphere.radius*2
		speck.mesh = sphere
		var ink := mat([Color("9d7a94"),Color("b28d51"),Color("8f82aa")][i%3])
		ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		ink.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		speck.material_override = ink
		photo_world.add_child(speck)
		spin_particles.append(speck)
	for i in 18:
		var ink := mat([Color("9d7d9a"),Color("b49665")][i%2])
		ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		ink.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		var ray := box(photo_world,Vector3(0.32+0.05*(i%3),0.014,0.014),Vector3.ZERO,ink)
		spin_lines.append(ray)

func update_spin_emission(t: float) -> void:
	for group in [spin_particles,spin_lines]:
		var rays: bool = group == spin_lines
		for i in group.size():
			var n: MeshInstance3D = group[i]
			var born: float = 0.80+(i%9)*0.075 if rays else 0.76+(i%12)*0.062
			var life: float = 0.48+(i%3)*0.08 if rays else 0.50+(i%4)*0.07
			var age := (t-born)/life
			n.visible = age >= 0 and age < 1
			if not n.visible: continue
			var theta: float = i*2.399963+0.35 if rays else i*2.399963
			var edge := minf(2.09/maxf(absf(cos(theta)),0.001),1.37/maxf(absf(sin(theta)),0.001))
			var source := Vector3(cos(theta)*edge,sin(theta)*edge,0.04)
			var born_spin := spin_in_out(unit(0.70,1.90,born))
			var basis := Basis.from_euler(Vector3(0,TAU*born_spin,deg_to_rad(20)))
			var centre := bezier3(Vector3(-0.42,0.65,1),Vector3(0.80,0.38,1.16),Vector3(0.36,-0.02,1.03),Vector3(0.06,-0.05,1),out_cubic(unit(0.23,0.85,born)))
			var direction := (basis*Vector3(cos(theta),sin(theta),0.12*sin(i*1.7))+Vector3(0,0.06,0.24)).normalized()
			var move := 1-pow(1-age,2)
			n.position = centre+basis*source*0.82+direction*move*(0.90+0.16*(i%4))+Vector3(0,-0.16*age*age,0.10)
			var fade := out_sine(unit(0,0.12,age))*(1-pow(age,2))
			n.material_override.albedo_color.a = fade*(0.70 if rays else 0.84)
			if rays:
				n.quaternion = Quaternion(Vector3.RIGHT,direction)
				n.scale = Vector3(0.5+0.5*sin(PI*age),1,1)
			else:
				n.scale = Vector3.ONE*(1-0.45*age)

func update_photos(t: float) -> void:
	photos.render_target_update_mode = SubViewport.UPDATE_ALWAYS if t < 2.58 else SubViewport.UPDATE_DISABLED
	var fall := out_cubic(unit(0.23,0.85,t))
	var spin := spin_in_out(unit(0.70,1.90,t))
	# A larger downward bow settles near the centre before the slower turn.
	first_photo.position = bezier3(Vector3(-0.42,0.65,1),Vector3(0.80,0.38,1.16),Vector3(0.36,-0.02,1.03),Vector3(0.06,-0.05,1),fall)
	first_photo.rotation = Vector3(0,TAU*spin,deg_to_rad(20)*(1-in_out_sine(unit(1.65,2.12,t))))
	first_photo.scale = Vector3.ONE*0.82
	# Change at the last edge-on pass, so the front emerges as the room and
	# the slow end of the complete turn never shows the old picture again.
	var room_print := spin >= 0.75
	var print_texture: Texture2D = room.get_texture() if room_print else load("res://assets/gate-snapshot.png")
	central_ink.albedo_texture = print_texture
	var ring_in := out_sine(unit(0.65,1.05,t))
	var ring_alpha := 0.32*ring_in*(1-out_sine(unit(1.55,1.85,t)))
	ring_root.position = Vector3(0.06,-1.60,1.0)
	ring_root.scale = Vector3.ONE
	ring_root.visible = t >= 0.65 and t < 1.85
	ring_ink.set_shader_parameter("reveal",out_sine(unit(0.65,1.15,t)))
	ring_ink.set_shader_parameter("opacity",ring_alpha)
	ring_ink.set_shader_parameter("head",spin)
	ring_decor_ink.albedo_color.a = ring_alpha
	orbit_marker.position = Vector3(sin(TAU*spin)*0.373,0.015,cos(TAU*spin)*0.373)
	# Begin entering during the last 0.25s of the turn instead of waiting for a hold.
	var enter := in_out_sine(unit(1.65,2.55,t))
	var print_centre := first_photo.to_global(Vector3(0,0.114,0.012))
	var fill_distance := (2.12625*0.82*0.5)/tan(deg_to_rad(18.0))
	var end := print_centre+Vector3(0,0,fill_distance)
	photo_camera.position = bezier3(Vector3(0,0,8),Vector3(-0.90,0.06,6.4),end+Vector3(-0.35,0.10,1.15),end,enter)
	photo_camera.look_at(Vector3(0,0,0).lerp(print_centre,enter))
	update_spin_emission(t)
	var slow_t := 0.14*out_sine(unit(0.23,1.75,t))+0.006*maxf(t-1.75,0)
	for i in side_photos.size():
		var n := side_photos[i]
		var row := floori(i/8.0)
		var lane: float = [-6.1,6.1,-4.3,4.3,-2.45,2.45,-0.8,0.8][i%8]
		var z: float = [-2.4,-4.2,-5.8,-1.4,-3.7,-0.8,-4.8,-2.9][i%8]-0.15*(row%3)
		var speed: float = 8.5+(i%5)*0.85
		var initial_y := -3.4+row*2.8+0.38*sin(i*2.19)
		n.visible = t >= 0.23 and t < 2.58
		n.position = Vector3(lane+0.32*sin(row*2.3)+0.12*slow_t*sin(i*1.7),initial_y-speed*slow_t-0.35*slow_t*slow_t,z)
		n.rotation = Vector3([-0.95,0.65,1.22,-0.52][i%4]+0.18*sin(row*1.4)+(0.65+0.08*(i%3))*slow_t,
			[-0.75,1.75,-1.30,0.45][i%4]+0.21*sin(row*2.1)+(-0.95 if i%2 else 0.82)*slow_t,
			[-0.35,0.28,0.48,-0.24][i%4]+0.12*sin(row*1.8)+(0.22 if i%2 else -0.26)*slow_t)
		n.scale = Vector3.ONE*(0.50+0.085*(i%4))

func make_sms() -> void:
	sms_view = SubViewport.new()
	sms_view.size = Vector2i(1920,1080)
	sms_view.transparent_bg = true
	sms_view.own_world_3d = true
	sms_view.msaa_3d = Viewport.MSAA_4X
	sms_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(sms_view)
	var sms_world := Node3D.new()
	sms_view.add_child(sms_world)
	var env_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0,0,0,0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.8
	env_node.environment = env
	sms_world.add_child(env_node)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-20,-20,0)
	light.light_energy = 0.9
	sms_world.add_child(light)
	sms_phone = phone_model(sms_world,load("res://assets/ren-mail-screen.png"))
	sms_phone.scale = Vector3.ONE*6.8
	# Keep the upper-right roll, with a small depth tilt exposing the casing edge.
	sms_phone.quaternion = Quaternion(Vector3.BACK,deg_to_rad(-30))*Quaternion(Vector3.UP,deg_to_rad(8))*Quaternion(Vector3.RIGHT,PI/2-deg_to_rad(4))
	var lens := Camera3D.new()
	lens.projection = Camera3D.PROJECTION_ORTHOGONAL
	lens.size = 1.0
	lens.position = Vector3(0,0,3)
	lens.current = true
	sms_world.add_child(lens)
	var bottom_y := mesh_lowest_y(sms_phone,Transform3D.IDENTITY)
	sms_brake_y = lens.project_position(Vector2(960,810),3.0).y-bottom_y
	print("SMS_BRAKE lower_edge_screen_y=0.75 root_y=",sms_brake_y," tail_seconds=0.85")

func make_canvas() -> void:
	scene_view = SubViewport.new()
	scene_view.size = Vector2i(1920,1080)
	scene_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(scene_view)
	var canvas := Node2D.new()
	scene_view.add_child(canvas)
	backdrop = rect(load("res://assets/gate-snapshot.png"))
	bg_finish = ShaderMaterial.new()
	bg_finish.shader = load("res://print_finish.gdshader")
	backdrop.material = bg_finish
	canvas.add_child(backdrop)
	wash = ColorRect.new()
	wash.size = SIZE
	wash.color = Color("fff8ed")
	canvas.add_child(wash)
	photo_image = rect(photos.get_texture())
	photo_finish = ShaderMaterial.new()
	photo_finish.shader = load("res://photo_focus.gdshader")
	photo_image.material = photo_finish
	canvas.add_child(photo_image)
	room_image = rect(room.get_texture())
	finish = ShaderMaterial.new()
	finish.shader = load("res://print_finish.gdshader")
	finish.set_shader_parameter("blur_px",0.6)
	room_image.material = finish
	canvas.add_child(room_image)
	blue_hold = ColorRect.new()
	blue_hold.size = SIZE
	blue_hold.color = Color("3e69a0")
	canvas.add_child(blue_hold)
	sms_image = rect(sms_view.get_texture())
	sms_finish = ShaderMaterial.new()
	sms_finish.shader = load("res://sms_silhouette.gdshader")
	sms_image.material = sms_finish
	canvas.add_child(sms_image)
	silhouette_call = load("res://silhouette_call.gd").new()
	silhouette_call.heroine = load("res://assets/ren-paper-cup-"+silhouette_style+".png")
	silhouette_call.shadow = load("res://assets/ren-paper-cup-shadow.png")
	silhouette_call.cup_anchor = silhouette_call.heroine_origin+Vector2(249,450)*silhouette_call.heroine_size/silhouette_call.heroine.get_size()
	sms_phone.position = Vector3(-0.47,-0.055,0)
	var sms_lens := sms_view.get_camera_3d()
	var front_y := 0.00525
	var frame_points := PackedVector2Array()
	for corner in 4:
		var centre := Vector2((1 if corner in [0,3] else -1)*0.026,(1 if corner in [0,1] else -1)*0.054)
		for step in 9:
			var a := corner*PI/2+step*PI/16
			var p := centre+Vector2(cos(a),sin(a))*0.004
			frame_points.append(sms_lens.unproject_position(sms_phone.to_global(Vector3(p.x,front_y,-p.y-0.002))))
	frame_points.append(frame_points[0])
	silhouette_call.phone_frame = frame_points
	silhouette_call.phone_speaker = PackedVector2Array([sms_lens.unproject_position(sms_phone.to_global(Vector3(-0.006,front_y,-0.067))),sms_lens.unproject_position(sms_phone.to_global(Vector3(0.006,front_y,-0.067)))])
	var home_points := PackedVector2Array()
	for i in 41:
		var a := i*TAU/40
		home_points.append(sms_lens.unproject_position(sms_phone.to_global(Vector3(0.004*cos(a),front_y,0.066-0.004*sin(a)))))
	silhouette_call.phone_home = home_points
	var icon_points := PackedVector2Array()
	for p in [Vector2(-0.009,0.022),Vector2(0.009,0.022),Vector2(0.009,0.008),Vector2(-0.009,0.008),Vector2(-0.009,0.022),Vector2(0,0.015),Vector2(0.009,0.022)]:
		icon_points.append(sms_lens.unproject_position(sms_phone.to_global(Vector3(p.x,front_y,-p.y))))
	silhouette_call.phone_icon = icon_points
	silhouette_call.icon_centre = (icon_points[0]+icon_points[2])*0.5
	silhouette_call.line_start = sms_lens.unproject_position(sms_phone.to_global(Vector3(0.034,front_y,0.010)))
	canvas.add_child(silhouette_call)
	flash = ColorRect.new()
	flash.size = SIZE
	flash.color = Color.WHITE
	canvas.add_child(flash)
	puppet_view = SubViewport.new()
	puppet_view.size = Vector2i(1920,1080)
	puppet_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(puppet_view)
	if ResourceLoader.exists("res://assets/incoming-cgc06-overscan.png"):
		incoming_motion=load("res://assets/cgc06-motion.gd")
		incoming_world=Node2D.new()
		puppet_view.add_child(incoming_world)
		var incoming_plate:=Sprite2D.new()
		incoming_plate.texture=load("res://assets/incoming-cgc06-overscan.png")
		incoming_plate.centered=false
		incoming_plate.position=Vector2(-128,-192)
		incoming_world.add_child(incoming_plate)
		incoming_particles=load("res://atmosphere.gd").new()
		incoming_particles.closeup_fill=true
		incoming_world.add_child(incoming_particles)
	elif ResourceLoader.exists("res://assets/incoming-cgc06.png"):
		# Land the existing whip on the exact opening composition of shot three.
		puppet_view.add_child(rect(load("res://assets/incoming-cgc06.png")))
	else:
		puppet_entry = load("res://puppet_entry.gd").new()
		puppet_view.add_child(puppet_entry)
	var display := CanvasLayer.new()
	add_child(display)
	var composite := rect(scene_view.get_texture())
	transition = ShaderMaterial.new()
	transition.shader = load("res://laser_transition.gdshader")
	transition.set_shader_parameter("incoming",puppet_view.get_texture())
	composite.material = transition
	display.add_child(composite)
	if ResourceLoader.exists("res://atmosphere.gd"):
		incoming_atmosphere=load("res://atmosphere.gd").new()
		incoming_atmosphere.particle_count=0
		incoming_atmosphere.name="IncomingWhiteFrame"
		display.add_child(incoming_atmosphere)

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--time="): fixed_time = float(arg.trim_prefix("--time="))
		if arg.begins_with("--start="): start_time = float(arg.trim_prefix("--start="))
		if arg.begins_with("--capture-fps="): capture_fps=float(arg.trim_prefix("--capture-fps="))
		if arg.begins_with("--silhouette-style="): silhouette_style = arg.trim_prefix("--silhouette-style=")
	make_room()
	make_photos()
	make_sms()
	make_canvas()
	update_scene(fixed_time if fixed_time >= 0 else start_time)
	print("CHORUS_PHONE_READY real_3d=true start=59.200 end=66.700")

func _process(delta: float) -> void:
	var elapsed:=float(capture_frame)/capture_fps if capture_fps>0.0 else clock
	var t := fixed_time if fixed_time >= 0 else start_time + elapsed
	update_scene(t)
	capture_frame+=1
	clock += delta

func content_time(actual_time: float) -> float:
	# Keep the flash/focus opening. Recover 0.12s from photo rotation/entry,
	# 0.18s from the room pass and 0.10s from the overlapping SMS drop.
	# Existing paths and easing are evaluated on their original phase clock.
	if actual_time < 0.70: return actual_time
	if actual_time < 2.43: return lerpf(0.70,2.55,unit(0.70,2.43,actual_time))
	if actual_time < 3.55: return lerpf(2.55,3.85,unit(2.43,3.55,actual_time))
	if actual_time < 4.55: return lerpf(3.85,4.95,unit(3.55,4.55,actual_time))
	return actual_time+0.40

func laser_recoil(age: float) -> Vector3:
	if age < 0 or age >= 0.30: return Vector3.ZERO
	var decay := exp(-age/0.10)*(1-smoothstep(0.18,0.30,age))
	# Subtle residual vibration, about15% of the previous translation amplitude.
	return Vector3((-4*exp(-age/0.055)+3*sin(TAU*11*age))*decay,
		2.5*sin(TAU*8*age)*decay,deg_to_rad(0.05)*sin(TAU*9*age)*decay)

func update_scene(actual_time: float) -> void:
	var t := content_time(actual_time)
	# The live room view already exists in the rotated card, beside the phone at desk height.
	var orbit := out_sine(unit(2.25,4.95,t))
	var angle := lerpf(-PI/4,0.60,orbit)
	phone.position = Vector3(0,0.512,0.60)
	phone.rotation = Vector3(deg_to_rad(30),-0.09,0)
	# Descend diagonally and move inward through the right arc, ending near
	# the call screen rather than keeping the camera at room-view height.
	var radius := lerpf(0.50,0.22,orbit)
	camera.position = phone.position+Vector3(sin(angle)*radius,lerpf(0.325,0.105,orbit),cos(angle)*radius)
	var room_glance := sin(PI*orbit)
	camera.look_at(phone.position+Vector3(-0.07*room_glance,0.008+0.025*room_glance,-0.07*room_glance))
	camera.fov = lerpf(55.0,48.0,orbit)
	focus.dof_blur_far_distance = lerpf(0.86,0.38,orbit)
	focus.dof_blur_far_transition = 0.35
	focus.dof_blur_amount = 0.045
	phone_point = camera.unproject_position(phone.to_global(Vector3(0,0.008,-0.045)))
	update_photos(t)
	photo_image.visible = t >= 0.23 and t < 2.58
	photo_image.modulate.a = 1
	# The second white flash reveals a soft photo field which settles into focus.
	photo_finish.set_shader_parameter("blur_px",24.0*(1-out_cubic(unit(0.25,0.70,t))))
	room_image.visible = t >= 2.55
	finish.set_shader_parameter("opacity",1.0)
	finish.set_shader_parameter("blocks",0.0)
	finish.set_shader_parameter("dots",0.0)
	finish.set_shader_parameter("pale",0.0)
	backdrop.visible = t < 0.23
	wash.visible = false
	bg_finish.set_shader_parameter("blur_px",0.0)
	bg_finish.set_shader_parameter("pale",0.0)
	sms_phone.position = Vector3(-0.47,sms_drop_y(t),0)
	sms_image.visible = t >= 3.85
	sms_finish.set_shader_parameter("silhouette",1.0 if t >= 4.95 else 0.0)
	blue_hold.visible = t >= 4.95
	var travel_time: float = silhouette_call.travel_time(t)
	var follow := in_out_cubic(unit(5.28,6.52,travel_time))
	# Pull in gently during the fastest pass without overtaking the final camera stop.
	var catch_up := unit(5.85,6.52,travel_time)
	follow += (1-follow)*0.28*pow(sin(PI*catch_up),2)
	var settle := unit(6.20,6.58,t)
	sms_image.position.x = -18000*follow-4*pow(sin(PI*settle),2)
	silhouette_call.position.x = sms_image.position.x
	silhouette_call.update_at(t,actual_time)
	# Two white flashes; cut to the already-tilted card under the second full-white peak.
	var first_flash := 1-out_cubic(unit(0.0,0.13,t))
	var second_flash := out_cubic(unit(0.14,0.18,t))*(1-out_cubic(unit(0.25,0.31,t)))
	flash.modulate.a = maxf(first_flash,second_flash)

	# The recovered 0.40s belongs to the laser, not an extra hold on the CG.
	# Cross the screen in 85ms, then give the cast shadow and whip room to read.
	# Wait 50ms longer behind the laser, preserving the final CG landing.
	var whip := unit(6.20,6.78,actual_time)
	var cut := smoothstep(6.47,6.71,actual_time)
	if is_instance_valid(incoming_atmosphere): incoming_atmosphere.update_at(actual_time+START-66.0,cut)
	var outgoing := pow(unit(6.20,6.59,actual_time),3)*0.88
	var incoming := 0.35*(1-out_cubic(unit(6.50,6.78,actual_time)))
	var blur := 160.0*sin(PI*whip)
	transition.set_shader_parameter("blend",cut)
	transition.set_shader_parameter("outgoing_shift",outgoing)
	transition.set_shader_parameter("incoming_shift",incoming)
	transition.set_shader_parameter("blur_px",maxf(blur,0.0))
	# Fire and breakthrough are separate impulses; only the outgoing shot recoils.
	var shock_age := actual_time-6.00
	var shock := laser_recoil(shock_age)+0.25*laser_recoil(shock_age-0.085)
	var punch := exp(-maxf(shock_age,0)/0.11) if shock_age >= 0 else 0.0
	transition.set_shader_parameter("shock_px",Vector2(shock.x,shock.y))
	transition.set_shader_parameter("shock_roll",shock.z)
	transition.set_shader_parameter("shock_zoom",1+0.0045*punch)
	if is_instance_valid(puppet_entry): puppet_entry.update_at(actual_time)
	if is_instance_valid(incoming_world):
		var incoming_time:=actual_time+START-66.0
		incoming_particles.update_at(incoming_time,1.0,false)
		var incoming_zoom:float=incoming_motion.zoom(incoming_time)
		incoming_world.scale=Vector2.ONE*incoming_zoom
		incoming_world.position=Vector2(960,540)-incoming_motion.center(incoming_time)*incoming_zoom
