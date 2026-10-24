extends SceneTree
## Bake the MCP-created skeleton into an editable geometric scene.
## East is +X, south/harbor is +Z. Distances are deliberately composed.

const BLUE = Color("549fc8")
const PINK = Color("ef628f")
const INK = Color("42555c")
const CREAM = Color("faf9f6")
const LAYOUT_SCALE = 1.0 # One unit is one metre for all city geometry.
var stage: Node3D
var mats: Dictionary = {}
var printed_mats: Dictionary = {}
var land_outline = PackedVector2Array()
var map_layout: Dictionary
var blue_samples = PackedVector3Array()
var red_samples = PackedVector3Array()
var building_count = 0
var rng = RandomNumberGenerator.new()

func _initialize() -> void:
	call_deferred("build")

func material(color: Color, unshaded: bool = false) -> StandardMaterial3D:
	var key = str(color) + str(unshaded)
	if not mats.has(key):
		var mat = StandardMaterial3D.new()
		mat.albedo_color = color
		mat.roughness = 1.0
		if unshaded:
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mats[key] = mat
	return mats[key]

func put(parent: Node, child: Node, node_name: String) -> Node:
	child.name = node_name
	parent.add_child(child)
	return child

func printed_material(color: Color) -> ShaderMaterial:
	var key = str(color)
	if not printed_mats.has(key):
		var mat = ShaderMaterial.new()
		mat.shader = load("res://printed_building.gdshader")
		mat.set_shader_parameter("paint_color", color)
		mat.set_shader_parameter("paper_texture", load("res://assets/paper-fiber.png"))
		printed_mats[key] = mat
	return printed_mats[key]

func box(parent: Node, node_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var instance = MeshInstance3D.new()
	var mesh = BoxMesh.new()
	mesh.size = size
	mesh.material = material(color)
	instance.mesh = mesh
	instance.position = pos
	put(parent, instance, node_name)
	return instance

func cylinder(parent: Node, node_name: String, pos: Vector3, radius: float, height: float, color: Color, top: float = -1.0) -> MeshInstance3D:
	var instance = MeshInstance3D.new()
	var mesh = CylinderMesh.new()
	mesh.bottom_radius = radius
	mesh.top_radius = radius if top < 0.0 else top
	mesh.height = height
	mesh.radial_segments = 16
	mesh.material = material(color)
	instance.mesh = mesh
	instance.position = pos
	put(parent, instance, node_name)
	return instance

func label(parent: Node, node_name: String, words: String, pos: Vector3, color: Color = INK, size: int = 48, pixel: float = 0.009) -> Label3D:
	var text = Label3D.new()
	text.text = words
	text.font_size = size
	text.pixel_size = pixel
	text.modulate = color
	text.outline_size = 8
	text.outline_modulate = CREAM
	text.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	text.position = pos
	text.no_depth_test = false
	put(parent, text, node_name)
	return text

func polygon(parent: Node, node_name: String, points: PackedVector2Array, y: float, color: Color) -> void:
	var triangles = Geometry2D.triangulate_polygon(points)
	var surface = SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for index in triangles:
		var p = points[index]
		surface.set_normal(Vector3.UP)
		surface.add_vertex(Vector3(p.x, y, p.y))
	var mesh = surface.commit()
	var instance = MeshInstance3D.new()
	instance.mesh = mesh
	var mat = material(color).duplicate()
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	instance.material_override = mat
	put(parent, instance, node_name)

func straight_curve(points: Array[Vector3]) -> Curve3D:
	var curve = Curve3D.new()
	curve.bake_interval = 1.0
	for point in points:
		curve.add_point(point)
	return curve

func ribbon(parent: Node, node_name: String, curve: Curve3D, width: float, color: Color) -> void:
	var surface = SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var sides: Array[Vector3] = []
	var distances: Array[float] = [0.0]
	for i in range(1, curve.point_count):
		distances.append(distances[-1] + curve.get_point_position(i - 1).distance_to(curve.get_point_position(i)))
	for i in range(curve.point_count):
		var point = curve.get_point_position(i)
		var before = (point - curve.get_point_position(maxi(0, i - 1))).normalized()
		var after = (curve.get_point_position(mini(curve.point_count - 1, i + 1)) - point).normalized()
		if i == 0:
			before = after
		if i == curve.point_count - 1:
			after = before
		var normal = after.cross(Vector3.UP)
		var miter = (before.cross(Vector3.UP) + normal).normalized()
		sides.append(miter * width * 0.5 / maxf(0.2, miter.dot(normal)))
	for i in range(curve.point_count - 1):
		var a = curve.get_point_position(i)
		var b = curve.get_point_position(i + 1)
		var side_a = sides[i]
		var side_b = sides[i + 1]
		var vertices = [a - side_a, a + side_a, b + side_b, a - side_a, b + side_b, b - side_b]
		var uv_distances = [distances[i], distances[i], distances[i + 1], distances[i], distances[i + 1], distances[i + 1]]
		for j in range(vertices.size()):
			surface.set_normal(Vector3.UP)
			surface.set_uv(Vector2(uv_distances[j] / distances[-1], 0.0))
			surface.add_vertex(vertices[j])
	var instance = MeshInstance3D.new()
	instance.mesh = surface.commit()
	var mat = material(color, true).duplicate()
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	instance.material_override = mat
	if node_name.ends_with("MapRibbon"):
		var route_material = ShaderMaterial.new()
		route_material.shader = load("res://route_reveal.gdshader")
		route_material.set_shader_parameter("route_color", color)
		route_material.set_shader_parameter("reveal", 1.0)
		instance.material_override = route_material
	put(parent, instance, node_name)

func segment(parent: Node, node_name: String, a: Vector3, b: Vector3, width: float, color: Color) -> void:
	var curve = Curve3D.new()
	curve.add_point(a)
	curve.add_point(b)
	ribbon(parent, node_name, curve, width, color)

func station(parent: Node, node_name: String, point: Vector3, color: Color, code: String) -> void:
	var path: Curve3D = parent.get_node("AiPath" if node_name.begins_with("Blue") else "RenPath").curve
	var progress = path.get_closest_offset(point) / path.get_baked_length()
	for node in [cylinder(parent, node_name + "Rim", point + Vector3(0, 0.1, 0), 7, 0.15, color),
		cylinder(parent, node_name + "Core", point + Vector3(0, 0.20, 0), 4, 0.04, CREAM)]:
		node.set_meta("route_progress", progress)
	# Points indicate story beats rather than a strict subway station chart.

func pawn(parent: Node, node_name: String, point: Vector3, color: Color, words: String) -> void:
	var group = Node3D.new()
	put(parent, group, node_name)
	group.position = point
	group.scale = Vector3.ONE * 20.0 # Screen-readable map icon, hidden in city view.
	cylinder(group, "Foot", Vector3(0, 0.06, 0), 0.58, 0.12, color)
	cylinder(group, "Body", Vector3(0, 0.65, 0), 0.35, 0.95, color, 0.19)
	var head = MeshInstance3D.new()
	var sphere = SphereMesh.new()
	sphere.radius = 0.28
	sphere.height = 0.56
	sphere.radial_segments = 16
	sphere.rings = 8
	sphere.material = material(CREAM)
	head.mesh = sphere
	head.position = Vector3(0, 1.38, 0)
	put(group, head, "Head")
	label(group, "Name", words, Vector3(0, 2.35, 0), INK, 56, 0.020)

func anchor(key: String) -> Vector3:
	var point: Array = map_layout.anchors[key]
	return Vector3(point[0], 0, point[1])

func build_ground() -> void:
	var ground = stage.get_node("MapGround")
	map_layout = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world-map.json"))
	for point in map_layout.land:
		land_outline.append(Vector2(point[0], point[1]))
	# A flat, large map surface replaces the small finite model board.
	var floor = MeshInstance3D.new()
	var plane = PlaneMesh.new()
	plane.size = Vector2(2200, 1600)
	var surface_material = material(Color.WHITE, true).duplicate()
	surface_material.albedo_texture = load("res://assets/map-surface.png")
	surface_material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	plane.material = surface_material
	floor.mesh = plane
	put(ground, floor, "StreetMapSurface")
	var distant_floor = MeshInstance3D.new()
	var distant_plane = PlaneMesh.new()
	distant_plane.size = Vector2(16000, 16000)
	var horizon_material = ShaderMaterial.new()
	horizon_material.shader = load("res://paper_horizon.gdshader")
	horizon_material.set_shader_parameter("paper_texture", load("res://assets/paper-fiber.png"))
	distant_plane.material = horizon_material
	distant_floor.mesh = distant_plane
	distant_floor.position.y = -0.01
	put(ground, distant_floor, "HorizonGround")
	box(ground, "HarborWalk", anchor("kamome") + Vector3(0, 0.025, 12), Vector3(120, 0.05, 30), Color("e4d6be"))
	var annotations = Node3D.new()
	put(ground, annotations, "MapAnnotations")
	for entry in [["jr", "JR KOBE", INK], ["kumo", "KUMO / SHRINE", Color("809e8a")],
		["kamome", "KAMOME / HARBOR", Color("bb986b")], ["shiori", "SHIORI / HOME*", Color("a897b7")],
		["hiiro", "HIIRO / HOME*", Color("b98c79")], ["ai", "AI", BLUE], ["ren", "REN", PINK]]:
		var pin = Node3D.new()
		put(annotations, pin, entry[0])
		pin.position = anchor(entry[0])
		cylinder(pin, "Dot", Vector3(0, 0.1, 0), 8, 0.15, entry[2])
		var title = label(pin, "Title", entry[1], Vector3(0, 25, 0), INK, 48, 0.38)
		title.no_depth_test = true

func build_routes() -> void:
	var routes = stage.get_node("Routes")
	var blue_points: Array[Vector3] = []
	var red_points: Array[Vector3] = []
	for point in map_layout.blue:
		blue_points.append(Vector3(point[0], 0.025, point[1]))
	for point in map_layout.pink:
		red_points.append(Vector3(point[0], 0.025, point[1]))
	for entry in [["AiPath", blue_points, BLUE], ["RenPath", red_points, PINK]]:
		var path = Path3D.new()
		var points: Array[Vector3] = entry[1]
		for i in range(points.size()):
			points[i].y = 0.025
		path.curve = straight_curve(points)
		put(routes, path, entry[0])
		if entry[0] == "AiPath":
			var street = path.curve.duplicate(true)
			for i in range(street.point_count):
				var point = street.get_point_position(i)
				point.y = 0.004
				street.set_point_position(i, point)
			ribbon(routes, "DriveStreetCasing", street, 16.0, Color("d9dee3"))
			for i in range(street.point_count):
				var point = street.get_point_position(i)
				point.y = 0.007
				street.set_point_position(i, point)
			ribbon(routes, "DriveStreet", street, 14.0, Color("ffffff"))
		ribbon(routes, entry[0] + "Ribbon", path.curve, 1.8, entry[2])
		var map_curve = path.curve.duplicate(true)
		for i in range(map_curve.point_count):
			var point = map_curve.get_point_position(i)
			point.y = 0.035
			map_curve.set_point_position(i, point)
		ribbon(routes, entry[0] + "MapRibbon", map_curve, 5.5, entry[2])
	station(routes, "BlueStart", anchor("ai"), BLUE, "")
	station(routes, "BlueCity", Vector3(-320, 0.08, 145), BLUE, "")
	station(routes, "BlueJoin", Vector3(520, 0.08, -80), BLUE, "")
	station(routes, "PinkStart", anchor("ren"), PINK, "")
	station(routes, "PinkCity", Vector3(-280, 0.08, -230), PINK, "")
	station(routes, "PinkJoin", Vector3(520, 0.08, -170), PINK, "")
	for i in range(7):
		segment(routes, "WalkingLink" + str(i), Vector3(520, 0.09, -165 + i * 12), Vector3(520, 0.09, -158 + i * 12), 1.2, INK)
	label(routes, "SannomiyaTitle", "MEETING POINT", Vector3(630, 70, -100), INK, 48, 0.30)

func add_building(point: Vector3, width: float, depth: float, height: float, color_index: int) -> void:
	var buildings = stage.get_node("Buildings")
	var colors = [Color("c4d5d9"), Color("d1cbdc"), Color("ddcfb5"), Color("cbd9c4"), Color("c4cbd1")]
	var block = Node3D.new()
	put(buildings, block, "Block%03d" % building_count)
	block.position = point
	var color: Color = colors[color_index]
	box(block, "Volume", Vector3(0, height * 0.5 + 0.006, 0), Vector3(width, height, depth), color)
	box(block, "Roof", Vector3(0, height + 0.045, 0), Vector3(width, 0.09, depth), color.darkened(0.07))
	if building_count % 3 == 0:
		for stripe in range(2):
			box(block, "Band" + str(stripe), Vector3(-width * 0.22 + stripe * width * 0.44, height * 0.5, depth * 0.5 + 0.03), Vector3(width * 0.07, height * 0.90, 0.04), color.darkened(0.17))
	for part in block.get_children():
		var original_material = part.mesh.surface_get_material(0)
		part.material_override = printed_material(original_material.albedo_color)
	var closest_index = 0
	var closest = INF
	for i in range(blue_samples.size()):
		var distance = point.distance_squared_to(blue_samples[i])
		if distance < closest:
			closest = distance
			closest_index = i
	var route_fraction = float(closest_index) / maxf(1, blue_samples.size() - 1)
	# Lead the short camera journey by several seconds, on the same metre scale.
	block.set_meta("rise_fraction", maxf(-0.025, (route_fraction - 0.04) / 0.085 * 0.52 - 0.07) + rng.randf_range(0, 0.004))
	# Keep a real skyline ahead: distant neighborhoods are established at entry.
	if route_fraction > 0.125 or closest > 3600.0:
		block.set_meta("rise_fraction", -0.03)
	block.scale.y = 1.0
	building_count += 1

func build_buildings() -> void:
	rng.seed = 27140
	var curve: Curve3D = stage.get_node("Routes/AiPath").curve
	blue_samples = curve.get_baked_points()
	red_samples = stage.get_node("Routes/RenPath").curve.get_baked_points()
	# The texture and 3D volumes use exactly the same street-facing parcels.
	for footprint in map_layout.buildings:
		add_building(Vector3(footprint.x, 0, footprint.z), footprint.width, footprint.depth, footprint.height, footprint.color)
	print("Generated varied street-facing building blocks: ", building_count)

func build_landmarks() -> void:
	var landmarks = stage.get_node("Landmarks")
	var jr = Node3D.new()
	put(landmarks, jr, "JRKobe")
	jr.position = anchor("jr")
	jr.scale = Vector3.ONE * 8
	box(jr, "Station", Vector3(0, 0.33, 0), Vector3(6.2, 0.6, 0.82), Color("e3ca91"))
	box(jr, "Canopy", Vector3(0, 0.69, 0), Vector3(6.6, 0.16, 1.12), CREAM)
	label(jr, "Title", "JR KOBE", Vector3(0, 2.8, -0.1), INK, 64, 0.035)
	var shrine = Node3D.new()
	put(landmarks, shrine, "IkutaShrine")
	shrine.position = anchor("shrine")
	shrine.scale = Vector3.ONE * 6
	box(shrine, "Garden", Vector3(0, 0.03, 0), Vector3(4.0, 0.08, 2.5), Color("cdddc9"))
	for x in [-0.7, 0.7]:
		box(shrine, "ToriiPillar" + str(x), Vector3(x, 0.6, 0.65), Vector3(0.15, 1.2, 0.15), Color("cb7770"))
	box(shrine, "ToriiTop", Vector3(0, 1.23, 0.65), Vector3(1.95, 0.20, 0.27), Color("cb7770"))
	box(shrine, "Sanctuary", Vector3(0, 0.43, -0.4), Vector3(1.55, 0.8, 0.92), Color("e4d7c3"))
	box(shrine, "Roof", Vector3(0, 0.92, -0.4), Vector3(1.85, 0.18, 1.18), Color("8c9d93"))
	var home = Node3D.new()
	put(landmarks, home, "ShioriHome")
	home.position = anchor("shiori_home")
	home.scale = Vector3.ONE * 6
	box(home, "Garden", Vector3(0, 0.04, 0), Vector3(3.9, 0.12, 2.8), Color("dce1c6"))
	box(home, "House", Vector3(0, 0.52, -0.2), Vector3(2.0, 0.9, 1.2), Color("e1d9df"))
	box(home, "Roof", Vector3(0, 1.06, -0.2), Vector3(2.22, 0.2, 1.38), Color("b8afc4"))
	for x in [-1.7, 1.7]:
		box(home, "Gate" + str(x), Vector3(x, 0.28, 1.2), Vector3(0.28, 0.55, 0.26), Color("b7b5bd"))
	var new_home = Node3D.new()
	put(landmarks, new_home, "HiiroHome")
	new_home.position = anchor("hiiro_home")
	new_home.scale = Vector3.ONE * 6
	box(new_home, "House", Vector3(0, 0.5, 0), Vector3(1.65, 1, 1.45), Color("e4d4c0"))
	box(new_home, "Roof", Vector3(0, 1.06, 0), Vector3(1.90, 0.16, 1.7), Color("c7b18c"))
	box(new_home, "Door", Vector3(0.35, 0.3, 0.735), Vector3(0.32, 0.6, 0.03), Color("9bafb4"))
	var port = Node3D.new()
	put(landmarks, port, "PortSilhouette")
	port.position = anchor("port")
	port.scale = Vector3.ONE * 18
	cylinder(port, "TowerFoot", Vector3(0, 0.45, 0), 0.62, 0.9, Color("bd7774"), 0.28)
	cylinder(port, "TowerStem", Vector3(0, 1.85, 0), 0.28, 2, Color("bd7774"), 0.54)
	cylinder(port, "TowerCap", Vector3(0, 3.0, 0), 0.62, 0.25, Color("d1b18c"))

func build_characters() -> void:
	var actors = stage.get_node("Characters")
	pawn(actors, "Ai", anchor("ai"), BLUE, "AI")
	pawn(actors, "Ren", anchor("ren"), PINK, "REN")
	pawn(actors, "Kumo", anchor("kumo"), Color("809e8a"), "KUMO\nIKUTA SHRINE")
	pawn(actors, "Kamome", anchor("kamome"), Color("bb986b"), "KAMOME\nHARBOR WALK")
	pawn(actors, "Shiori", anchor("shiori"), Color("a897b7"), "SHIORI\nHOME*")
	pawn(actors, "Hiiro", anchor("hiiro"), Color("b98c79"), "HIIRO\nHOME*")

func build_lighting() -> void:
	var world = WorldEnvironment.new()
	var environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	var paper_sky = Sky.new()
	var sky_material = ShaderMaterial.new()
	sky_material.shader = load("res://paper_sky.gdshader")
	sky_material.set_shader_parameter("paper_texture", load("res://assets/paper-fiber.png"))
	paper_sky.sky_material = sky_material
	environment.sky = paper_sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = CREAM
	environment.ambient_light_energy = 0.5
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = environment
	put(stage, world, "WorldEnvironment")
	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -28, 0)
	sun.light_color = Color("fff1dd")
	sun.light_energy = 0.55
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 450.0
	put(stage, sun, "Sun")

func set_owners(node: Node) -> void:
	for child in node.get_children():
		child.owner = stage
		set_owners(child)

func build() -> void:
	stage = load("res://main.tscn").instantiate()
	stage.name = "KobeSequence"
	# Retain the six groups established through Godot MCP, rebuilding contents.
	for child in stage.get_children():
		if child.name in ["MapGround", "Routes", "Buildings", "Landmarks", "Characters", "CameraRig"]:
			child.scale = Vector3.ONE if child.name == "CameraRig" else Vector3.ONE * LAYOUT_SCALE
			for item in child.get_children():
				child.remove_child(item)
				item.free()
		else:
			stage.remove_child(child)
			child.free()
	build_ground()
	build_routes()
	build_buildings()
	build_landmarks()
	build_characters()
	build_lighting()
	var camera = Camera3D.new()
	camera.current = true
	camera.fov = 46.0
	camera.near = 0.08
	camera.far = 6500.0
	camera.position = Vector3(530, 394, 942)
	# The initial editor view already shows the composed map.
	camera.rotation_degrees = Vector3(-20, 26, 0)
	put(stage.get_node("CameraRig"), camera, "ViewCamera")
	var controller = load("res://scene_controller.gd")
	if controller == null or not controller.can_instantiate():
		push_error("Scene controller failed to load")
		stage.free()
		quit(1)
		return
	stage.set_script(controller)
	set_owners(stage)
	var packed = PackedScene.new()
	var pack_error = packed.pack(stage)
	if pack_error != OK:
		push_error("Could not pack map scene: " + str(pack_error))
		quit(1)
		return
	var save_error = ResourceSaver.save(packed, "res://main.tscn")
	print("Editable Kobe scene saved: ", save_error, "; nodes=", stage.find_children("*", "", true, false).size())
	stage.free()
	quit(0 if save_error == OK else 1)
