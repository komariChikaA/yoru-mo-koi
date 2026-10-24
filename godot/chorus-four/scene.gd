extends Node2D
## Final shot, sampled at absolute song times. 0 timeline; 1/2 puppet; Space pause.
@export_range(0.0, 2.0, .05) var hair_strength := 1.0
@export_range(0.0, 2.0, .05) var detail_strength := 1.0
@export_range(0.0, 2.0, .05) var particle_strength := 1.0
@export_range(-1.0, 1.0, .01) var eye_change_override := -1.0

# Relative speed over normalized time, following the user's velocity sketch.
# Third component is a monotone Hermite tangent; these are not position keys.
const PULLBACK_SPEED_PROFILE := [
	Vector3(0.00, 1.000, 0.000000),
	Vector3(0.15, 1.000, 0.000000),
	Vector3(0.20, 0.950, -1.500000),
	Vector3(0.25, 0.800, -4.591837),
	Vector3(0.28, 0.550, -7.496034),
	Vector3(0.32, 0.280, -3.763941),
	Vector3(0.38, 0.130, -0.946894),
	Vector3(0.46, 0.085, -0.389423),
	Vector3(0.62, 0.040, 0.000000),
	Vector3(1.00, 0.040, 0.000000),
]
const PULLBACK_INTEGRATION_STEPS := 512
var pullback_velocity: Curve
var pullback_distance := PackedFloat64Array()

var timeline: Dictionary
var worlds: Array[Node2D] = []
var views: Array[SubViewport] = []
var cards: Array[Sprite2D] = []
var rigs: Array[Node2D] = []
var particle_layers: Array[Node2D] = []
var card_materials: Array[ShaderMaterial] = []
var eyes14: Node2D
var smile15: Node2D
var previous: Sprite2D
var sky: Sprite2D
var sky_material: ShaderMaterial
var border: Sprite2D
var paint := ShaderMaterial.new()
var paper: Array[Texture2D] = []
var dust: Array[Texture2D] = []
var dust_sprite: Sprite2D
var title: Sprite2D
var title_states: Array[Texture2D] = []
var clock := 0.0
var frame := 0
var frame_limit := 408
var fps := 60.0
var rendering := false
var paused := false
var fixed_time := -1.0
var solo := 0
var hide_hair := false
var blink_speed := 1.0

func sprite(parent: Node, path: String) -> Sprite2D:
	var s := Sprite2D.new()
	s.centered = false
	s.texture = load(path)
	parent.add_child(s)
	return s

func blur_material(s: Sprite2D) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = load("res://card-blur.gdshader")
	s.material = material
	return material

func phase(key: String, song: float) -> float:
	return smoothstep(float(timeline[key][0]), float(timeline[key][1]), song)

func camera(card: Sprite2D, focus: Vector2, zoom: float) -> void:
	card.rotation = 0.0
	card.scale = Vector2.ONE * zoom
	card.position = focus * (1.0 - zoom)

func build_pullback_distance() -> void:
	pullback_velocity = Curve.new()
	for key in PULLBACK_SPEED_PROFILE:
		pullback_velocity.add_point(Vector2(key.x, key.y), key.z, key.z, Curve.TANGENT_FREE, Curve.TANGENT_FREE)
	pullback_distance.resize(PULLBACK_INTEGRATION_STEPS + 1)
	pullback_distance[0] = 0.0
	var previous_speed := pullback_velocity.sample(0.0)
	for i in range(1, PULLBACK_INTEGRATION_STEPS + 1):
		var speed := pullback_velocity.sample(float(i) / PULLBACK_INTEGRATION_STEPS)
		pullback_distance[i] = pullback_distance[i-1] + (previous_speed + speed) * 0.5 / PULLBACK_INTEGRATION_STEPS
		previous_speed = speed
	var total := pullback_distance[PULLBACK_INTEGRATION_STEPS]
	for i in range(pullback_distance.size()):
		pullback_distance[i] /= total

func pullback_progress(value: float, end_phase: float = 1.0) -> float:
	var position := clampf(value, 0.0, 1.0) * PULLBACK_INTEGRATION_STEPS
	var index := mini(int(position), PULLBACK_INTEGRATION_STEPS - 1)
	var distance := lerpf(pullback_distance[index], pullback_distance[index+1], position-index)
	# Continue the final velocity until the outgoing card has fully dissolved.
	var tail_speed := (pullback_distance[-1] - pullback_distance[-2]) * PULLBACK_INTEGRATION_STEPS
	distance += maxf(0.0, value - 1.0) * tail_speed
	return distance / (1.0 + maxf(0.0, end_phase - 1.0) * tail_speed)

func _ready() -> void:
	timeline = JSON.parse_string(FileAccess.get_file_as_string("res://timeline.json"))
	build_pullback_distance()
	for arg in OS.get_cmdline_user_args():
		if arg == "--render": rendering = true
		elif arg == "--puppet14": solo = 1
		elif arg == "--puppet15": solo = 2
		elif arg == "--hide-hair": hide_hair = true
		elif arg.begins_with("--time="): fixed_time = float(arg.trim_prefix("--time="))
		elif arg.begins_with("--frames="): frame_limit = int(arg.trim_prefix("--frames="))
		elif arg.begins_with("--strength="): hair_strength = float(arg.trim_prefix("--strength="))
		elif arg.begins_with("--blink-speed="): blink_speed = float(arg.trim_prefix("--blink-speed="))
		elif arg.begins_with("--particle-strength="): particle_strength = float(arg.trim_prefix("--particle-strength="))
	var back := ColorRect.new()
	back.size = Vector2(1920, 1080)
	back.color = Color("f4edda")
	add_child(back)
	previous = sprite(self, "res://assets/entry-previous.png")
	sky = sprite(self, "res://assets/entry-sunset.png")
	sky_material = blur_material(sky)
	for i in range(2):
		var view := SubViewport.new()
		view.size = Vector2i(1920, 1080)
		view.disable_3d = true
		view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		view.transparent_bg = true
		add_child(view)
		views.append(view)
		var world := Node2D.new()
		view.add_child(world)
		worlds.append(world)
		var rebuilt: Node2D = load("res://rebuilt-hair.gd").new()
		world.add_child(rebuilt)
		rebuilt.configure(14 if i == 0 else 15, "", "res://assets/CGC14-rebuilt-eye-clean.png" if i == 0 else "")
		rigs.append(rebuilt)
		var particles: Node2D = load("res://sunset-particles.gd").new()
		particles.cg = 14 if i == 0 else 15
		particles.z_index = -900
		rebuilt.add_child(particles)
		particle_layers.append(particles)
		if i == 0:
			eyes14 = load("res://cgc14-eye.gd").new()
			rebuilt.eye_layer.add_child(eyes14)
			eyes14.configure(rebuilt.plate)
		else:
			smile15 = load("res://smile15.gd").new()
			rebuilt.eye_layer.add_child(smile15)
			smile15.configure(rebuilt.plate, rebuilt.eye_layer)
			smile15.detail_strength = detail_strength
		var card := Sprite2D.new()
		card.centered = false
		card.texture = view.get_texture()
		add_child(card)
		cards.append(card)
		card_materials.append(blur_material(card))
	border = sprite(self, "res://assets/white-frame.png")
	for n in range(6):
		paper.append(load("res://assets/paint-finish/wall-state-%d.png" % n))
		dust.append(load("res://assets/paint-finish/dust-state-%d.png" % n))
		title_states.append(load("res://assets/paint-finish/all-collected-title-state-%d.png" % n))
	var wipe := ColorRect.new()
	wipe.size = Vector2(1920, 1080)
	paint.shader = load("res://paint.gdshader")
	wipe.material = paint
	add_child(wipe)
	paint.set_shader_parameter("arrival", load("res://assets/paint-finish/paint-arrival.png"))
	paint.set_shader_parameter("surface", load("res://assets/paint-finish/paint-surface.png"))
	paint.set_shader_parameter("bristles", load("res://assets/paint-finish/paint-bristle-detail.png"))
	dust_sprite = sprite(self, "res://assets/paint-finish/dust-state-0.png")
	title = sprite(self, "res://assets/paint-finish/all-collected-title.png")
	title.centered = true
	title.position = Vector2(960, 577)
	pose()
	if rendering:
		RenderingServer.frame_post_draw.connect(_capture_frame_done)
	print("SCENE4_READY cut=%.3f paint=%.3f end=%.3f rebuilt_hair=%d/%d title=全種類のカラーベルを獲得しました！" % [timeline.cut, timeline.paint_start, timeline.song_end, rigs[0].part_ids.size(), rigs[1].part_ids.size()])

func pose() -> void:
	var t := fixed_time if fixed_time >= 0.0 else clock
	var song := float(timeline.song_start) + t
	var local15 := t if solo == 2 else maxf(0.0, song - float(timeline.cut_blend[0]))
	# Hidden cards need neither a fresh mesh nor a viewport draw. Sample the
	# absolute pose when they enter; wind and expression timing stay unchanged.
	var active14 := solo == 1 or (solo == 0 and song < float(timeline.cut_blend[1]))
	var active15 := solo == 2 or (solo == 0 and song >= float(timeline.cut_blend[0]) and song < float(timeline.paint_end))
	views[0].render_target_update_mode = SubViewport.UPDATE_ALWAYS if active14 else SubViewport.UPDATE_DISABLED
	views[1].render_target_update_mode = SubViewport.UPDATE_ALWAYS if active15 else SubViewport.UPDATE_DISABLED
	if active14: rigs[0].pose(t, hair_strength)
	if active15: rigs[1].pose(local15, hair_strength)
	particle_layers[0].update_at(t, particle_strength)
	particle_layers[1].update_at(local15, particle_strength)
	for rig in rigs: rig.set_hair_visible(not hide_hair)
	eyes14.manual_close = eye_change_override
	eyes14.pose(1.32 + (t - 1.32) * blink_speed)
	# Expression timing is local to the incoming CG, independent of hair sampling.
	smile15.pose(local15)
	if solo > 0:
		previous.visible = false
		sky.visible = false
		for i in range(2):
			cards[i].visible = i == solo - 1
			camera(cards[i], Vector2(960, 540), 1.0)
			card_materials[i].set_shader_parameter("opacity", 1.0)
			card_materials[i].set_shader_parameter("blur_px", 0.0)
	else:
		previous.visible = song < float(timeline.entry_cg[1])
		sky.visible = previous.visible
		sky_material.set_shader_parameter("opacity", phase("entry_sky", song))
		sky_material.set_shader_parameter("blur_px", 2.5)
		# Begin under zero CG opacity; the sky follows the same outward/rightward motion.
		var pullback_duration := float(timeline.camera_pullback[1]) - float(timeline.camera_pullback[0])
		var pullback_end_phase := (float(timeline.cut_blend[1]) - float(timeline.camera_pullback[0])) / pullback_duration
		var pullback_phase := clampf((song - float(timeline.camera_pullback[0])) / pullback_duration, 0.0, pullback_end_phase)
		var pullback := pullback_progress(pullback_phase, pullback_end_phase)
		camera(sky, Vector2(960, 540), lerpf(1.022, 1.0, pullback))
		sky.position.x -= 4.2 * (1.0 - pullback)
		var dissolve := phase("cut_blend", song)
		var enter := smoothstep(float(timeline.cut_blend[0]), float(timeline.border_exit), song)
		cards[0].visible = dissolve < 1.0
		cards[1].visible = dissolve > 0.0
		card_materials[0].set_shader_parameter("opacity", phase("entry_cg", song))
		card_materials[1].set_shader_parameter("opacity", dissolve)
		var blur := 13.0 * pow(maxf(0.0, sin(PI * dissolve)), 1.1)
		camera(cards[0], Vector2(1250, 480), lerpf(1.42, 1.0, pullback))
		var sweep_remaining := 1.0 - pullback
		cards[0].rotation = deg_to_rad(-2.0) * sweep_remaining
		cards[0].position = Vector2(1250, 480) - (Vector2(1250, 480) * cards[0].scale).rotated(cards[0].rotation) + Vector2(-80.0 * sweep_remaining, 0.0)
		var push_phase := clampf((song - float(timeline.camera_enter[0])) / (float(timeline.camera_enter[1]) - float(timeline.camera_enter[0])), 0.0, 1.0)
		var push := float(Tween.interpolate_value(0.0, 1.0, push_phase, 1.0, Tween.TRANS_CUBIC, Tween.EASE_OUT_IN))
		var incoming_zoom := lerpf(1.015, 1.462, push)
		camera(cards[1], Vector2(1040, 470), incoming_zoom)
		# Exit blur belongs to the incoming CG card below paint, dust and title.
		# Compensate its camera zoom so the timeline's pixel strength is stable.
		var exit_blur := float(timeline.exit_blur_px) * phase("exit_blur", song) / incoming_zoom
		card_materials[0].set_shader_parameter("blur_px", blur)
		card_materials[1].set_shader_parameter("blur_px", maxf(blur, exit_blur))
		# The inherited 42px frame opens with the camera, its outer edges leaving the viewport.
		border.scale = Vector2(1.0 + .065 * enter, 1.0 + .115 * enter)
		border.position = Vector2(960, 540) * (Vector2.ONE - border.scale)
		border.modulate.a = 1.0 - smoothstep(float(timeline.border_exit) - .18, float(timeline.border_exit), song)
	border.visible = solo == 0 and song < float(timeline.border_exit)
	var progress := smoothstep(float(timeline.paint_start), float(timeline.paint_end), song) if solo == 0 else 0.0
	paint.set_shader_parameter("progress", progress)
	var state := int(floor(t * float(timeline.grain_hz))) % paper.size()
	paint.set_shader_parameter("paper", paper[state])
	dust_sprite.texture = dust[state]
	dust_sprite.visible = solo == 0
	dust_sprite.modulate.a = smoothstep(.72, 1.0, progress)
	var dust_time := maxf(0.0, song - float(timeline.paint_start))
	dust_sprite.position = Vector2(dust_time * 7.0 + sin(dust_time * 1.2), -dust_time * 4.0)
	title.visible = solo == 0
	title.modulate.a = phase("title_in", song) if solo == 0 else 0.0
	var lettering_time := maxf(0.0, song - float(timeline.title_in[0]))
	var lettering_state := int(floor(lettering_time * 10.0)) % title_states.size()
	title.texture = title_states[lettering_state]
	title.position = Vector2(960, 577 + 5 * (1.0 - phase("title_in", song)))

func _capture_frame_done() -> void:
	# Window redraws can lag process ticks; advance only after a captured draw.
	frame += 1

func _process(delta: float) -> void:
	if rendering:
		if frame >= frame_limit:
			get_tree().quit()
			return
		clock = float(frame) / fps
	elif not paused:
		clock = fmod(clock + delta, 6.8 if solo == 0 else 5.6 if solo == 1 else 9.2)
	pose()

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_SPACE: paused = not paused
			KEY_0: solo = 0; clock = 0.0
			KEY_1: solo = 1; clock = 0.0
			KEY_2: solo = 2; clock = 0.0
			KEY_H: hide_hair = not hide_hair
			KEY_HOME: clock = 0.0
