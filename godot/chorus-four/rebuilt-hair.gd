extends Node2D
## Production adapter for the reviewed natural-cluster hair rebuilds.
## Add this node to the puppet world before configure(); all images retain
## their authored pixel coordinates, including CGC15's 1920x1600 continuation.

const STAGE_ROOT := "res://local-assets/rebuilt-hair"

var cg := 14
var cycle := 5.6
var stage_dir := ""
var plate: Sprite2D
var hair: Node2D
## Eye/tear overlays belong above the repaired plate and behind moving hair.
## Existing eye code may configure(plate) to attach its aperture shader.
var eye_layer: Node2D
var part_ids: Array[String] = []
var static_overlays: Array[Sprite2D] = []


func _image(path: String) -> Image:
	var image := Image.load_from_file(path)
	assert(image != null and not image.is_empty(), "Cannot read rebuilt hair image: "+path)
	return image


func _path(path: String) -> String:
	return path if path.is_absolute_path() else stage_dir.path_join(path)


func _sprite(path: String, offset := Vector2.ZERO) -> Sprite2D:
	var result := Sprite2D.new()
	result.centered = false
	result.texture = ImageTexture.create_from_image(_image(_path(path)))
	result.position = offset
	add_child(result)
	return result


func _definition(part: Dictionary, index: int, policy: Dictionary) -> Dictionary:
	var support_data: Array = part.get("support_point", part.chain[0])
	var support := Vector2(float(support_data[0]), float(support_data[1]))
	var first := Vector2(float(part.chain[1][0]), float(part.chain[1][1]))
	var transition: Dictionary = part.get("fixed_transition", {})
	var band := float(transition.get("root_band_px", part.get("fixed_transition_length", 16)))
	var line: Array = transition.get("cut_line", part.get("fixed_root_seam", []))
	assert(line.size() == 2, "Rebuilt hair needs its authored support seam: "+str(part.id))
	var anchor := support-(first-support).normalized()*band
	var chain: Array = [[anchor.x, anchor.y], [support.x, support.y]]
	for i in range(1, part.chain.size()):
		chain.append(part.chain[i])
	var image := _image(_path(str(part.get("native_texture", str(part.id)+"-native.png"))))
	var bounds := image.get_used_rect().grow(4)
	assert(bounds.has_area(), "Empty rebuilt hair cluster: "+str(part.id))
	var gains: Dictionary = policy.get("motion_gain_by_id", {})
	var models: Dictionary = policy.get("deformation_by_id", {})
	var reference: Dictionary = policy.get("reference_by_id", {}).get(str(part.id), {})
	return {"name": str(part.id), "chain": chain,
		"texture_object": ImageTexture.create_from_image(image),
		"draw_depth": int(part.get("depth", index)),
		"bounds": [bounds.position.x, bounds.position.y, bounds.end.x, bounds.end.y],
		"cut_line": line, "root_band": band,
		"motion_profile": str(policy.get("motion_profile", "")),
		"gradient_solver": str(policy.get("gradient_solver_by_id", {}).get(str(part.id), "chain")),
		"release_fraction": float(policy.get("release_fraction_by_id", {}).get(str(part.id), 0.5)),
		"pin_return_tip": str(part.id) in policy.get("pinned_return_tips", []),
		"region": str(part.get("region", "chest-front" if cg == 14 else "fringe")),
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


func configure(cg_number: int, stage_override := "", plate_override := "") -> void:
	assert(is_inside_tree(), "Add rebuilt-hair to the puppet world before configure()")
	assert(cg_number == 14 or cg_number == 15, "Rebuilt hair supports CGC14 and CGC15")
	for child in get_children():
		remove_child(child)
		child.queue_free()
	part_ids.clear()
	static_overlays.clear()
	cg = cg_number
	cycle = 5.6 if cg == 14 else 9.2
	var default_stage := "CGC14/stage-cliff-wind-v2" if cg == 14 else "CGC15/stage-reference-wind-root-clean"
	stage_dir = stage_override.replace("\\", "/") if not stage_override.is_empty() else ProjectSettings.globalize_path(STAGE_ROOT).path_join(default_stage)
	var record: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(stage_dir.path_join("stage.json")))
	var policy: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://hair-redo/user-grouping.json"))
	plate = _sprite("repaired-plate.png" if plate_override.is_empty() else plate_override)
	plate.name = "RepairedPlate"
	plate.z_index = -1000
	eye_layer = Node2D.new()
	eye_layer.name = "EyeDetails"
	eye_layer.z_index = -500
	add_child(eye_layer)
	hair = load("res://hair-redo/reference-wind.gd").new()
	hair.name = "ReviewedHairClusters"
	hair.wind_direction = Vector2(1.0, -0.32) if cg == 15 else Vector2(-1.0, -0.24)
	hair.wind_time_offset = float(policy.get("time_offset_by_cg", {}).get(str(cg), 0.0))
	add_child(hair)
	var definitions: Array = []
	for i in range(record.parts.size()-1, -1, -1):
		definitions.append(_definition(record.parts[i], i, policy))
	for part in record.parts:
		part_ids.append(str(part.id))
	hair.build(definitions, cycle)
	for overlay in record.get("static_overlays", []):
		var foreground: Sprite2D
		if overlay is String:
			foreground = _sprite(overlay)
			foreground.z_index = 1000
		else:
			var point: Array = overlay.get("position", [0, 0])
			foreground = _sprite(str(overlay.get("path", overlay.get("texture", ""))), Vector2(float(point[0]), float(point[1])))
			foreground.z_index = -int(overlay.draw_depth) if overlay.has("draw_depth") else 1000
		static_overlays.append(foreground)
	pose(0.0)
	print("REBUILT_HAIR_READY cg=%d parts=%d seconds=%.3f stage=%s" % [cg, part_ids.size(), cycle, stage_dir])


func pose(time: float, amount := 1.0) -> void:
	hair.pose(time, amount)


func set_hair_visible(value: bool) -> void:
	hair.visible = value


func pin_metrics() -> Dictionary:
	return hair.pin_metrics()
