extends Control

func _ready() -> void:
    var art := TextureRect.new()
    art.name = "OriginalCGWithSoftWash"
    art.texture = load("res://assets/cgc16.png")
    art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    art.stretch_mode = TextureRect.STRETCH_SCALE
    art.size = Vector2(1920, 1080)
    var wash := ShaderMaterial.new()
    wash.shader = load("res://cover_wash.gdshader")
    wash.set_shader_parameter("portrait_mask", load("res://assets/cgc16_ren_cutout.png"))
    art.material = wash
    add_child(art)

    # Keep the author's exact original lettering, colours, texture and shadows.
    # The previous per-character crops cut neighbouring letters at their edges;
    # a single source texture preserves the actual original spacing and strokes.
    var title := TextureRect.new()
    title.name = "OriginalTitle"
    title.texture = load("res://assets/title.png")
    title.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
    title.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    title.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    title.position = Vector2(95, 405)
    title.size = Vector2(1730, 358)
    var title_ink := ShaderMaterial.new()
    title_ink.shader = load("res://original_title_ink.gdshader")
    title.material = title_ink
    add_child(title)
