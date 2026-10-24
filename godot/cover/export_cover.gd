extends SceneTree

func _initialize() -> void:
    call_deferred("export_cover")

func export_cover() -> void:
    var destination := ""
    var scene_path := "res://cover_refined.tscn"

    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--out="):
            destination = argument.trim_prefix("--out=")
        if argument.begins_with("--scene="):
            scene_path = argument.trim_prefix("--scene=")

    if destination.is_empty():
        destination = "godot_cover_refined.png"

    root.size = Vector2i(1920, 1080)
    var cover_scene: PackedScene = load(scene_path)
    var cover_instance = cover_scene.instantiate()
    root.add_child(cover_instance)

    await RenderingServer.frame_post_draw
    await RenderingServer.frame_post_draw

    var img: Image = root.get_texture().get_image()
    var result := img.save_png(destination)
    if result != OK:
        push_error("Failed to save Godot cover: " + destination)
        quit(1)
        return
    print("Godot cover exported successfully to: " + destination)
    quit(0)
