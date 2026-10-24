extends Control
## Fixed screen cards; only the projected map pins and their leaders move.
var camera: Camera3D
var records: Array[Dictionary] = []

func setup(view_camera: Camera3D, pins: Node3D) -> void:
	camera = view_camera
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# A shared proposed home replaces the two actor-route callouts.
	var home: Node3D = pins.get_node("ai")
	home.name = "home"
	home.position = Vector3(-620, 0, -90)
	home.get_node("Title").text = "蓝恋家"
	var former_route_pin = pins.get_node("ren")
	pins.remove_child(former_route_pin)
	former_route_pin.queue_free()
	var font: Font = load("res://assets/fonts/fz-shaoer-map.ttf")
	var entries = {
		"jr": ["JR 神户站", "JR KOBE", Vector2(250, 740)],
		"kumo": ["云 · 神社", "KUMO / SHRINE", Vector2(1088, 42)],
		"kamome": ["鸥 · 港边", "KAMOME / HARBOR", Vector2(812, 886)],
		"shiori": ["紫织 · 家", "SHIORI / HOME*", Vector2(410, 114)],
		"hiiro": ["姬色 · 新家", "HIIRO / HOME*", Vector2(1478, 116)],
		"home": ["蓝恋家", "HOME*", Vector2(110, 520)]
	}
	for pin in pins.get_children():
		var entry: Array = entries[String(pin.name)]
		var color: Color = pin.get_node("Dot").mesh.material.albedo_color
		if pin.name == "home":
			color = Color("928ab1")
		pin.get_node("Dot").visible = false
		var panel = Panel.new()
		panel.size = Vector2(203, 76)
		panel.position = entry[2]
		panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var style = StyleBoxFlat.new()
		style.bg_color = Color("fcfcf8")
		style.border_color = color
		style.set_border_width_all(1)
		style.border_width_left = 4
		style.set_corner_radius_all(6)
		panel.add_theme_stylebox_override("panel", style)
		add_child(panel)
		for index in range(2):
			var words = Label.new()
			words.text = entry[index]
			words.position = Vector2(14, 7 + index * 35)
			words.add_theme_font_override("font", font)
			words.add_theme_font_size_override("font_size", 26 if index == 0 else 17)
			words.add_theme_color_override("font_color", Color("334a55") if index == 0 else Color("657781"))
			panel.add_child(words)
		records.append({"pin": pin, "panel": panel, "color": color,
			"anchor": Vector2.ZERO, "join": Vector2.ZERO, "alpha": 0.0})

func pose() -> void:
	for record in records:
		var pin: Node3D = record.pin
		var title: Label3D = pin.get_node("Title")
		var panel: Panel = record.panel
		record.alpha = title.modulate.a if pin.is_visible_in_tree() else 0.0
		title.visible = false
		panel.visible = record.alpha > 0.001 and not camera.is_position_behind(pin.global_position)
		if not panel.visible:
			record.alpha = 0.0
			continue
		record.anchor = camera.unproject_position(pin.global_position)
		panel.modulate.a = record.alpha
		record.join = Vector2(panel.position.x if record.anchor.x < panel.position.x + panel.size.x * 0.5 else panel.position.x + panel.size.x, clampf(record.anchor.y, panel.position.y + 12, panel.position.y + panel.size.y - 12))
	queue_redraw()

func _draw() -> void:
	for record in records:
		if record.alpha <= 0.001:
			continue
		var color: Color = record.color
		color.a = record.alpha
		var paper = Color(1, 1, 0.98, record.alpha)
		draw_line(record.anchor, record.join, paper, 6.0, true)
		draw_line(record.anchor, record.join, color, 2.0, true)
		draw_circle(record.anchor, 10.0, paper, true, -1.0, true)
		draw_circle(record.anchor, 6.0, color, true, -1.0, true)
