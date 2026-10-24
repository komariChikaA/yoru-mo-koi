@tool
extends Sprite2D
## A real editor sprite gives the native 2D view visible bounds and F-to-frame.
func _enter_tree() -> void:
	visible=Engine.is_editor_hint()
