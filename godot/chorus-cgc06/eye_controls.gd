extends Resource
## Edit on the scene root's Eye Controls resource in Godot's Inspector.
## X/Y amounts are the first/second native eye; offsets are native-image pixels.

@export_category("Native Parts")
@export var manual := false
@export var inspect_face := false

@export_group("Eye Body / Upper Lid")
@export var upper_close := Vector2.ZERO
@export var upper_thickness := Vector2(0.78, 0.78)

@export_group("Native Lash Tips")
@export var lash_tip_compress := Vector2(0.60,0.60)
@export var long_tip_min_length := 14.0

@export_group("Lower Lid")
@export var lower_close := Vector2.ZERO
@export var lower_flatten := Vector2(0.94,0.94)
@export var lower_bend := Vector2.ZERO
@export var lower_thickness := Vector2.ONE

@export_group("Eyebrows")
@export var brow_left_offset := Vector2.ZERO
@export var brow_right_offset := Vector2.ZERO
@export var brow_bend := Vector2.ZERO

@export_group("Iris / Pupil")
@export var iris_left_offset := Vector2.ZERO
@export var iris_right_offset := Vector2.ZERO
@export var iris_scale := Vector2.ONE

@export_group("Native Edge Creases")
@export var edge_follow := Vector2.ONE
@export var edge_flatten := Vector2(0.85,1.0)
@export var edge_gap := Vector2(10,22)
@export var edge_left_offset := Vector2.ZERO
@export var edge_right_offset := Vector2.ZERO
@export var edge_details_visible := true

@export_group("Layer Visibility")
@export var eyebrows_visible := true
@export var iris_visible := true
@export var eye_body_visible := true
@export var lower_lids_visible := true

func reset() -> void:
	upper_close=Vector2.ZERO
	upper_thickness=Vector2(0.78,0.78)
	lash_tip_compress=Vector2(0.60,0.60)
	long_tip_min_length=14.0
	lower_close=Vector2.ZERO
	lower_flatten=Vector2(0.94,0.94)
	lower_thickness=Vector2.ONE
	lower_bend=Vector2.ZERO
	brow_left_offset=Vector2.ZERO
	brow_right_offset=Vector2.ZERO
	brow_bend=Vector2.ZERO
	iris_left_offset=Vector2.ZERO
	iris_right_offset=Vector2.ZERO
	iris_scale=Vector2.ONE
	edge_follow=Vector2.ONE
	edge_flatten=Vector2(0.85,1.0)
	edge_gap=Vector2(10,22)
	edge_left_offset=Vector2.ZERO
	edge_right_offset=Vector2.ZERO
	edge_details_visible=true
	eyebrows_visible=true
	iris_visible=true
	eye_body_visible=true
	lower_lids_visible=true
