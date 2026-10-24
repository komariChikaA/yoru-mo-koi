extends SceneTree

func _initialize() -> void:
	call_deferred("check")

func check() -> void:
	var skeleton := Skeleton2D.new()
	root.add_child(skeleton)
	var bone := Bone2D.new()
	bone.name = "Hair"
	bone.set_autocalculate_length_and_angle(false)
	bone.set_length(100.0)
	bone.set_bone_angle(0.0)
	bone.rest = Transform2D.IDENTITY
	skeleton.add_child(bone)
	var target := Node2D.new()
	target.name = "Wind"
	target.position = Vector2(100, 0)
	skeleton.add_child(target)
	await process_frame
	var stack := SkeletonModificationStack2D.new()
	var jiggle := SkeletonModification2DJiggle.new()
	jiggle.enabled = true
	jiggle.jiggle_data_chain_length = 1
	jiggle.target_nodepath = NodePath("Wind")
	jiggle.set_jiggle_joint_bone2d_node(0, NodePath("Hair"))
	jiggle.stiffness = 4.0
	jiggle.damping = 0.82
	jiggle.mass = 0.75
	stack.add_modification(jiggle)
	stack.enabled = true
	skeleton.set_modification_stack(stack)
	stack.setup()
	for i in range(360):
		stack.execute(1.0 / 60.0, 0)
	var maximum := 0.0
	for i in range(360):
		target.position.y = 10.0 * sin(TAU * float(i) / 360.0)
		stack.execute(1.0 / 60.0, 0)
		maximum = maxf(maximum, absf(bone.rotation))
	print("NATIVE_JIGGLE_CHECK version=%s bones=%d max_angle_deg=%.4f root=%s" % [Engine.get_version_info().string, skeleton.get_bone_count(), rad_to_deg(maximum), bone.position])
	stack.enabled = false
	quit(0 if maximum > 0.01 and maximum < 0.2 and bone.position == Vector2.ZERO else 1)
