extends SceneTree
## Run with --script; this never instantiates or edits the production scene/rig.

var stage := ""
var frames := ""
var seconds := 5.6
var strength := 1.0
var sample_times: Array[float] = []
var cg := 14
var crop := Rect2()
var hair: Node2D
var world: Node2D
var clock := 0.0
var active := false
var preview_paused := false
var metrics_only := false
var proof := {"fixed_vertices": 0, "fixed_max_displacement_px": 0.0,
	"support_max_displacement_px": 0.0, "fixed_moving_weight_max": 0.0,
	"visible_max_displacement_px": 0.0, "visible_min_area_ratio": 1.0,
	"visible_min_edge_ratio": 1.0, "visible_max_edge_ratio": 1.0,
		"visible_folded_triangles_max": 0, "per_part": {}}

func _initialize() -> void:
	call_deferred("run")

func _parse_args() -> void:
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		var pair := args[i].split("=", true, 1)
		var key := pair[0]
		var value := ""
		if pair.size() == 2:
			value = pair[1]
		else:
			i += 1
			assert(i < args.size(), "Missing argument value for "+key)
			value = args[i]
		match key:
			"--stage": stage = value.replace("\\", "/")
			"--frames": frames = value.replace("\\", "/")
			"--seconds": seconds = float(value)
			"--strength": strength = float(value)
			"--metrics-only": metrics_only = value == "true"
			"--samples":
				for sample in value.split(","):
					sample_times.append(float(sample))
			"--cg": cg = int(value)
			"--crop":
				var values := value.split(",")
				assert(values.size() == 4, "--crop needs x,y,w,h")
				crop = Rect2(float(values[0]), float(values[1]), float(values[2]), float(values[3]))
			_: assert(false, "Unknown argument: "+key)
		i += 1
	assert(not stage.is_empty(), "Supply --stage ABSOLUTE_STAGE_DIRECTORY")
	assert(seconds > 0.0, "--seconds must be positive")

func _external_image(path: String) -> Image:
	var image := Image.load_from_file(path)
	assert(image != null and not image.is_empty(), "Cannot read image: "+path)
	return image

func _path(path: String) -> String:
	return path if path.is_absolute_path() else stage.path_join(path)

func _sprite(path: String, offset := Vector2.ZERO) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.centered = false
	sprite.texture = ImageTexture.create_from_image(_external_image(_path(path)))
	sprite.position = offset
	world.add_child(sprite)
	return sprite

func _definition(part: Dictionary, index: int) -> Dictionary:
	var support_data: Array = part.get("support_point", part.chain[0])
	var support := Vector2(float(support_data[0]), float(support_data[1]))
	var first := Vector2(float(part.chain[1][0]), float(part.chain[1][1]))
	var transition: Dictionary = part.get("fixed_transition", {})
	var band := float(transition.get("root_band_px", part.get("fixed_transition_length", 16)))
	var line: Array = transition.get("cut_line", part.get("fixed_root_seam", []))
	assert(line.size() == 2, "Part needs an authored fixed seam: "+str(part.id))
	# Bone0 only holds fixed pixels. Bone1 pivots at the actual support point.
	var anchor := support-(first-support).normalized()*band
	var chain: Array = [[anchor.x, anchor.y], [support.x, support.y]]
	for i in range(1, part.chain.size()):
		chain.append(part.chain[i])
	var image := _external_image(_path(str(part.get("native_texture", str(part.id)+"-native.png"))))
	var bounds := image.get_used_rect().grow(4)
	assert(bounds.has_area(), "Empty native cutout: "+str(part.id))
	var region := str(part.get("region", "chest-front" if cg == 14 else "fringe"))
	var policy: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://hair-redo/user-grouping.json"))
	var gains: Dictionary = policy.get("motion_gain_by_id", {})
	var models: Dictionary = policy.get("deformation_by_id", {})
	var reference: Dictionary = policy.get("reference_by_id", {}).get(str(part.id), {})
	return {"name": str(part.id), "chain": chain, "texture_object": ImageTexture.create_from_image(image),
		"draw_depth": int(part.get("depth", index)),
		"bounds": [bounds.position.x, bounds.position.y, bounds.end.x, bounds.end.y],
		"cut_line": line, "root_band": band,
		"motion_profile": str(policy.get("motion_profile", "")),
		"gradient_solver": str(policy.get("gradient_solver_by_id", {}).get(str(part.id), "chain")),
		"release_fraction": float(policy.get("release_fraction_by_id", {}).get(str(part.id), 0.5)),
		"pin_return_tip": str(part.id) in policy.get("pinned_return_tips", []), "region": region,
		"sway_percent": float(part.get("sway_percent", 15.0 if cg == 14 else 10.0)),
		"reference_amplitude_deg": float(reference.get("amplitude_deg", 0.45*float(part.get("sway_percent", 15.0 if cg == 14 else 10.0)))),
		"reference_lag": float(reference.get("lag", 0.28)),
		"reference_phase": float(reference.get("phase", 0.0)),
		"motion_gain": float(gains.get(str(part.id), part.get("motion_gain", 1.0))),
		"bend_length_px": float(part.get("bend_length_px", 0.0)),
		"deformation_model": str(part.get("deformation_model", models.get(str(part.id), "skeleton"))),
		"phase": float(part.get("phase", 0.3+index*0.79)),
		"response": float(part.get("response", 9.0 if cg == 14 else 12.0)),
		"stiffness": 4.0, "damping": 0.85, "mass": 0.7}

func _collect_proof() -> void:
	var current: Dictionary = hair.pin_metrics()
	proof.fixed_vertices = current.fixed_vertices
	for key in ["fixed_max_displacement_px", "support_max_displacement_px", "fixed_moving_weight_max"]:
		proof[key] = maxf(float(proof[key]), float(current[key]))
	proof.visible_max_displacement_px = maxf(proof.visible_max_displacement_px, current.visible_max_displacement_px)
	proof.visible_min_area_ratio = minf(proof.visible_min_area_ratio, current.visible_min_area_ratio)
	proof.visible_folded_triangles_max = maxi(proof.visible_folded_triangles_max, current.visible_folded_triangles)
	proof.visible_min_edge_ratio = minf(proof.visible_min_edge_ratio, current.get("visible_min_edge_ratio", 1.0))
	proof.visible_max_edge_ratio = maxf(proof.visible_max_edge_ratio, current.get("visible_max_edge_ratio", 1.0))
	for id in current.per_part:
		var value: Dictionary = current.per_part[id]
		var previous: Dictionary = proof.per_part.get(id, {"max_displacement_px": 0.0,
			"min_area_ratio": 1.0, "folded_triangles": 0})
		previous.max_displacement_px = maxf(previous.max_displacement_px, value.max_displacement_px)
		previous.min_area_ratio = minf(previous.min_area_ratio, value.min_area_ratio)
		previous.folded_triangles = maxi(previous.folded_triangles, value.folded_triangles)
		previous.min_edge_ratio = minf(previous.get("min_edge_ratio", 1.0), value.get("min_edge_ratio", 1.0))
		previous.max_edge_ratio = maxf(previous.get("max_edge_ratio", 1.0), value.get("max_edge_ratio", 1.0))
		previous.safety_scale_min = minf(previous.get("safety_scale_min", 1.0), value.get("safety_scale", 1.0))
		proof.per_part[id] = previous

func run() -> void:
	_parse_args()
	if not frames.is_empty():
		OS.low_processor_usage_mode = false
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var record: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(stage.path_join("stage.json")))
	var size := Vector2i(1280, 720) if crop.has_area() else Vector2i(1920, 1080)
	root.size = size
	root.content_scale_size = size
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	root.title = "CGC%d 松散发簇隔离预览 | H 发束 G 骨骼 Space 暂停" % cg
	root.disable_3d = true
	root.close_requested.connect(func(): quit())
	root.window_input.connect(_input_event)
	world = Node2D.new()
	root.add_child(world)
	if crop.has_area():
		var zoom := minf(float(size.x)/crop.size.x, float(size.y)/crop.size.y)
		world.scale = Vector2.ONE*zoom
		world.position = (Vector2(size)-crop.size*zoom)*0.5-crop.position*zoom
	var plate := stage.path_join("repaired-plate.png")
	if not FileAccess.file_exists(plate):
		plate = stage.path_join("before.png")
		root.title += " [未补底结构测试]"
		print("PREVIEW_UNREPAIRED_TEST: before.png is only a runtime test; duplicate original hair is not visual acceptance.")
	var background := _sprite(plate)
	background.z_index = -1000
	hair = load("res://hair-redo/reference-wind.gd").new()
	# Follow the wind already drawn into each camera view of the cliff.
	hair.wind_direction = Vector2(1.0, -0.32) if cg == 15 else Vector2(-1.0, -0.24)
	var policy: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://hair-redo/user-grouping.json"))
	hair.wind_time_offset = float(policy.get("time_offset_by_cg", {}).get(str(cg), 0.0))
	world.add_child(hair)
	var definitions: Array = []
	# Parts are authored front-to-back; draw back-to-front without splitting clusters.
	for i in range(record.parts.size()-1, -1, -1):
		definitions.append(_definition(record.parts[i], i))
	hair.build(definitions, seconds)
	for overlay in record.get("static_overlays", []):
		if overlay is String:
			var foreground := _sprite(overlay)
			foreground.z_index = 1000
		else:
			var point: Array = overlay.get("position", [0, 0])
			var foreground := _sprite(str(overlay.get("path", overlay.get("texture", ""))), Vector2(float(point[0]), float(point[1])))
			foreground.z_index = -int(overlay.draw_depth) if overlay.has("draw_depth") else 1000
	print("SHORT_PREVIEW_READY cg=%d parts=%d seconds=%.3f strength=%.3f solver=reference-wind 100percent_baseline_deg=45" % [cg, definitions.size(), seconds, strength])
	if metrics_only:
		var count := roundi(seconds*120.0)
		for frame in range(count):
			hair.pose(float(frame)/120.0, strength)
			_collect_proof()
		proof["geometry_samples"] = count
		print("SHORT_PREVIEW_PROOF ", JSON.stringify(proof))
		quit()
		return
	if frames.is_empty():
		active = true
		return
	assert(DirAccess.make_dir_recursive_absolute(frames) == OK, "Cannot create frames directory")
	await process_frame
	var count := sample_times.size() if not sample_times.is_empty() else maxi(1, roundi(seconds*60.0))
	for frame in range(count):
		var time := sample_times[frame] if not sample_times.is_empty() else float(frame)/60.0
		hair.pose(time, strength)
		# The solver calibrates 24 phases. Sample another 32 capture phases for
		# geometry; every original-speed frame is still rendered below.
		if not sample_times.is_empty() or frame % maxi(1, ceili(float(count)/32.0)) == 0 or frame == count-1:
			_collect_proof()
			proof["geometry_samples"] = int(proof.get("geometry_samples", 0))+1
		# Polygon2D queues its redraw callback. Flush it without an automatic
		# presentation, then render explicitly even for covered windows.
		await process_frame
		RenderingServer.force_draw(false)
		var image := root.get_texture().get_image()
		assert(not image.is_empty(), "Rendering needs a real renderer, not the headless dummy backend")
		assert(image.save_png(frames.path_join("frame-%04d.png" % frame)) == OK, "Cannot save preview frame")
	print("SHORT_PREVIEW_PROOF ", JSON.stringify(proof))
	print("SHORT_PREVIEW_SAVED frames=%d fps=60 directory=%s" % [count, frames])
	quit()

func _process(delta: float) -> bool:
	if active:
		if not preview_paused:
			clock = fposmod(clock+delta, seconds)
		hair.pose(clock, strength)
		_collect_proof()
	return false

func _input_event(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_H: hair.visible = not hair.visible
		KEY_G:
			hair.show_bones = not hair.show_bones
			hair.queue_redraw()
		KEY_SPACE: preview_paused = not preview_paused
		KEY_ESCAPE:
			print("SHORT_PREVIEW_PROOF ", JSON.stringify(proof))
			quit()
