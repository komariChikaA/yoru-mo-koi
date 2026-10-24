extends Control

func _ready() -> void:
    var title_texture: Texture2D = load("res://assets/title-redrawn.svg")
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
    var portrait_mask: Texture2D = load("res://assets/portrait-contour-smooth.svg")
    wash.set_shader_parameter("portrait_mask", portrait_mask)
    art.material = wash
    add_child(art)

    var frame := Node2D.new()
    frame.name = "FineFrame"
    frame.set_script(load("res://cover_frame.gd"))
    add_child(frame)

    # Centre-line vector redraw of the original lettering, with open counters.
    var title := TextureRect.new()
    title.name = "RedrawnLineTitle"
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

    if OS.get_cmdline_user_args().has("--contour-guide"):
        art.material = null
        frame.visible = false
        title.visible = false
        var guide := TextureRect.new()
        guide.texture = portrait_mask
        guide.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
        guide.stretch_mode = TextureRect.STRETCH_SCALE
        guide.size = Vector2(1920, 1080)
        var guide_ink := ShaderMaterial.new()
        guide_ink.shader = load("res://portrait_contour_guide.gdshader")
        guide.material = guide_ink
        add_child(guide)
