extends Node2D

func _draw() -> void:
    var ink := Color(0.54, 0.46, 0.43, 0.46)
    # Leave the upper hair and lower skirt free to break through the frame.
    for segment in [
        [Vector2(90, 82), Vector2(565, 82)],
        [Vector2(1280, 82), Vector2(1830, 82)],
        [Vector2(90, 998), Vector2(690, 998)],
        [Vector2(1605, 998), Vector2(1830, 998)],
        [Vector2(90, 82), Vector2(90, 998)],
        [Vector2(1830, 82), Vector2(1830, 998)],
    ]:
        draw_line(segment[0], segment[1], ink, 0.8, true)

    for corner in [Vector2(90, 82), Vector2(1830, 82), Vector2(90, 998), Vector2(1830, 998)]:
        draw_line(corner - Vector2(10, 0), corner + Vector2(10, 0), ink, 0.8, true)
        draw_line(corner - Vector2(0, 10), corner + Vector2(0, 10), ink, 0.8, true)

    var gold := Color(0.68, 0.57, 0.31, 0.75)
    for centre in [Vector2(548, 82), Vector2(1297, 82), Vector2(673, 998), Vector2(1622, 998)]:
        draw_colored_polygon(PackedVector2Array([
            centre + Vector2(0, -4), centre + Vector2(3, 0),
            centre + Vector2(0, 4), centre + Vector2(-3, 0)]), gold)
