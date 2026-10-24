extends SceneTree

func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	var sequence = load("res://sequence.gd").new()
	root.add_child(sequence)
	sequence.fixed_time = 3.85
	await process_frame
	await RenderingServer.frame_post_draw
	var folder := ProjectSettings.globalize_path("res://../../_preview/chorus-photo-phone/")
	sequence.room.get_texture().get_image().save_jpg(folder+"brake-preview-room.jpg",0.85)
	sequence.set_process(false)
	sequence.sms_phone.position = Vector3.ZERO
	sequence.sms_view.get_camera_3d().size = 1.3
	await process_frame
	await RenderingServer.frame_post_draw
	sequence.sms_view.get_texture().get_image().save_png(folder+"brake-preview-phone.png")
	print("BRAKE_PREVIEW_CAPTURED phone_reference_lens=1.3 room_local_time=3.85")
	quit()
