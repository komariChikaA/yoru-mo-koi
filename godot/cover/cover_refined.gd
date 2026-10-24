extends Control

@export_range(0.0, 1.0, 0.01) var title_underlay_strength := 0.74

func _ready() -> void:
    var title_texture: Texture2D = load("res://assets/title.png")
    var title_size := Vector2(1730, 1730.0 * title_texture.get_height() / title_texture.get_width())
    var title_position := Vector2(95, 405)
    var art := TextureRect.new()
    art.name = "OriginalCGWithSoftWash"
    art.texture = load("res://assets/cgc16.png")
    art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    art.stretch_mode = TextureRect.STRETCH_SCALE
    art.size = Vector2(1920, 1080)
    var wash := ShaderMaterial.new()
    wash.shader = load("res://cover_wash.gdshader")
    wash.set_shader_parameter("portrait_mask", load("res://assets/cgc16_ren_cutout.png"))
    wash.set_shader_parameter("title_texture", title_texture)
    wash.set_shader_parameter("title_rect_px", Vector4(title_position.x, title_position.y, title_size.x, title_size.y))
    wash.set_shader_parameter("underlay_strength", title_underlay_strength)
    art.material = wash
    add_child(art)

    # Keep the author's exact original lettering, colours, texture and shadows.
    # The previous per-character crops cut neighbouring letters at their edges;
    # a single source texture preserves the actual original spacing and strokes.
    var title := TextureRect.new()
    title.name = "OriginalTitle"
    title.texture = title_texture
    title.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
    title.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    title.stretch_mode = TextureRect.STRETCH_SCALE
    title.position = title_position
    title.size = title_size
    var title_ink := ShaderMaterial.new()
    title_ink.shader = load("res://original_title_ink.gdshader")
    title.material = title_ink
    add_child(title)
