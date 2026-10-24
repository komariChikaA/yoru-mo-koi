extends Node2D

@export_range(0.0, 2.0, 0.05) var intensity: float = 1.0
@export var cycle_seconds: float = 6.0

const SHOTS = ["CGC14_a", "CGC14_b", "CGC14_c", "CGC15_c", "CGC16"]
var shot_index := 0
var rigs: Dictionary
var rig: Dictionary
var puppet_material := ShaderMaterial.new()
var sprite := Sprite2D.new()
var hair := Node2D.new()
var hair_rigs: Dictionary
var hide_hair := false
var hair_only := false
var eyes_only := false
var blink_override := -1.0
var eye_rigs: Dictionary
var clock := 0.0
var frame := 0
var fps := 60.0
var rendering := false
var paused := false
var show_pins := false
var fixed_time := -1.0
var render_frames := 360
var hud: VBoxContainer
var time_slider: HSlider
var status: Label

func _ready() -> void:
	rigs = JSON.parse_string(FileAccess.get_file_as_string("res://rigs.json"))
	hair_rigs = JSON.parse_string(FileAccess.get_file_as_string("res://hair-rigs.json"))
	eye_rigs = JSON.parse_string(FileAccess.get_file_as_string("res://eye-rigs.json"))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			shot_index = maxi(0, SHOTS.find(arg.trim_prefix("--shot=")))
		elif arg == "--render":
			rendering = true
		elif arg == "--hide-hair":
			hide_hair = true
		elif arg == "--hair-only":
			hair_only = true
		elif arg == "--eyes-only":
			eyes_only = true
		elif arg.begins_with("--blink="):
			blink_override = clampf(float(arg.trim_prefix("--blink=")),0.0,1.0)
		elif arg.begins_with("--fps="):
			fps = float(arg.trim_prefix("--fps="))
		elif arg.begins_with("--frames="):
			render_frames = int(arg.trim_prefix("--frames="))
		elif arg.begins_with("--time="):
			fixed_time = float(arg.trim_prefix("--time="))
		elif arg.begins_with("--intensity="):
			intensity = float(arg.trim_prefix("--intensity="))
	puppet_material.shader = load("res://puppet.gdshader")
	sprite.centered = false
	sprite.material = puppet_material
	add_child(sprite)
	hair.set_script(load("res://hair-sway.gd"))
	add_child(hair)
	_load_shot()
	if not rendering:
		_build_hud()
	_update_pose()
	print("CG_PUPPET_READY shot=%s cycle=%.2f fps=%.0f intensity=%.2f" % [SHOTS[shot_index], cycle_seconds, fps, intensity])

func _load_shot() -> void:
	var shot: String = SHOTS[shot_index]
	var family: String = "CGC14" if shot.begins_with("CGC14") else shot
	rig = rigs[family]
	sprite.texture = load("res://assets/%s%s.png" % [shot, "" if eyes_only else "-plate"])
	hair.build(hair_rigs[family], cycle_seconds)
	for atlas in range(4):
		puppet_material.set_shader_parameter("weights%d" % atlas, load("res://assets/%s/weights%d.png" % [family, atlas]))
	puppet_material.set_shader_parameter("eye_open",load("res://assets/%s.png" % shot))
	for texture_name in ["eye_skin","eye_region","eye_foreground","upper_lid","lower_lid","eye_curves","eye_ink"]:
		puppet_material.set_shader_parameter(texture_name,load("res://assets/%s/%s.png" % [family,texture_name.replace("_","-")]))
	var bases := PackedVector4Array()
	var bounds := PackedVector4Array()
	for eye in eye_rigs[family]:
		bases.append(Vector4(float(eye.basis[0]),float(eye.basis[1]),float(eye.basis[2]),float(eye.basis[3])))
		bounds.append(Vector4(float(eye.bounds[0]),float(eye.bounds[1]),float(eye.bounds[2]),float(eye.bounds[3])))
	puppet_material.set_shader_parameter("eye_basis",bases)
	puppet_material.set_shader_parameter("eye_bounds",bounds)
	puppet_material.set_shader_parameter("eye_count",0 if shot == "CGC14_c" else bases.size())
	var pivots := PackedVector2Array()
	for pin in rig.pins:
		pivots.append(Vector2(float(pin.pivot[0]), float(pin.pivot[1])))
	puppet_material.set_shader_parameter("pivots", pivots)
	clock = 0.0
	frame = 0
	_update_pose()

func _process(delta: float) -> void:
	if rendering and frame >= render_frames:
		get_tree().quit()
		return
	if fixed_time >= 0.0:
		clock = fixed_time
		frame += 1
	elif rendering:
		clock = float(frame) / fps
		frame += 1
	elif not paused:
		clock += delta
	_update_pose()
	if is_instance_valid(time_slider) and not time_slider.has_focus():
		time_slider.set_value_no_signal(fmod(clock, cycle_seconds))
	if is_instance_valid(status):
		status.text = "%s  %.2fs  %s" % [SHOTS[shot_index], fmod(clock, cycle_seconds), "PAUSED" if paused else "PLAYING"]
	queue_redraw()

func _update_pose() -> void:
	var t := fmod(clock, cycle_seconds)
	var motions := PackedVector4Array()
	for pin in rig.pins:
		# Hair is skinned on its own RGBA meshes. Keep head fixed at the layer roots.
		if hair_only or eyes_only or str(pin.name).contains("hair") or str(pin.name) == "head":
			motions.append(Vector4.ZERO)
			continue
		var phase := float(pin.get("phase", 0.0))
		var frequency := float(pin.get("frequency", 1.0))
		var wave := sin(TAU * frequency * t / cycle_seconds + phase) - sin(phase)
		motions.append(Vector4(float(pin.move[0]) * wave * intensity,
			float(pin.move[1]) * wave * intensity,
			deg_to_rad(float(pin.get("angle", 0.0))) * wave * intensity, 0.0))
	puppet_material.set_shader_parameter("motions", motions)
	hair.pose(clock, 0.0 if eyes_only else intensity)
	hair.visible = not hide_hair and not eyes_only
	hair.show_bones = show_pins and not rendering
	var upper := 0.0
	var lower := 0.0
	if SHOTS[shot_index] != "CGC14_c" and intensity > 0.0 and not hair_only:
		for at in [1.50, 4.45]:
			upper = maxf(upper,_blink_curve(t-float(at)))
			lower = maxf(lower,_blink_curve(t-float(at)-0.008))
	if blink_override >= 0.0:
		upper = blink_override
		lower = blink_override
	puppet_material.set_shader_parameter("blink_upper",upper)
	puppet_material.set_shader_parameter("blink_lower",lower)

func _blink_curve(elapsed: float) -> float:
	if elapsed >= 0.0 and elapsed < 0.07:
		return smoothstep(0.0,0.07,elapsed)
	if elapsed >= 0.07 and elapsed < 0.125:
		return 1.0
	if elapsed >= 0.125 and elapsed < 0.225:
		return 1.0-smoothstep(0.125,0.225,elapsed)
	return 0.0

func _build_hud() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var panel := PanelContainer.new()
	panel.position = Vector2(24, 24)
	panel.custom_minimum_size = Vector2(620, 160)
	canvas.add_child(panel)
	hud = VBoxContainer.new()
	panel.add_child(hud)
	var choice := OptionButton.new()
	for shot in SHOTS:
		choice.add_item(shot)
	choice.select(shot_index)
	choice.item_selected.connect(func(index: int): shot_index = index; _load_shot())
	hud.add_child(choice)
	status = Label.new()
	hud.add_child(status)
	var row := HBoxContainer.new()
	hud.add_child(row)
	var play := Button.new()
	play.text = "Play / Pause (Space)"
	play.pressed.connect(func(): paused = not paused)
	row.add_child(play)
	var pins := CheckButton.new()
	pins.text = "Controls (G)"
	pins.toggled.connect(func(value: bool): show_pins = value)
	row.add_child(pins)
	var underlay := CheckButton.new()
	underlay.text = "Hide hair (H)"
	underlay.toggled.connect(func(value: bool): hide_hair = value)
	row.add_child(underlay)
	var amount := HSlider.new()
	amount.min_value = 0.0
	amount.max_value = 2.0
	amount.step = 0.05
	amount.value = intensity
	amount.custom_minimum_size = Vector2(200, 0)
	amount.tooltip_text = "Motion intensity: 0 = original, 1 = pilot, 2 = exaggerated"
	amount.value_changed.connect(func(value: float): intensity = value)
	row.add_child(amount)
	time_slider = HSlider.new()
	time_slider.max_value = cycle_seconds
	time_slider.step = 1.0 / 60.0
	time_slider.value_changed.connect(func(value: float): paused = true; clock = value)
	hud.add_child(time_slider)
	var eyelid := HSlider.new()
	eyelid.min_value = -0.05
	eyelid.max_value = 1.0
	eyelid.step = 0.01
	eyelid.value = -0.05
	eyelid.tooltip_text = "Eyelid closure: below 0 = automatic; 0 = open; 1 = closed"
	eyelid.value_changed.connect(func(value: float): blink_override = value if value >= 0.0 else -1.0)
	hud.add_child(eyelid)

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE:
			paused = not paused
		elif event.keycode == KEY_G:
			show_pins = not show_pins
		elif event.keycode == KEY_H:
			hide_hair = not hide_hair
		elif event.keycode == KEY_RIGHT:
			shot_index = (shot_index + 1) % SHOTS.size()
			_load_shot()
		elif event.keycode == KEY_LEFT:
			shot_index = (shot_index + SHOTS.size() - 1) % SHOTS.size()
			_load_shot()

func _draw() -> void:
	if not show_pins or rendering:
		return
	for i in range(rig.pins.size()):
		var pin: Dictionary = rig.pins[i]
		if float(pin.radius[0]) <= 0.0:
			continue
		var point := Vector2(float(pin.center[0]), float(pin.center[1]))
		draw_circle(point, 7.0, Color(0.2, 0.95, 0.8))
		draw_arc(point, float(pin.radius[0]), 0.0, TAU, 64, Color(0.2, 0.95, 0.8, 0.35), 1.5)
		draw_string(ThemeDB.fallback_font, point + Vector2(12, -10), str(pin.name), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color.WHITE)
