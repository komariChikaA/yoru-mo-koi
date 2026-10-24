extends Node2D
## Independent RGBA hair meshes, driven by Godot's native 2D Jiggle modifier.
## Bake a settled cycle so scrubbing and Movie Maker use the same pose.

var strands: Array[Dictionary] = []
var cycle := 6.0
var sample_rate := 120.0
var show_bones := false

func build(definitions: Array, seconds: float) -> void:
	cycle = seconds
	for child in get_children():
		remove_child(child)
		child.queue_free()
	strands.clear()
	for definition in definitions:
		var skeleton := Skeleton2D.new()
		skeleton.name = str(definition.name).replace("-", "_")
		add_child(skeleton)
		var points := PackedVector2Array()
		for point in definition.chain:
			points.append(Vector2(float(point[0]), float(point[1])))
		var bones: Array[Bone2D] = []
		var targets: Array[Node2D] = []
		var stack := SkeletonModificationStack2D.new()
		stack.enabled = true
		for i in range(points.size()):
			var bone := Bone2D.new()
			bone.name = "Joint%d" % i
			bone.position = points[i] if i == 0 else points[i] - points[i-1]
			bone.rest = Transform2D(0.0, bone.position)
			bone.set_autocalculate_length_and_angle(false)
			var direction := points[mini(i+1, points.size()-1)] - points[i]
			if i == points.size()-1:
				direction = points[i] - points[i-1]
			bone.set_length(direction.length())
			bone.set_bone_angle(direction.angle())
			if i == 0:
				skeleton.add_child(bone)
			else:
				bones[i-1].add_child(bone)
			bones.append(bone)
			var target := Node2D.new()
			target.name = "Wind%d" % i
			target.position = points[i] + direction
			skeleton.add_child(target)
			targets.append(target)
			if i > 0:
				var jiggle := SkeletonModification2DJiggle.new()
				jiggle.enabled = true
				jiggle.jiggle_data_chain_length = 1
				jiggle.target_nodepath = skeleton.get_path_to(target)
				jiggle.set_jiggle_joint_bone2d_node(0, skeleton.get_path_to(bone))
				jiggle.stiffness = float(definition.stiffness)
				jiggle.damping = float(definition.damping)
				jiggle.mass = float(definition.mass) * (1.0 + 0.12*i)
				stack.add_modification(jiggle)
		skeleton.set_modification_stack(stack)
		stack.setup()
		var data := {"skeleton": skeleton, "bones": bones, "targets": targets,
			"points": points, "definition": definition, "stack": stack}
		_make_mesh(data)
		_bake(data)
		strands.append(data)
	print("HAIR_SWAY_READY native=SkeletonModification2DJiggle strands=%d" % strands.size())

func _make_mesh(data: Dictionary) -> void:
	var mesh := Polygon2D.new()
	mesh.texture = load("res://" + str(data.definition.texture))
	mesh.name = "HairMesh"
	add_child(mesh)
	mesh.skeleton = mesh.get_path_to(data.skeleton)
	var box: Array = data.definition.bounds
	var nx := maxi(2, ceili((float(box[2])-float(box[0])) / 20.0))
	var ny := maxi(2, ceili((float(box[3])-float(box[1])) / 20.0))
	var vertices := PackedVector2Array()
	var triangles: Array[PackedInt32Array] = []
	var weights: Array[PackedFloat32Array] = []
	for unused in data.bones:
		weights.append(PackedFloat32Array())
	for y in range(ny+1):
		for x in range(nx+1):
			var p := Vector2(lerpf(float(box[0]), float(box[2]), float(x)/nx),
				lerpf(float(box[1]), float(box[3]), float(y)/ny))
			vertices.append(p)
			var nearest := INF
			var along := 0.0
			for i in range(data.points.size()-1):
				var a: Vector2 = data.points[i]
				var b: Vector2 = data.points[i+1]
				var u := clampf((p-a).dot(b-a)/(b-a).length_squared(), 0.0, 1.0)
				var distance := p.distance_squared_to(a.lerp(b, u))
				if distance < nearest:
					nearest = distance
					along = float(i) + u
			var lower := mini(floori(along), data.bones.size()-2)
			var blend := smoothstep(0.0, 1.0, along-float(lower))
			var fixed_tip := 0.0
			if data.definition.get("pin_tip", false):
				fixed_tip = smoothstep(float(data.bones.size()-2), float(data.bones.size()-1), along)
			var cap_motion := 1.0
			for cap in ["root_pin", "tip_pin"]:
				if data.definition.get(cap) != null:
					var anchor: Vector2 = data.points[0] if cap == "root_pin" else data.points[-1]
					var radius := float(data.definition[cap][1])+2.0
					cap_motion *= smoothstep(radius,radius+40.0,p.distance_to(anchor))
			for i in range(data.bones.size()):
				var w := 0.0
				if i == lower:
					w += 1.0-blend
				if i == lower+1:
					w += blend
				w *= (1.0-fixed_tip)*cap_motion
				if i == 0:
					w += 1.0-(1.0-fixed_tip)*cap_motion
				weights[i].append(w)
	for y in range(ny):
		for x in range(nx):
			var a := y*(nx+1)+x
			triangles.append(PackedInt32Array([a, a+1, a+nx+2]))
			triangles.append(PackedInt32Array([a, a+nx+2, a+nx+1]))
	mesh.polygon = vertices
	mesh.uv = vertices
	mesh.polygons = triangles
	for i in range(data.bones.size()):
		mesh.add_bone(data.skeleton.get_path_to(data.bones[i]), weights[i])
	if data.definition.get("shadow") != null:
		var settings: Dictionary = data.definition.shadow
		var shadow := mesh.duplicate() as Polygon2D
		shadow.name = "SkinShadow"
		add_child(shadow)
		move_child(shadow, mesh.get_index())
		shadow.skeleton = shadow.get_path_to(data.skeleton)
		shadow.position = Vector2(float(settings.offset[0]),float(settings.offset[1]))
		shadow.texture = load(str(mesh.texture.resource_path).replace("hair-", "hair-shadow-"))
		var material := ShaderMaterial.new()
		material.shader = load("res://hair-shadow.gdshader")
		material.set_shader_parameter("receiver",load(str(mesh.texture.resource_path).replace("hair-", "hair-receiver-")))
		material.set_shader_parameter("ink",Color(float(settings.color[0]),float(settings.color[1]),float(settings.color[2]),float(settings.opacity)))
		shadow.material = material
	data.mesh = mesh

func _bake(data: Dictionary) -> void:
	var steps := roundi(cycle*sample_rate)
	var poses: Array[PackedFloat32Array] = []
	# Warm up the actual native solver before recording one repeating wind cycle.
	for step in range(steps*6+1):
		var t := float(step % steps)/sample_rate
		for i in range(1, data.bones.size()):
			var bone: Bone2D = data.bones[i]
			var direction: Vector2 = Vector2.from_angle(bone.get_bone_angle()) * maxf(bone.get_length(), 70.0)
			var parent: Bone2D = data.bones[i-1]
			direction = direction.rotated(parent.global_rotation)
			var phase := float(data.definition.phase) + 0.23*i
			var wave := sin(TAU*t/cycle + phase) + 0.16*sin(2.0*TAU*t/cycle + phase)
			var wind := direction.orthogonal().normalized() * float(data.definition.sway) * wave
			data.targets[i].global_position = bone.global_position + direction + wind
		data.stack.execute(1.0/sample_rate, 0)
		if step >= steps*5:
			var pose := PackedFloat32Array()
			for bone in data.bones:
				pose.append(bone.rotation)
			poses.append(pose)
	data.stack.enabled = false
	for i in range(data.bones.size()):
		data.skeleton.set_bone_local_pose_override(i, Transform2D.IDENTITY, 0.0, false)
		data.bones[i].rotation = 0.0
	# The settled endpoints should agree; measure before closing the sampled loop.
	var seam := 0.0
	for i in range(data.bones.size()):
		seam = maxf(seam, absf(poses[0][i]-poses[-1][i]))
	print("HAIR_NATIVE_BAKE %s joints=%d seam_deg=%.6f" % [data.definition.name, data.bones.size(), rad_to_deg(seam)])
	poses[-1] = poses[0]
	data.poses = poses

func pose(time: float, amount: float) -> void:
	var sample := fposmod(time, cycle)*sample_rate
	var index := floori(sample)
	var blend := sample-float(index)
	for data in strands:
		for i in range(data.bones.size()):
			data.bones[i].rotation = lerp_angle(data.poses[index][i], data.poses[index+1][i], blend)*amount
	queue_redraw()

func _draw() -> void:
	if not show_bones:
		return
	for data in strands:
		for i in range(data.bones.size()):
			var point: Vector2 = to_local(data.bones[i].global_position)
			draw_circle(point, 5.0, Color(1.0, 0.7, 0.2))
			if i > 0:
				draw_line(to_local(data.bones[i-1].global_position), point, Color(1.0, 0.7, 0.2), 2.0)
