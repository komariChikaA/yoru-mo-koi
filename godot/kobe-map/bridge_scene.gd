extends Control
## Shared raster assets/timeline also used by the Storybrew Bridge effect.
var shots: Array[Dictionary] = []
var lyrics: Array[Dictionary] = []
var textures: Dictionary = {}
var song_time_ms := 40000.0
var show_lyrics := true
var bar_start := 0.0
var bar_settle := 0.0
var bar_end := 0.0
var bar_height := 0.0
var montage: Array[Dictionary] = []
const ASSETS = "res://assets/bridge/"
const MONTAGE = "res://assets/bridge-montage/"

func _ready() -> void:
	size = Vector2(1920, 1080)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	textures[ASSETS + "base-day.png"] = load(ASSETS + "base-day.png")
	shots = read_timeline("timeline.tsv")
	lyrics = read_timeline("lyrics-motion.tsv")
	var bars = FileAccess.get_file_as_string(ASSETS + "letterbox.tsv").strip_edges().split("\t")
	bar_start = bars[0].to_float()
	bar_settle = bars[1].to_float()
	bar_end = bars[2].to_float()
	bar_height = bars[3].to_float()
	read_montage()

func read_montage() -> void:
	var by_id: Dictionary = {}
	for line in FileAccess.get_file_as_string(MONTAGE + "sprites.tsv").split("\n"):
		if line.is_empty(): continue
		var fields = line.strip_edges().split("\t")
		var entry = {"texture": load(MONTAGE + fields[1]), "commands": []}
		by_id[fields[0].to_int()] = entry
		montage.append(entry)
	for line in FileAccess.get_file_as_string(MONTAGE + "commands.tsv").split("\n"):
		if line.is_empty(): continue
		var values = line.strip_edges().split("\t")
		var row: Array[float] = []
		for value in values: row.append(value.to_float())
		by_id[int(row[0])].commands.append(row)

func draw_montage() -> void:
	for entry in montage:
		for row in entry.commands:
			if song_time_ms < row[1] or song_time_ms >= row[2]: continue
			var q: float = (song_time_ms - row[1]) / (row[2] - row[1])
			var position = Vector2(lerpf(row[3], row[5], q), lerpf(row[4], row[6], q))
			var scale_factor = Vector2(lerpf(row[7], row[9], q), lerpf(row[8], row[10], q))
			var angle = lerpf(row[11], row[12], q)
			var alpha = lerpf(row[13], row[14], q)
			var texture: Texture2D = entry.texture
			draw_set_transform(position, angle, scale_factor)
			draw_texture(texture, -texture.get_size() / 2, Color(1, 1, 1, alpha))
			draw_set_transform(Vector2.ZERO)
			break

func read_timeline(file_name: String) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	var file = FileAccess.open(ASSETS + file_name, FileAccess.READ)
	while not file.eof_reached():
		var line = file.get_line()
		if line.is_empty():
			continue
		var fields = line.split("\t")
		var path = ASSETS + fields[2]
		textures[path] = load(path)
		var shot = {"start": fields[0].to_int(), "end": fields[1].to_int(),
			"path": path, "fade_in": fields[3].to_int(), "fade_out": fields[4].to_int()}
		if fields.size() >= 15 and fields[5] == "lyric":
			shot["position"] = Vector2(fields[6].to_float(), fields[7].to_float())
			shot["enter"] = fields[8].to_float()
			shot["leave"] = fields[9].to_float()
			shot["enter_y"] = fields[10].to_float()
			shot["leave_y"] = fields[11].to_float()
			shot["enter_scale"] = fields[12].to_float()
			shot["leave_scale"] = fields[13].to_float()
			shot["initial_alpha"] = fields[14].to_float()
		elif fields.size() >= 9:
			shot["zoom"] = fields[5].to_float()
			shot["cx"] = fields[6].to_float()
			shot["y0"] = fields[7].to_float()
			shot["y1"] = fields[8].to_float()
			shot["full"] = fields.size() >= 10 and fields[9] == "full"
		result.append(shot)
	return result

func pose(song_seconds: float) -> void:
	# Match the shared integer-millisecond timeline at exact frame boundaries.
	song_time_ms = roundf(song_seconds * 1000.0)
	queue_redraw()

func draw_timeline(entries: Array[Dictionary]) -> void:
	for shot in entries:
		if song_time_ms < shot.start or song_time_ms >= shot.end:
			continue
		var alpha = 1.0
		if shot.fade_in > 0:
			alpha *= lerpf(shot.get("initial_alpha", 0.0), 1.0,
				clampf((song_time_ms - shot.start) / shot.fade_in, 0.0, 1.0))
		if shot.fade_out > 0:
			alpha *= clampf((shot.end - song_time_ms) / shot.fade_out, 0.0, 1.0)
		var rect = Rect2(Vector2.ZERO, size)
		if shot.has("position"):
			var position: Vector2 = shot.position
			var scale_factor = 1.0
			if shot.enter > 0:
				var progress = clampf((song_time_ms - shot.start) / shot.enter, 0, 1)
				var eased = 1 - pow(1 - progress, 3)
				position.y += lerpf(shot.enter_y, 0, eased)
				scale_factor *= lerpf(shot.enter_scale, 1, eased)
			if shot.leave > 0:
				var progress = clampf((song_time_ms - (shot.end - shot.leave)) / shot.leave, 0, 1)
				var eased = pow(progress, 3)
				position.y += shot.leave_y * eased
				scale_factor *= lerpf(1, shot.leave_scale, eased)
			var extent: Vector2 = textures[shot.path].get_size() * scale_factor
			rect = Rect2(position - extent / 2, extent)
		elif shot.has("zoom"):
			var progress = clampf((song_time_ms - shot.start) / float(shot.end - shot.start), 0, 1)
			var cy = lerpf(shot.y0, shot.y1, progress)
			var viewport = size if shot.full else Vector2(1728, 972)
			var extent = viewport * float(shot.zoom)
			rect = Rect2(Vector2(960, 540) - Vector2(shot.cx, cy) * extent, extent)
		draw_texture_rect(textures[shot.path], rect, false, Color(1, 1, 1, alpha))

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color.BLACK)
	if song_time_ms < 40000:
		# Map's existing horizontal reveal introduces the first actual bridge card.
		draw_texture_rect(textures[ASSETS + "base-day.png"], Rect2(Vector2.ZERO, size), false)
	else:
		draw_timeline(shots)
		if song_time_ms >= bar_start and song_time_ms < bar_end:
			var progress = clampf((song_time_ms - bar_start) / (bar_settle - bar_start), 0, 1)
			var visible_height = bar_height * (1 - pow(1 - progress, 3))
			draw_rect(Rect2(0, visible_height - bar_height, size.x, bar_height), Color.BLACK)
			draw_rect(Rect2(0, size.y - visible_height, size.x, bar_height), Color.BLACK)
		draw_montage()
		if show_lyrics:
			draw_timeline(lyrics)
