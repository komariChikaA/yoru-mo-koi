extends SceneTree

# Export only the three static title textures consumed by Storybrew.
# Storybrew owns their fade/cut timing; no Godot movie is rendered here.
func _initialize() -> void:
    call_deferred("export_titles")

func export_titles() -> void:
    var destination:=""
    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--out="):destination=argument.trim_prefix("--out=")
    if destination.is_empty():
        push_error("Missing --out=<texture directory>")
        quit(1)
        return
    root.size=Vector2i(1920,1080)
    var title=load("res://ending-title.gd").new()
    root.add_child(title)
    var settings:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://ending.json"))
    var shots:Array=[
        ["title-cast.png",float(settings.title_cast_hit)],
        ["title-silhouette.png",float(settings.title_silhouette_hit)],
        ["title-final.png",float(settings.title_settle_hit)]]
    for shot in shots:
        title.pose(float(shot[1]))
        await RenderingServer.frame_post_draw
        await RenderingServer.frame_post_draw
        var result:=root.get_texture().get_image().save_png(destination.path_join(shot[0]))
        if result!=OK:
            push_error("Title export failed: "+str(shot[0]))
            quit(1)
            return
        print("Exported "+str(shot[0]))
    quit()
