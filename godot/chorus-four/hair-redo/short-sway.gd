extends "res://wind-field.gd"
## Loose-section wind: middle-weighted curvature and a continuous support fade.

var wind_time_offset := 0.0
var active_joint_weights: Array[float] = []

func field(t: float, point: Vector2, seed: float) -> float:
	# The cliff preview keeps a prevailing lift between stronger advected gusts.
	# Standalone previews and the production rebuilt adapter share this field.
	var travel := point.dot(wind_direction.normalized())/propagation_speed
	var phase := TAU*(t-travel)/cycle
	var gust := pow(0.5+0.5*sin(phase+0.4), 3.0)
	var eddy := sin(2.0*phase+seed)*0.6+sin(3.0*phase-seed*0.7)*0.4
	return clampf(0.28+0.70*gust+0.14*eddy, 0.12, 1.0)

func _joint_weight(index: int, count: int) -> float:
	# Curvature is distributed around the loose section's middle. The support
	# has zero turn; progressively smaller proximal turns avoid a root hinge.
	# The final bone has no downstream span and receives no angle budget.
	if not active_joint_weights.is_empty():
		return active_joint_weights[index]
	var u := clampf(float(index-1)/float(maxi(1, count-2)), 0.0, 1.0)
	return pow(sin(PI*u), 1.5)

func _bake(data: Dictionary) -> void:
	active_joint_weights.clear()
	var length := 0.0
	var stations: Array[float] = [0.0, 0.0]
	for i in range(2, data.points.size()):
		length += data.points[i].distance_to(data.points[i-1])
		stations.append(length)
	var control_length := float(data.definition.get("bend_length_px", 0.0))
	if control_length <= 0.0:
		control_length = length
	for i in range(stations.size()):
		var u := clampf(stations[i]/control_length, 0.0, 1.0)
		active_joint_weights.append(pow(sin(PI*u), 1.5) if i > 0 and stations[i] < control_length else 0.0)
	super._bake(data)
	var gain := float(data.definition.get("motion_gain", 1.0))
	for index in range(data.poses.size()):
		# The wind bake shares its closed-loop endpoint with frame zero. Copy it
		# before scaling so the first pose does not receive the gain twice.
		var values: PackedFloat32Array = data.poses[index].duplicate()
		for i in range(values.size()):
			values[i] *= gain
		data.poses[index] = values
	print("SHORT_GAIN %s gain=%.3f" % [data.definition.name, gain])

func _axis_samples(low: float, high: float, anchors: Array) -> Array[float]:
	var result: Array[float] = [low, high]
	for step in range(1, ceili((high-low)/8.0)):
		result.append(minf(low+8.0*step, high))
	for value in anchors:
		var sample := float(value)
		if sample > low and sample < high:
			result.append(sample)
	result.sort()
	var unique: Array[float] = []
	for value in result:
		if unique.is_empty() or value-unique[-1] > 0.001:
			unique.append(value)
	return unique

func _make_mesh(data: Dictionary) -> void:
	var mesh := Polygon2D.new()
	mesh.name = "ShortHairMesh"
	mesh.z_index = -int(data.definition.get("draw_depth", 0))
	mesh.texture = data.definition.texture_object as Texture2D
	add_child(mesh)
	mesh.skeleton = mesh.get_path_to(data.skeleton)
	var line: Array = data.definition.cut_line
	var origin := Vector2(float(line[0][0]), float(line[0][1]))
	var cross_axis := (Vector2(float(line[1][0]), float(line[1][1]))-origin).normalized()
	var free_axis := cross_axis.orthogonal()
	if free_axis.dot(data.points[2]-data.points[1]) < 0.0:
		free_axis = -free_axis
	var band := float(data.definition.root_band)
	var graded: bool = data.definition.get("motion_profile", "") == "midspan-gradient"
	data.graded = graded
	var lengths: Array[float] = [0.0]
	for i in range(1, data.points.size()):
		lengths.append(lengths[-1]+data.points[i].distance_to(data.points[i-1]))
	var total_length := lengths[-1]-lengths[1]
	var control_length := float(data.definition.get("bend_length_px", 0.0))
	if control_length <= 0.0:
		control_length = total_length
	var release := maxf(band, control_length*float(data.definition.get("release_fraction", 0.5)))
	data.release_length = release
	data.total_length = total_length
	data.manual_strip = (data.definition.deformation_model == "supported-strip" and not graded) or data.definition.get("gradient_solver", "chain") == "transverse"
	var box: Array = data.definition.bounds
	var low_cross := INF
	var high_cross := -INF
	var low_free := INF
	var high_free := -INF
	for x in [float(box[0]), float(box[2])]:
		for y in [float(box[1]), float(box[3])]:
			var delta := Vector2(x, y)-origin
			low_cross = minf(low_cross, delta.dot(cross_axis))
			high_cross = maxf(high_cross, delta.dot(cross_axis))
			low_free = minf(low_free, delta.dot(free_axis))
			high_free = maxf(high_free, delta.dot(free_axis))
	# Explicit seam rows prevent triangles interpolating motion across the fixed line.
	var columns := _axis_samples(low_cross, high_cross, [])
	var rows := _axis_samples(low_free, high_free, [0.0, band*0.5, band])
	var vertices := PackedVector2Array()
	var triangles: Array[PackedInt32Array] = []
	var weights: Array[PackedFloat32Array] = []
	var fixed := PackedInt32Array()
	for unused in data.bones:
		weights.append(PackedFloat32Array())
	for distance in rows:
		for across in columns:
			var p := origin+cross_axis*across+free_axis*distance
			vertices.append(p)
			var nearest := INF
			var along := 0.0
			var arc := 0.0
			for i in range(data.points.size()-1):
				var a: Vector2 = data.points[i]
				var b: Vector2 = data.points[i+1]
				var u := clampf((p-a).dot(b-a)/(b-a).length_squared(), 0.0, 1.0)
				var separation := p.distance_squared_to(a.lerp(b, u))
				if separation < nearest:
					nearest = separation
					along = float(i)+u
					arc = lerpf(lengths[i], lengths[i+1], u)-lengths[1]
			var lower := mini(floori(along), data.bones.size()-2)
			var blend := smoothstep(0.0, 1.0, along-float(lower))
			var motion := 0.0 if distance <= 0.0 else smoothstep(0.0, band, distance)
			if graded:
				# Follow distance along the actual lock, including a returning U,
				# rather than treating its vertical projection as another root.
				motion = smoothstep(0.0, release, arc)
				var proximal := 1.0-smoothstep(band, release, arc)
				motion *= lerpf(1.0, smoothstep(0.0, band, distance), proximal)
				if data.definition.get("pin_return_tip", false):
					motion *= 1.0-smoothstep(total_length*0.65, total_length, arc)
			if graded and data.manual_strip:
				var fixed_return := 8.0 if data.definition.get("pin_return_tip", false) else 0.0
				motion = smoothstep(fixed_return, release, distance)
			if motion == 0.0:
				fixed.append(vertices.size()-1)
			for i in range(data.bones.size()):
				var weight := 0.0
				if i == lower:
					weight += 1.0-blend
				if i == lower+1:
					weight += blend
				weight *= motion
				if i == 0:
					weight += 1.0-motion
				weights[i].append(weight)
	for y in range(rows.size()-1):
		for x in range(columns.size()-1):
			var a := y*columns.size()+x
			triangles.append(PackedInt32Array([a, a+1, a+columns.size()+1]))
			triangles.append(PackedInt32Array([a, a+columns.size()+1, a+columns.size()]))
	mesh.polygon = vertices
	mesh.uv = vertices
	mesh.polygons = triangles
	var rests: Array[Transform2D] = []
	for i in range(data.bones.size()):
		mesh.add_bone(data.skeleton.get_path_to(data.bones[i]), weights[i])
		rests.append(data.skeleton.global_transform.affine_inverse()*data.bones[i].global_transform)
	data.mesh = mesh
	data.fixed_vertices = fixed
	var fixed_flags := PackedByteArray()
	fixed_flags.resize(vertices.size())
	for index in fixed:
		fixed_flags[index] = 1
	data.fixed_flags = fixed_flags
	data.skin_weights = weights
	data.rest_transforms = rests
	# Inspect only triangles that actually carry native hair alpha. Transparent
	# corners of the rectangular mesh must not count as visible folds.
	var native_image: Image = (data.definition.texture_object as Texture2D).get_image()
	var visible_triangles: Array[PackedInt32Array] = []
	for triangle in triangles:
		var a: Vector2 = vertices[triangle[0]]
		var b: Vector2 = vertices[triangle[1]]
		var c: Vector2 = vertices[triangle[2]]
		var visible := false
		for point in [a, b, c, (a+b+c)/3.0]:
			var pixel := Vector2i(roundi(point.x), roundi(point.y))
			if pixel.x >= 0 and pixel.y >= 0 and pixel.x < native_image.get_width() and pixel.y < native_image.get_height():
				if native_image.get_pixelv(pixel).a > 0.03:
					visible = true
		if visible:
			visible_triangles.append(triangle)
	data.visible_triangles = visible_triangles
	data.rest_vertices = vertices
	data.free_axis = free_axis
	data.cross_axis = cross_axis
	data.seam_origin = origin
	data.rows = rows
	data.columns = columns
	var free_length := 1.0
	for triangle in visible_triangles:
		for index in triangle:
			free_length = maxf(free_length, (vertices[index]-origin).dot(free_axis))
	data.free_length = free_length
	if data.manual_strip:
		# A wide fixed cross-section cannot rotate around a single central root:
		# that compresses the distant end of the seam into folded triangles.
		mesh.skeleton = NodePath()
		mesh.clear_bones()
		data.deformed_vertices = vertices
	print("SHORT_MESH %s vertices=%d fixed=%d band_px=%.1f" % [data.definition.name, vertices.size(), fixed.size(), band])

func pose(time: float, amount: float) -> void:
	super.pose(time+wind_time_offset, amount)
	for data in strands:
		if not data.manual_strip:
			continue
		var bend := 0.0
		for bone in data.bones:
			bend += bone.rotation
		if data.graded and data.definition.get("pin_return_tip", false):
			# This U returns under a fixed native garment/root. Its middle is
			# wind-driven while both concealed attachments stay in place.
			bend = 0.0
			for bone in data.bones:
				bend += absf(bone.rotation)
			bend *= signf((data.points[2]-data.points[1]).cross(wind_direction))
		var posed := PackedVector2Array()
		var offset := Vector2.ZERO
		var previous := 0.0
		# Out-of-frame texture continuation must not dilute the visible lock's bend.
		var bend_length := float(data.definition.get("bend_length_px", 0.0))
		if bend_length <= 0.0:
			bend_length = data.free_length
		for value in data.rows:
			var distance := float(value)
			if data.graded:
				# A broad bang and a two-ended return loop use transverse
				# middle/tip controls: quadratic release gives zero root slope,
				# visible proximal response and no rotating wide cross-section.
				var fixed_return := 8.0 if data.definition.get("pin_return_tip", false) else 0.0
				var u := clampf((distance-fixed_return)/(bend_length-fixed_return), 0.0, 1.0)
				offset = -data.free_axis.orthogonal()*(bend_length*sin(bend)*1.3*u*u)
			elif distance > 0.0:
				var steps := maxi(1, ceili((distance-previous)/2.0))
				var step_length := (distance-previous)/steps
				for step in range(steps):
					var position := previous+(step+0.5)*step_length
					var angle := 2.0*bend*smoothstep(0.0, bend_length, position)
					# Keep the strip's transverse rows ordered even in a strong gust.
					# Smooth saturation retains the changing wind without flattening
					# the hair at a hard angle clamp or turning the mesh inside out.
					var limit := deg_to_rad(80.0)
					angle = limit*tanh(angle/limit)
					# Arc-length integration bends each transverse row together;
					# displacement and slope are both zero at the fixed seam.
					# Vector2.orthogonal() returns (y, -x); its negative matches
					# the skeleton's positive rotation direction.
					offset += (data.free_axis*(cos(angle)-1.0)-data.free_axis.orthogonal()*sin(angle))*step_length
				previous = distance
			for across in data.columns:
				posed.append(data.seam_origin+data.cross_axis*across+data.free_axis*distance+offset)
		data.deformed_vertices = posed
		data.mesh.polygon = posed

func pin_metrics() -> Dictionary:
	var displacement := 0.0
	var support_displacement := 0.0
	var fixed_count := 0
	var weight_error := 0.0
	var visible_displacement := 0.0
	var min_area_ratio := 1.0
	var folded := 0
	var per_part := {}
	for data in strands:
		var part_min_area := 1.0
		var part_folded := 0
		var part_displacement := 0.0
		var current: Array[Transform2D] = []
		var skin_transforms: Array[Transform2D] = []
		for bone in data.bones:
			current.append(data.skeleton.global_transform.affine_inverse()*bone.global_transform)
		for i in range(current.size()):
			skin_transforms.append(current[i]*data.rest_transforms[i].affine_inverse())
		var support: Vector2 = data.points[1]
		support_displacement = maxf(support_displacement, current[1].origin.distance_to(support))
		var transformed := PackedVector2Array()
		for index in range(data.rest_vertices.size()):
			var vertex: Vector2 = data.rest_vertices[index]
			var moved := Vector2.ZERO
			if data.manual_strip:
				moved = data.deformed_vertices[index]-vertex
			else:
				for i in range(data.bones.size()):
					var weight: float = data.skin_weights[i][index]
					if i > 0 and data.fixed_flags[index] != 0:
						weight_error = maxf(weight_error, absf(weight))
					if weight == 0.0 or current[i] == data.rest_transforms[i]:
						continue
					moved += (skin_transforms[i]*vertex-vertex)*weight
			transformed.append(vertex+moved)
			if data.fixed_flags[index] != 0:
				fixed_count += 1
				displacement = maxf(displacement, moved.length())
		for triangle in data.visible_triangles:
			var a: Vector2 = data.rest_vertices[triangle[0]]
			var b: Vector2 = data.rest_vertices[triangle[1]]
			var c: Vector2 = data.rest_vertices[triangle[2]]
			var ta := transformed[triangle[0]]
			var tb := transformed[triangle[1]]
			var tc := transformed[triangle[2]]
			var ratio := (tb-ta).cross(tc-ta)/(b-a).cross(c-a)
			part_min_area = minf(part_min_area, ratio)
			min_area_ratio = minf(min_area_ratio, ratio)
			if ratio <= 0.0:
				folded += 1
				part_folded += 1
			for index in triangle:
				visible_displacement = maxf(visible_displacement, transformed[index].distance_to(data.rest_vertices[index]))
				part_displacement = maxf(part_displacement, transformed[index].distance_to(data.rest_vertices[index]))
		per_part[data.definition.name] = {"max_displacement_px": part_displacement,
			"min_area_ratio": part_min_area, "folded_triangles": part_folded}
	return {"fixed_vertices": fixed_count, "fixed_max_displacement_px": displacement,
		"support_max_displacement_px": support_displacement, "fixed_moving_weight_max": weight_error,
		"visible_max_displacement_px": visible_displacement, "visible_min_area_ratio": min_area_ratio,
		"visible_folded_triangles": folded, "per_part": per_part}
