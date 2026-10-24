extends Node2D
## Deterministic native-CG background motes; the existing card owns its camera,
## dissolve and blur. Moving hair and eye details render above this layer.

@export_enum("CGC14:14", "CGC15:15") var cg: int = 14

const NATIVE_SIZE := Vector2(1920, 1080)
const MARGIN := 96.0
const ASSETS := "res://assets/sunset-particles/"
const TIER_NAMES := ["small", "medium", "large"]

var particles: Array[Dictionary] = []
var exclusion: Image
var wind_direction := Vector2.ZERO
var sample_time := 0.0
var sample_strength := 1.0


func _ready() -> void:
	wind_direction = Vector2(-1.0, -0.24).normalized() if cg == 14 else Vector2(1.0, -0.32).normalized()
	var count := 108 if cg == 14 else 132
	var mask: Texture2D = load(ASSETS + "CGC%d-exclusion.png" % cg)
	exclusion = mask.get_image()
	assert(exclusion.get_size() == Vector2i(1920, 1080), "Sunset exclusion must use native CG coordinates")
	var material := ShaderMaterial.new()
	material.shader = load("res://sunset-particle.gdshader")
	material.set_shader_parameter("exclusion_mask", mask)
	var textures: Array[Texture2D] = [load(ASSETS + "native-halo-bright.png"), load(ASSETS + "native-halo-defocus.png")]
	var random := RandomNumberGenerator.new()
	random.seed = 141517 + cg * 7919
	for i in range(count):
		var tier := 2
		var diameter := random.randf_range(54.0, 104.0)
		var speed := random.randf_range(24.0, 65.0)
		var tint := Color.WHITE.lerp(Color("fff9ec"), random.randf_range(0.0, 0.12))
		var opacity := random.randf_range(0.55, 0.82)
		var mote := Sprite2D.new()
		mote.name = "SunsetMote_%s_%02d" % [TIER_NAMES[tier], i]
		mote.texture = textures[i % textures.size()]
		mote.scale = Vector2.ONE * diameter / float(mote.texture.get_width())
		mote.material = material
		add_child(mote)
		particles.append({"sprite": mote, "tier": tier, "speed": speed,
			"origin": Vector2(random.randf_range(-MARGIN, NATIVE_SIZE.x + MARGIN), random.randf_range(-MARGIN, NATIVE_SIZE.y + MARGIN)),
			"phase": random.randf_range(0.0, TAU), "eddy": random.randf_range(4.0, 8.0),
			"along": random.randf_range(2.0, 5.0), "tint": tint, "opacity": opacity})
	update_at(0.0)


func _drift(part: Dictionary, t: float) -> Vector2:
	var phase := float(part.phase)
	var across := float(part.eddy) * (sin(t * 0.48 + phase) - sin(phase))
	var along := float(part.along) * (sin(t * 0.28 + phase * 1.7) - sin(phase * 1.7))
	return wind_direction * (float(part.speed) * t + along) + wind_direction.orthogonal() * across


func update_at(t: float, strength := 1.0) -> void:
	sample_time = t
	sample_strength = maxf(0.0, strength)
	visible = sample_strength > 0.0
	for part in particles:
		var mote: Sprite2D = part.sprite
		var point: Vector2 = part.origin + _drift(part, t)
		mote.position = Vector2(fposmod(point.x + MARGIN, NATIVE_SIZE.x + 2.0 * MARGIN) - MARGIN,
			fposmod(point.y + MARGIN, NATIVE_SIZE.y + 2.0 * MARGIN) - MARGIN)
		# Slow eight-percent variation keeps the field steady rather than blinking.
		var breathing := 0.96 + 0.04 * sin(t * 0.36 + float(part.phase))
		var tint: Color = part.tint
		tint.a = clampf(float(part.opacity) * 1.35 * breathing * sample_strength, 0.0, 1.0)
		mote.modulate = tint


func metrics() -> Dictionary:
	var tier_counts := {"small": 0, "medium": 0, "large": 0}
	var visible_centers := 0
	var min_speed := INF
	var max_speed := 0.0
	var drift_sum := 0.0
	for part in particles:
		var tier_name: String = TIER_NAMES[int(part.tier)]
		tier_counts[tier_name] += 1
		var mote: Sprite2D = part.sprite
		var point := mote.position
		if sample_strength > 0.0 and Rect2(Vector2.ZERO, NATIVE_SIZE).has_point(point):
			if exclusion.get_pixel(int(point.x), int(point.y)).r < 0.95:
				visible_centers += 1
		min_speed = minf(min_speed, float(part.speed))
		max_speed = maxf(max_speed, float(part.speed))
		drift_sum += _drift(part, sample_time).length()
	return {"cg": cg, "count": particles.size(), "tier_counts": tier_counts,
		"center_visible_count": visible_centers, "time": sample_time, "strength": sample_strength,
		"wind_direction": [wind_direction.x, wind_direction.y],
		"base_speed_px_s": [min_speed if not particles.is_empty() else 0.0, max_speed],
		"mean_unwrapped_drift_px": drift_sum / float(maxi(1, particles.size()))}
