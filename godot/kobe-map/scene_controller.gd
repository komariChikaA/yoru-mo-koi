extends Node3D
## Song timing: 26.60s overhead entry, 27.5s route, 34s top map, 37s low oblique, 40s CG bridge.
## Five supplied SD cards replace their existing geometric actor placeholders.

@export var bridge_show_lyrics: bool = true
@export var default_view: String = "oblique"
@export var show_preview_controls: bool = true
@export_range(0.6, 1.6, 0.01) var driving_height: float = 1.0
@onready var camera: Camera3D = $CameraRig/ViewCamera
@onready var blue_path: Curve3D = $Routes/AiPath.curve
@onready var red_path: Curve3D = $Routes/RenPath.curve
var view = "oblique"
var touring = false
var clock = 0.0
var yaw = 0.38
var elevation = asin(LOW_CAMERA_HEIGHT / LOW_CAMERA_RADIUS)
var radius = LOW_CAMERA_RADIUS
var capture_time = -1.0
var rendering_movie = false
var status: Label
var entry_transition: Node3D
var bridge_panel: Control
var bridge_flash: ColorRect
var bridge_scene: Control
var building_blocks: Array[Node] = []
var drive_segments: Array[Dictionary] = []
var printed_materials: Array[ShaderMaterial] = []
var building_rise_times: Array[float] = []
var building_burial_depths: Array[float] = []
var map_surface_material: ShaderMaterial
var map_callouts: Control
var ren_focus_material: ShaderMaterial
var ren_focus_ring: MeshInstance3D
const MAP_CENTER = Vector3(60, 0, -30)
const MAP_TOP = Vector3(35, 860, -45)
const MAP_DRIFT = Vector3(55, 0, -15)
const MAP_YAW = -0.18
const SONG_START = 27.5
const ENTRY_BEGIN = -0.90 # song 26.60: start before outgoing station rings appear
const ENTRY_HEIGHT = 30.0
const CITY_END = 6.5 # song 34.0: begin the gentle curved lift
const LIFT_END = 8.3 # song 35.8: settle into the angled, drifting top view
const ROUTE_BEGIN = 7.65 # song 35.15: draw during the final lift
const ROUTE_END = 9.1 # song 36.6: finish both routes
const MAP_END = 9.5 # song 37.0: flat effects finished
const TILT_END = 10.35 # song 37.85: settle into the close tabletop angle
const LOW_CAMERA_HEIGHT = 200.0
const LOW_CAMERA_RADIUS = 600.0
const LOW_CAMERA_FOV = 90.0
const SD_CARD_HEIGHT = 9.0 # Nearest card occupies about 280px in the 1080p low shot.
const LOW_CAMERA_TARGET = Vector3(135, 18, -30)
const OBLIQUE_BUILDING_HEIGHT = 0.22
const BUILDING_RISE_SECONDS = 0.85
const BUILDING_ROADSIDE_DISTANCE = 55.0 # Clearance from the facade, not the parcel centre.
const FIRST_ORBIT_END = 11.4 # song 38.900: finish the first turn and hold
const SECOND_ORBIT_STRENGTH = 0.5 # Half of the previous right turn and radial travel.
const SECOND_ORBIT_BEGIN = 11.7 # song 39.200: begin the rightward return
const SECOND_ORBIT_END = 12.0 # song 39.500: finish the main turn before peak white
const ORBIT_END = 11.85 # song 39.35: brighten into the white-light transition
const FLASH_PEAK_BEGIN = 12.12 # song 39.62: fully white
const FLASH_SWITCH = 12.16 # song 39.66: replace the scene while fully white
const FLASH_PEAK_END = 12.20 # song 39.70: begin revealing the next scene
const TOUR_END = 12.5 # song 40.0: CG fully in frame
const BRIDGE_END = 25.76 # song 53.26: hand illustration yields to chorus sky
const DRIVE_START = 0.04
const DRIVE_END = 0.125

func _ready() -> void:
	view = default_view
	if OS.get_cmdline_user_args().has("--buildings=simple"):
		load("res://simple_building_trial.gd").apply(self)
	building_blocks = $Buildings.get_children()
	for mesh in $Buildings.find_children("*", "MeshInstance3D", true, false):
		if mesh.material_override is ShaderMaterial and not printed_materials.has(mesh.material_override):
			printed_materials.append(mesh.material_override)
	prepare_map_readability()
	prepare_metro_routes()
	prepare_drive_segments()
	prepare_building_growth()
	attach_sd_cards()
	prepare_ren_focus()
	var name_font: Font = load("res://assets/fonts/seurat-character-names.otf")
	var names = {"Hiiro": "姫色", "Ren": "恋", "Kumo": "雲", "Kamome": "かもめ", "Shiori": "紫織", "Ai": "藍"}
	for actor in $Characters.get_children():
		var title: Label3D = actor.get_node("Name")
		title.text = names[String(actor.name)]
		title.font = name_font
		title.font_size = 64
		title.pixel_size = 0.024
		title.position.y = SD_CARD_HEIGHT + 1.1
		if actor.name == "Ai":
			title.position.y = 2.6
			title.font_size = 52
			title.pixel_size = 0.020
	for argument in OS.get_cmdline_user_args():
		if argument == "--render":
			rendering_movie = true
			get_tree().auto_accept_quit = false
		elif argument == "--tour":
			touring = true
		elif argument.begins_with("--view="):
			view = argument.trim_prefix("--view=")
		elif argument.begins_with("--time="):
			capture_time = argument.trim_prefix("--time=").to_float()
		elif argument.begins_with("--tour-start="):
			clock = argument.trim_prefix("--tour-start=").to_float()
		elif argument == "--no-hud":
			show_preview_controls = false
	make_hud()
	make_transitions()
	make_entry_plane()
	apply_view(clock)
	print("KOBE_SCENE_READY nodes=", find_children("*", "", true, false).size(), " view=", view, " tour=", touring)
	print("CITY_CAMERA metres_per_unit=1 ground_offset=", driving_height, " route_metres=", blue_path.get_baked_length(), " drive_metres=", blue_path.get_baked_length() * (DRIVE_END - DRIVE_START), " buildings=", building_blocks.size())

func prepare_map_readability() -> void:
	map_surface_material = ShaderMaterial.new()
	map_surface_material.shader = load("res://map_surface.gdshader")
	map_surface_material.set_shader_parameter("street_texture", load("res://assets/map-surface.png"))
	map_surface_material.set_shader_parameter("overview_texture", load("res://assets/map-overview.png"))
	$MapGround/StreetMapSurface.material_override = map_surface_material
	var layer = CanvasLayer.new()
	layer.layer = 2
	add_child(layer)
	map_callouts = Control.new()
	map_callouts.set_script(load("res://map_callouts.gd"))
	layer.add_child(map_callouts)
	map_callouts.setup(camera, $MapGround/MapAnnotations)
	$Routes/SannomiyaTitle.font = load("res://assets/fonts/fz-shaoer-map.ttf")

func emphasize_map(amount: float) -> void:
	map_surface_material.set_shader_parameter("map_emphasis", amount)
	for mat in printed_materials:
		mat.set_shader_parameter("map_fade", amount * 0.90)

func metro_ribbon_mesh(points: Array[Vector3], width: float) -> ArrayMesh:
	var surface = SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var distances: Array[float] = [0.0]
	var sides: Array[Vector3] = []
	for i in range(1, points.size()):
		distances.append(distances[-1] + points[i - 1].distance_to(points[i]))
	for i in range(points.size()):
		var before = (points[i] - points[maxi(0, i - 1)]).normalized()
		var after = (points[mini(points.size() - 1, i + 1)] - points[i]).normalized()
		if i == 0:
			before = after
		if i == points.size() - 1:
			after = before
		var normal = after.cross(Vector3.UP)
		var miter = (before.cross(Vector3.UP) + normal).normalized()
		sides.append(miter * width * 0.5 / maxf(0.2, miter.dot(normal)))
	for i in range(points.size() - 1):
		var vertices = [points[i] - sides[i], points[i] + sides[i], points[i + 1] + sides[i + 1], points[i] - sides[i], points[i + 1] + sides[i + 1], points[i + 1] - sides[i + 1]]
		var offsets = [distances[i], distances[i], distances[i + 1], distances[i], distances[i + 1], distances[i + 1]]
		for j in range(6):
			surface.set_normal(Vector3.UP)
			surface.set_uv(Vector2(offsets[j] / distances[-1], 0))
			surface.add_vertex(vertices[j])
	return surface.commit()

func prepare_metro_routes() -> void:
	# Only the map ribbons change; driving and actor movement keep their original paths.
	for entry in [["AiPath", "Blue", blue_path, Color("248cbe")], ["RenPath", "Pink", red_path, Color("e45189")]]:
		var path: Curve3D = entry[2]
		var points: Array[Vector3] = [path.get_point_position(0)]
		for i in range(1, path.point_count - 1):
			var corner = path.get_point_position(i)
			var before = path.get_point_position(i - 1)
			var after = path.get_point_position(i + 1)
			var radius = minf(20.0, minf(corner.distance_to(before), corner.distance_to(after)) * 0.3)
			var a = corner + (before - corner).normalized() * radius
			var b = corner + (after - corner).normalized() * radius
			points.append(a)
			for step in range(1, 9):
				var t = float(step) / 8.0
				points.append(a.lerp(corner, t).lerp(corner.lerp(b, t), t))
		points.append(path.get_point_position(path.point_count - 1))
		var ink: MeshInstance3D = $Routes.get_node(entry[0] + "MapRibbon")
		ink.mesh = metro_ribbon_mesh(points, 10.0)
		ink.position.y = 0.06
		ink.material_override.set_shader_parameter("route_color", entry[3])
		var casing = MeshInstance3D.new()
		casing.name = entry[0] + "CasingMapRibbon"
		casing.mesh = metro_ribbon_mesh(points, 16.0)
		casing.position.y = 0.04
		casing.material_override = ink.material_override.duplicate()
		casing.material_override.set_shader_parameter("route_color", Color.WHITE)
		$Routes.add_child(casing)
		# White-centred rings, including a larger terminal at either end.
		for station_name in ["Start", "City", "Join"]:
			var rim: MeshInstance3D = $Routes.get_node(entry[1] + station_name + "Rim")
			var core: MeshInstance3D = $Routes.get_node(entry[1] + station_name + "Core")
			var terminal = station_name != "City"
			var offset = 0.0 if station_name == "Start" else path.get_baked_length() if station_name == "Join" else path.get_closest_offset(rim.position)
			var point = path.sample_baked(offset)
			for part in [rim, core]:
				part.mesh = part.mesh.duplicate(true)
				part.mesh.radial_segments = 48
				var radius = (17.0 if terminal else 12.0) if part == rim else (11.0 if terminal else 7.5)
				part.mesh.top_radius = radius
				part.mesh.bottom_radius = radius
				part.mesh.material.albedo_color = entry[3] if part == rim else Color.WHITE
				part.position = point + Vector3(0, 0.16 if part == rim else 0.27, 0)
				part.set_meta("route_progress", offset / path.get_baked_length())
		for fraction in [0.16, 0.52, 0.75]:
			for outer in [true, false]:
				var marker = MeshInstance3D.new()
				marker.name = entry[1] + "Stop" + str(int(fraction * 100)) + ("Rim" if outer else "Core")
				var disk = CylinderMesh.new()
				disk.top_radius = 12.0 if outer else 7.5
				disk.bottom_radius = disk.top_radius
				disk.height = 0.08
				disk.radial_segments = 48
				var mat = StandardMaterial3D.new()
				mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				mat.albedo_color = entry[3] if outer else Color.WHITE
				disk.material = mat
				marker.mesh = disk
				marker.position = path.sample_baked(path.get_baked_length() * fraction) + Vector3(0, 0.16 if outer else 0.27, 0)
				marker.set_meta("route_progress", fraction)
				$Routes.add_child(marker)

func attach_sd_cards() -> void:
	for actor_name in ["Hiiro", "Ren", "Kumo", "Kamome", "Shiori"]:
		var actor = $Characters.get_node(actor_name)
		var texture: Texture2D = load("res://assets/sd/" + actor_name.to_lower() + ".png")
		var bounds = texture.get_image().get_used_rect()
		var card = Sprite3D.new()
		card.name = "SDCard"
		card.texture = texture
		# Enlarge the silhouette, while keeping its alpha bottom at the original feet.
		card.pixel_size = SD_CARD_HEIGHT / float(bounds.size.y)
		card.position.y = (float(bounds.end.y) - texture.get_height() * 0.5) * card.pixel_size
		card.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
		card.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		card.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
		card.alpha_scissor_threshold = 0.15
		card.shaded = false
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for part in actor.get_children():
			if part is MeshInstance3D:
				part.visible = false
		actor.add_child(card)
		var actor_label = actor.get_node("Name")
		actor_label.position.y = maxf(actor_label.position.y, SD_CARD_HEIGHT + 1.5)
		if actor_name == "Hiiro":
			actor_label.position.y = SD_CARD_HEIGHT + 2.6 # Keep the far-right name above the card.

func prepare_ren_focus() -> void:
	var card: Sprite3D = $Characters/Ren/SDCard
	ren_focus_material = ShaderMaterial.new()
	ren_focus_material.shader = load("res://sd_focus.gdshader")
	ren_focus_material.set_shader_parameter("character_texture", card.texture)
	card.material_override = ren_focus_material
	ren_focus_ring = MeshInstance3D.new()
	ren_focus_ring.name = "FocusRing"
	var ring = TorusMesh.new()
	ring.inner_radius = 2.85
	ring.outer_radius = 3.05
	ring.rings = 64
	ring.ring_segments = 12
	var mat = StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color("f49abe")
	ring.material = mat
	ren_focus_ring.mesh = ring
	ren_focus_ring.position.y = 0.12
	ren_focus_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	$Characters/Ren.add_child(ren_focus_ring)

func pose_ren_focus(time: float) -> void:
	var focus = smoothstep01((time - 10.5) / 0.14) * (1.0 - smoothstep01((time - 11.35) / 0.20))
	ren_focus_material.set_shader_parameter("highlight", focus)
	ren_focus_material.set_shader_parameter("spin", TAU * smootherstep01((time - 10.65) / 0.70))
	ren_focus_ring.visible = focus > 0.001
	ren_focus_ring.mesh.material.albedo_color.a = focus * 0.85
	ren_focus_ring.scale = Vector3.ONE * (1.0 + 0.10 * sin(clampf((time - 10.5) / 1.05, 0.0, 1.0) * PI))
	$Characters/Ren/Name.modulate = Color("42555c").lerp(Color("e45189"), focus)

func make_hud() -> void:
	var layer = CanvasLayer.new()
	add_child(layer)
	var title = Label.new()
	title.text = "KOBE / GEOMETRIC ROUTE STUDY"
	title.position = Vector2(48, 34)
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", Color("42555c"))
	layer.add_child(title)
	status = Label.new()
	status.position = Vector2(48, 72)
	status.add_theme_font_size_override("font_size", 20)
	status.add_theme_color_override("font_color", Color("728285"))
	layer.add_child(status)
	var controls = Label.new()
	controls.text = "1 CITY   2 MAP   3 OBLIQUE   4 ORBIT   SPACE TOUR   DRAG ORBIT   WHEEL ZOOM"
	controls.position = Vector2(48, 1010)
	controls.add_theme_font_size_override("font_size", 19)
	controls.add_theme_color_override("font_color", Color("728285"))
	layer.add_child(controls)
	var note = Label.new()
	note.text = "* Homes are proposed placements.   Markers are SD placeholders."
	note.position = Vector2(48, 1040)
	note.add_theme_font_size_override("font_size", 17)
	note.add_theme_color_override("font_color", Color("8d9795"))
	layer.add_child(note)
	layer.visible = show_preview_controls

func make_transitions() -> void:
	var layer = CanvasLayer.new()
	layer.layer = 10
	add_child(layer)
	bridge_panel = Control.new()
	bridge_panel.size = Vector2(1920, 1080)
	bridge_panel.clip_contents = true
	bridge_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bridge_panel.visible = false
	layer.add_child(bridge_panel)
	bridge_scene = Control.new()
	bridge_scene.set_script(load("res://bridge_scene.gd"))
	bridge_scene.show_lyrics = bridge_show_lyrics
	bridge_panel.add_child(bridge_scene)

	bridge_flash = ColorRect.new()
	bridge_flash.size = Vector2(1920, 1080)
	bridge_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bridge_flash.visible = false
	var flash_material = ShaderMaterial.new()
	flash_material.shader = load("res://white_flash.gdshader")
	bridge_flash.material = flash_material
	layer.add_child(bridge_flash)

func pose_bridge(time: float) -> void:
	bridge_panel.visible = time >= FLASH_SWITCH
	bridge_scene.pose(SONG_START + time)
	var strength = 0.0
	if time < FLASH_PEAK_BEGIN:
		strength = smoothstep01((time - ORBIT_END) / (FLASH_PEAK_BEGIN - ORBIT_END))
	elif time <= FLASH_PEAK_END:
		strength = 1.0
	else:
		strength = 1.0 - smoothstep01((time - FLASH_PEAK_END) / (TOUR_END - FLASH_PEAK_END))
	bridge_flash.visible = strength > 0.0
	bridge_flash.material.set_shader_parameter("strength", strength)

func _process(delta: float) -> void:
	clock += delta
	# Advance by Movie Maker's fixed delta, keeping the grain repeatable in exports.
	for mat in printed_materials:
		mat.set_shader_parameter("texture_clock", clock)
	apply_view(clock)

func smoothstep01(value: float) -> float:
	var t = clampf(value, 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)

func smootherstep01(value: float) -> float:
	var t = clampf(value, 0.0, 1.0)
	return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

func oblique_position(angle: float, height_angle: float = asin(LOW_CAMERA_HEIGHT / LOW_CAMERA_RADIUS), distance: float = LOW_CAMERA_RADIUS) -> Vector3:
	return Vector3(sin(angle) * cos(height_angle), sin(height_angle), cos(angle) * cos(height_angle)) * distance + MAP_CENTER

func prepare_drive_segments() -> void:
	var start = blue_path.get_baked_length() * DRIVE_START
	var end = blue_path.get_baked_length() * DRIVE_END
	var turn_duration = 0.28 / CITY_END
	var turn_count = 0
	var corner_distance = 0.0
	for i in range(1, blue_path.point_count - 1):
		corner_distance += blue_path.get_point_position(i - 1).distance_to(blue_path.get_point_position(i))
		if corner_distance > start and corner_distance < end:
			turn_count += 1
	var travel_budget = 1.0 - turn_count * turn_duration
	var distance = 0.0
	for i in range(blue_path.point_count - 1):
		var a = blue_path.get_point_position(i)
		var b = blue_path.get_point_position(i + 1)
		var segment_end = distance + a.distance_to(b)
		var travel_start = maxf(start, distance)
		var travel_end = minf(end, segment_end)
		var heading = (b - a).normalized()
		if travel_end > travel_start:
			drive_segments.append({"turn": false, "start": travel_start, "end": travel_end,
				"heading": heading, "duration": (travel_end - travel_start) / (end - start) * travel_budget})
		if segment_end > start and segment_end < end and i < blue_path.point_count - 2:
			var next = (blue_path.get_point_position(i + 2) - b).normalized()
			drive_segments.append({"turn": true, "start": segment_end, "heading": heading,
				"next": next, "duration": turn_duration})
		distance = segment_end

func drive_pose(city_time: float) -> Dictionary:
	var remaining = clampf(city_time, 0.0, 1.0)
	var pose: Dictionary = {}
	for segment_value in drive_segments:
		var amount = clampf(remaining / float(segment_value.duration), 0.0, 1.0)
		var heading: Vector3 = segment_value.heading
		var distance: float = segment_value.start
		if segment_value.turn:
			var next: Vector3 = segment_value.next
			var angle = lerp_angle(atan2(heading.x, heading.z), atan2(next.x, next.z), smoothstep01(amount))
			heading = Vector3(sin(angle), 0, cos(angle))
		else:
			distance = lerpf(segment_value.start, segment_value.end, amount)
		var position: Vector3 = $Routes/AiPath.to_global(blue_path.sample_baked(distance, false)) + Vector3(0, driving_height, 0)
		pose = {"position": position, "heading": heading}
		if remaining <= float(segment_value.duration):
			break
		remaining -= float(segment_value.duration)
	return pose

func prepare_building_growth() -> void:
	# Schedule against actual travel/turn timing, rather than the entire song.
	var roadside_count = 0
	for i in range(building_blocks.size()):
		var volume: MeshInstance3D = building_blocks[i].get_node("Volume")
		# B models use the same parcel bounds; include the original roof lip.
		building_burial_depths.append(volume.mesh.size.y + 0.12)
		var point: Vector3 = $Routes/AiPath.to_local(building_blocks[i].global_position)
		var offset = blue_path.get_closest_offset(point)
		var delta = point - blue_path.sample_baked(offset, false)
		var clearance = Vector2(maxf(absf(delta.x) - volume.mesh.size.x * 0.5, 0.0),
			maxf(absf(delta.z) - volume.mesh.size.z * 0.5, 0.0)).length()
		var rise_time = -BUILDING_RISE_SECONDS
		# Include the entire line and corner parcels, including buildings past the drive endpoint.
		if clearance <= BUILDING_ROADSIDE_DISTANCE:
			roadside_count += 1
			var trigger_offset = offset - 28.0
			var journey_time = 0.0
			for segment_value in drive_segments:
				if not segment_value.turn and trigger_offset <= float(segment_value.end):
					var amount = clampf((trigger_offset - float(segment_value.start)) / (float(segment_value.end) - float(segment_value.start)), 0.0, 1.0)
					journey_time += amount * float(segment_value.duration)
					break
				journey_time += float(segment_value.duration)
			# Distant portions finish before the lift; the route beside the camera retains its timing.
			rise_time = minf(journey_time * CITY_END, CITY_END - BUILDING_RISE_SECONDS - 0.15) + float(i % 7) * 0.025
		building_rise_times.append(rise_time)
	print("ROADSIDE_RISE buildings=", roadside_count, " facade_clearance=", BUILDING_ROADSIDE_DISTANCE, " whole_blue_line=true")

func make_entry_plane() -> void:
	entry_transition = Node3D.new()
	entry_transition.name = "ContinuousRouteEntry"
	entry_transition.set_script(load("res://entry_transition.gd"))
	add_child(entry_transition)
	entry_transition.setup(self, camera)

func entry_camera(progress: float) -> void:
	entry_transition.camera_pose(progress)

func drive_camera(city_time: float) -> void:
	var pose = drive_pose(city_time)
	move_camera(pose.position, pose.position + pose.heading * 20.0, 68.0)

func map_camera(progress: float = 0.0) -> void:
	camera.position = MAP_TOP + MAP_DRIFT * smoothstep01(progress)
	camera.rotation = Vector3(-PI * 0.5, MAP_YAW, 0.0)
	camera.fov = 55.0

func lift_camera(amount: float) -> void:
	var pose = drive_pose(1.0)
	var t = smoothstep01(amount)
	var origin: Vector3 = pose.position
	var heading: Vector3 = pose.heading
	# One uninterrupted move: camera XYZ and gaze XYZ share the same curve time.
	var p1 = origin + heading * 110.0 + Vector3(0, 140, 0)
	var p2 = MAP_TOP + Vector3(-200, -160, 180)
	camera.position = origin.bezier_interpolate(p1, p2, MAP_TOP, t)
	var gaze_start = origin + heading * 150.0
	var gaze_p1 = origin + heading * 260.0
	var top_target = Vector3(MAP_TOP.x, 0, MAP_TOP.z)
	var gaze_p2 = top_target + Vector3(-200, 0, 180) + Vector3(-sin(MAP_YAW), 0, -cos(MAP_YAW)) * 100.0
	var gaze = gaze_start.bezier_interpolate(gaze_p1, gaze_p2, top_target, t)
	var direction = (gaze - camera.position).normalized()
	var horizontal = Vector2(direction.x, direction.z).length()
	# Derive the view from its moving target while keeping roll at zero.
	camera.rotation = Vector3(atan2(direction.y, horizontal), atan2(-direction.x, -direction.z) if horizontal > 0.000001 else MAP_YAW, 0.0)
	camera.fov = lerpf(68.0, 55.0, t)

func tilt_camera(amount: float) -> void:
	var t = smootherstep01(amount)
	var low_angle = asin(LOW_CAMERA_HEIGHT / LOW_CAMERA_RADIUS)
	var top_end = MAP_TOP + MAP_DRIFT
	var top_target = Vector3(top_end.x, 0, top_end.z)
	var position_value = oblique_position(lerp_angle(MAP_YAW, 0.38, t), lerpf(PI * 0.5, low_angle, t), lerpf(MAP_TOP.y, LOW_CAMERA_RADIUS, t))
	position_value += (top_target - MAP_CENTER) * (1.0 - t)
	camera.position = position_value
	camera.fov = lerpf(55.0, LOW_CAMERA_FOV, t)
	var top_up = Vector3.FORWARD.rotated(Vector3.UP, MAP_YAW)
	camera.look_at(top_target.lerp(LOW_CAMERA_TARGET, t), top_up.lerp(Vector3.UP, t).normalized())

func move_camera(position_value: Vector3, target: Vector3, fov: float) -> void:
	camera.position = position_value
	camera.fov = fov
	var direction = (target - position_value).normalized()
	var up = Vector3.FORWARD if absf(direction.dot(Vector3.UP)) > 0.99999 else Vector3.UP
	camera.look_at(target, up)

func set_building_height(height_scale: float) -> void:
	for block in building_blocks:
		block.scale.y = height_scale
		block.position.y = -0.20 * (1.0 - smoothstep01(height_scale / OBLIQUE_BUILDING_HEIGHT))

func grow_buildings(seconds: float, flatten: float = 0.0, entry_hide: float = 0.0) -> void:
	for i in range(building_blocks.size()):
		var block = building_blocks[i]
		var growth = smoothstep01((seconds - building_rise_times[i]) / BUILDING_RISE_SECONDS)
		growth = minf(growth, 1.0 - entry_hide)
		# Rise as a rigid building. Scaling belongs only to the later map presentation.
		block.scale.y = lerpf(1.0, 0.002, flatten)
		block.position.y = lerpf(-building_burial_depths[i] * (1.0 - growth), -0.20, flatten)

func pose_stations(visible_value: bool) -> void:
	for node in $Routes.get_children():
		if node.name.ends_with("Rim") or node.name.ends_with("Core"):
			node.visible = visible_value
		elif node.name.ends_with("MapRibbon"):
			node.visible = visible_value
		elif node.name in ["AiPathRibbon", "RenPathRibbon"]:
			node.visible = not visible_value

func pose_route_reveal(progress: float, enabled: bool = true) -> void:
	for node in $Routes.get_children():
		if node.name.ends_with("MapRibbon"):
			node.material_override.set_shader_parameter("reveal", progress)
		elif node.has_meta("route_progress"):
			node.visible = enabled and progress >= float(node.get_meta("route_progress"))
		elif node.name.begins_with("WalkingLink"):
			node.visible = enabled and progress >= 0.999
	$Routes/SannomiyaTitle.visible = enabled and progress >= 0.999

func pose_annotations(amount: float, enabled: bool) -> void:
	var pins = $MapGround/MapAnnotations.get_children()
	$MapGround/MapAnnotations.visible = enabled
	for i in range(pins.size()):
		var reveal = smoothstep01((amount - float(i) * 0.11) / 0.20)
		pins[i].visible = reveal > 0.0
		pins[i].get_node("Dot").scale = Vector3.ONE * lerpf(1.9, 1.0, reveal)
		pins[i].get_node("Title").visible = reveal > 0.0
		pins[i].get_node("Title").modulate.a = reveal

func pose_labels(visible_value: bool) -> void:
	# Keep the route callout below the enlarged Hiiro card in the low shot.
	$Routes/SannomiyaTitle.position.y = 12.0 if visible_value else 70.0
	for group in [$Routes, $Landmarks, $Characters, $MapGround]:
		for node in group.find_children("*", "Label3D", true, false):
			node.visible = visible_value

func reset_actors() -> void:
	$Characters/Ai.position = Vector3(-620, 0.13, 210)
	$Characters/Ren.position = Vector3(-620, 0.13, -330)

func apply_view(time: float) -> void:
	if capture_time >= ENTRY_BEGIN:
		apply_tour(capture_time)
		return
	if touring:
		apply_tour(minf(time, BRIDGE_END))
		return
	bridge_panel.visible = false
	bridge_flash.visible = false
	entry_transition.pose(CITY_END)
	pose_labels(view != "city" and view != "map")
	camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	pose_stations(view != "city")
	pose_route_reveal(1.0, view != "city")
	pose_annotations(1.0, view == "map")
	$Characters.visible = view != "city" and view != "map"
	$Buildings.visible = true
	set_building_height(OBLIQUE_BUILDING_HEIGHT)
	emphasize_map(1.0 if view == "map" else 0.0)
	reset_actors()
	for actor in $Characters.get_children():
		actor.scale = Vector3.ONE * 20.0
	if view == "city":
		var city_time = fmod(time, CITY_END) / CITY_END
		grow_buildings(city_time * CITY_END)
		drive_camera(city_time)
	elif view == "map":
		grow_buildings(time, 1.0)
		map_camera(0.5)
	elif view == "orbit":
		move_camera(oblique_position(yaw + time * 0.09, elevation, radius), LOW_CAMERA_TARGET, LOW_CAMERA_FOV)
	else:
		move_camera(oblique_position(yaw, elevation, radius), LOW_CAMERA_TARGET, LOW_CAMERA_FOV)
	pose_ren_focus(-1.0)
	map_callouts.pose()
	if status:
		status.text = view.to_upper() + "   /   AI: BLUE    REN: PINK"

func apply_tour(time: float) -> void:
	var elapsed = clampf(time, ENTRY_BEGIN, BRIDGE_END)
	var entry_progress = (elapsed - ENTRY_BEGIN) / -ENTRY_BEGIN
	entry_transition.pose(elapsed)
	var in_map = elapsed >= LIFT_END and elapsed < MAP_END
	var in_oblique = elapsed >= MAP_END
	camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	# Flatten the printed blocks into their footprints so map text and routes remain unobstructed.
	$Buildings.visible = true
	var map_emphasis = smoothstep01((elapsed - CITY_END - 0.45) / (LIFT_END - CITY_END - 0.45)) * (1.0 - smootherstep01((elapsed - MAP_END) / (TILT_END - MAP_END)))
	var entry_hide = 1.0 - smoothstep01((entry_progress - 0.60) / 0.40)
	grow_buildings(elapsed, map_emphasis, entry_hide)
	var map_height = lerpf(1.0, OBLIQUE_BUILDING_HEIGHT, smootherstep01((elapsed - CITY_END - 0.35) / (LIFT_END - CITY_END - 0.35)))
	for block in building_blocks:
		block.scale.y *= map_height
	emphasize_map(map_emphasis)
	pose_labels(in_oblique)
	pose_stations(true)
	# Keep the street ribbons, adding the thicker drawn line without replacing them.
	$Routes/AiPathRibbon.visible = true
	$Routes/RenPathRibbon.visible = true
	pose_route_reveal(smoothstep01((elapsed - ROUTE_BEGIN) / (ROUTE_END - ROUTE_BEGIN)), elapsed >= ROUTE_BEGIN)
	pose_annotations((elapsed - 8.05) / 1.0, elapsed >= 8.05 and elapsed < TILT_END)
	var annotation_fade = 1.0 - smootherstep01((elapsed - MAP_END) / (TILT_END - MAP_END))
	for pin in $MapGround/MapAnnotations.get_children():
		pin.get_node("Title").modulate.a *= annotation_fade
		pin.get_node("Dot").scale *= maxf(0.002, annotation_fade)
	$Characters.visible = in_oblique
	reset_actors()
	var actor_rise = smoothstep01((elapsed - MAP_END - 0.28) / 0.48)
	for actor in $Characters.get_children():
		var actor_size = 17.2 if actor.name == "Kamome" else 20.0
		actor.scale = Vector3(actor_size, actor_size * maxf(0.002, actor_rise), actor_size)
		actor.get_node("Name").visible = in_oblique and actor_rise > 0.95
	var meeting_progress = smoothstep01((elapsed - MAP_END - 0.65) / 1.7)
	$Characters/Ai.position = blue_path.sample_baked(blue_path.get_baked_length() * lerpf(0.52, 1.0, meeting_progress), false)
	$Characters/Ren.position = red_path.sample_baked(red_path.get_baked_length() * lerpf(0.54, 1.0, meeting_progress), false)
	pose_bridge(elapsed)
	var phase = "CITY / FOLLOW THE BLUE ROUTE"
	if elapsed < 0.0:
		entry_camera((elapsed - ENTRY_BEGIN) / -ENTRY_BEGIN)
		phase = "ENTRY / TOP LINE TO FIRST PERSON"
	elif elapsed < CITY_END:
		drive_camera(elapsed / CITY_END)
	elif elapsed < LIFT_END:
		lift_camera((elapsed - CITY_END) / (LIFT_END - CITY_END))
		phase = "LIFT / CITY TO TOP MAP"
	elif in_map:
		map_camera((elapsed - LIFT_END) / (MAP_END - LIFT_END))
		phase = "TOP MAP / DRAW ROUTES AND MARK PLACES"
	else:
		if elapsed < TILT_END:
			tilt_camera((elapsed - MAP_END) / (TILT_END - MAP_END))
		else:
			low_orbit_camera(elapsed)
		phase = "LOW OBLIQUE / SD STAND UP AND MEET"
		if elapsed >= ORBIT_END:
			phase = "WHITE LIGHT / CG BRIDGE"
	pose_ren_focus(elapsed)
	map_callouts.pose()
	if status:
		status.text = "%05.2fs  /  %s" % [SONG_START + elapsed, phase]

func low_orbit_camera(time: float) -> void:
	# Keep the orbit geometry, hold the camera, then return right at song 39.200.
	var turn = acos(-0.13 / (0.40 * PI)) / PI
	var t = turn * smootherstep01((time - TILT_END) / (FIRST_ORBIT_END - TILT_END))
	if time >= SECOND_ORBIT_BEGIN:
		t = lerpf(turn, 1.0, smootherstep01((time - SECOND_ORBIT_BEGIN) / (SECOND_ORBIT_END - SECOND_ORBIT_BEGIN)))
	var sweep = sin(PI * t)
	var angle = 0.38 - 0.40 * sweep - 0.13 * t
	var distance = LOW_CAMERA_RADIUS + 55.0 * sweep + 60.0 * t
	if time >= SECOND_ORBIT_BEGIN:
		var held_angle = 0.38 - 0.40 * sin(PI * turn) - 0.13 * turn
		var held_distance = LOW_CAMERA_RADIUS + 55.0 * sin(PI * turn) + 60.0 * turn
		angle = lerpf(held_angle, angle, SECOND_ORBIT_STRENGTH)
		distance = lerpf(held_distance, distance, SECOND_ORBIT_STRENGTH)
	var transition = smoothstep01((time - ORBIT_END) / (TOUR_END - ORBIT_END))
	angle += 0.12 * SECOND_ORBIT_STRENGTH * transition
	move_camera(oblique_position(angle, asin(LOW_CAMERA_HEIGHT / distance), distance), LOW_CAMERA_TARGET, LOW_CAMERA_FOV)

func _unhandled_input(event: InputEvent) -> void:
	# Movie Maker must not react to desktop clicks or keys during an export.
	if rendering_movie or OS.get_cmdline_args().has("--write-movie"):
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE:
			touring = not touring
			clock = ENTRY_BEGIN
			capture_time = -1.0
		elif event.keycode in [KEY_1, KEY_2, KEY_3, KEY_4]:
			view = ["city", "map", "oblique", "orbit"][event.keycode - KEY_1]
			touring = false
			capture_time = -1.0
			clock = 0.0
	elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		touring = false
		view = "oblique"
		yaw -= event.relative.x * 0.006
		elevation = clampf(elevation + event.relative.y * 0.004, 0.004, 1.25)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			radius = maxf(350.0, radius - 50.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			radius = minf(1800.0, radius + 50.0)
