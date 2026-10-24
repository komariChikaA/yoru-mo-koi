extends Node2D
## Arc-length hair ribbons. Native UVs and one reviewed RGBA per natural lock
## stay intact; only the sampled centerline and its transported frame move.

@export var wind_direction := Vector2(-1.0, -0.24)
@export var propagation_speed := 850.0
var wind_time_offset := 0.0
var cycle := 5.6
var show_bones := false
var strands: Array[Dictionary] = []


func _catmull(a: Vector2, b: Vector2, c: Vector2, d: Vector2, u: float) -> Vector2:
	return 0.5 * ((2.0*b) + (-a+c)*u + (2.0*a-5.0*b+4.0*c-d)*u*u + (-a+3.0*b-3.0*c+d)*u*u*u)


func _resample(chain: Array) -> PackedVector2Array:
	var controls := PackedVector2Array()
	# The adapter prepends a concealed anchor; index one is the true support.
	for i in range(1, chain.size()):
		controls.append(Vector2(float(chain[i][0]), float(chain[i][1])))
	var dense := PackedVector2Array()
	for i in range(controls.size()-1):
		var divisions := maxi(4, ceili(controls[i].distance_to(controls[i+1])/4.0))
		for j in range(divisions):
			dense.append(_catmull(controls[maxi(0, i-1)], controls[i], controls[i+1], controls[mini(controls.size()-1, i+2)], float(j)/divisions))
	dense.append(controls[-1])
	var lengths := PackedFloat32Array([0.0])
	for i in range(1, dense.size()):
		lengths.append(lengths[-1]+dense[i].distance_to(dense[i-1]))
	var count := maxi(3, ceili(lengths[-1]/12.0)+1)
	var result := PackedVector2Array()
	var index := 0
	for i in range(count):
		var arc := lengths[-1]*float(i)/float(count-1)
		while index < dense.size()-2 and lengths[index+1] < arc:
			index += 1
		var blend := (arc-lengths[index])/maxf(0.0001, lengths[index+1]-lengths[index])
		result.append(dense[index].lerp(dense[index+1], blend))
	return result


func _tangents(points: PackedVector2Array) -> PackedVector2Array:
	var result := PackedVector2Array()
	for i in range(points.size()):
		result.append((points[mini(i+1, points.size()-1)]-points[maxi(0, i-1)]).normalized())
	return result


func _axis_samples(low: float, high: float, anchors: Array) -> Array[float]:
	var values: Array[float] = [low, high]
	for step in range(1, ceili((high-low)/8.0)):
		values.append(minf(low+8.0*step, high))
	for anchor in anchors:
		if float(anchor) > low and float(anchor) < high:
			values.append(float(anchor))
	values.sort()
	var result: Array[float] = []
	for value in values:
		if result.is_empty() or value-result[-1] > 0.001:
			result.append(value)
	return result


func build(definitions: Array, seconds: float) -> void:
	cycle = seconds
	for child in get_children():
		remove_child(child)
		child.queue_free()
	strands.clear()
	for definition in definitions:
		var points := _resample(definition.chain)
		var lengths := PackedFloat32Array([0.0])
		for i in range(1, points.size()):
			lengths.append(lengths[-1]+points[i].distance_to(points[i-1]))
		var control_length := float(definition.get("bend_length_px", 0.0))
		if control_length <= 0.0:
			control_length = lengths[-1]
		var line: Array = definition.cut_line
		var seam := Vector2(float(line[0][0]), float(line[0][1]))
		var cross_axis := (Vector2(float(line[1][0]), float(line[1][1]))-seam).normalized()
		var free_axis := cross_axis.orthogonal()
		if free_axis.dot(points[1]-points[0]) < 0.0:
			free_axis = -free_axis
		var data := {"definition": definition, "points": points, "lengths": lengths,
			"rest_tangents": _tangents(points), "total_length": lengths[-1],
			"control_length": maxf(lengths[1]+1.0, control_length),
			"seam_origin": seam, "cross_axis": cross_axis, "free_axis": free_axis,
			"root_band": float(definition.get("root_band", 16.0)),
			"pin_return_tip": bool(definition.get("pin_return_tip", false)),
			"amplitude_deg": float(definition.get("reference_amplitude_deg", 0.45*float(definition.get("sway_percent", 10.0)))),
			"lag": float(definition.get("reference_lag", 0.28)),
			"wavelength": float(definition.get("reference_wavelength", maxf(280.0, control_length*1.2))),
			"phase": float(definition.get("reference_phase", 0.0))}
		_make_mesh(data)
		data.safety_cache = {}
		strands.append(data)
	pose(0.0, 1.0)
	print("REFERENCE_WIND_READY strands=%d native_uv=true old_gain=false" % strands.size())


func _make_mesh(data: Dictionary) -> void:
	var mesh := Polygon2D.new()
	mesh.name = str(data.definition.name)
	mesh.z_index = -int(data.definition.get("draw_depth", 0))
	mesh.texture = data.definition.texture_object as Texture2D
	add_child(mesh)
	var box: Array = data.definition.bounds
	var low_cross := INF
	var high_cross := -INF
	var low_free := INF
	var high_free := -INF
	for x in [float(box[0]), float(box[2])]:
		for y in [float(box[1]), float(box[3])]:
			var delta := Vector2(x, y)-Vector2(data.seam_origin)
			low_cross = minf(low_cross, delta.dot(data.cross_axis))
			high_cross = maxf(high_cross, delta.dot(data.cross_axis))
			low_free = minf(low_free, delta.dot(data.free_axis))
			high_free = maxf(high_free, delta.dot(data.free_axis))
	var columns := _axis_samples(low_cross, high_cross, [])
	var rows := _axis_samples(low_free, high_free, [0.0, float(data.root_band)*0.5, float(data.root_band)])
	var vertices := PackedVector2Array()
	var mappings := PackedVector4Array()
	var influence := PackedFloat32Array()
	var fixed := PackedByteArray()
	var points: PackedVector2Array = data.points
	var tangents: PackedVector2Array = data.rest_tangents
	var lengths: PackedFloat32Array = data.lengths
	var release := maxf(float(data.root_band), float(data.control_length)*0.5)
	for distance in rows:
		for across in columns:
			var point: Vector2 = data.seam_origin+data.cross_axis*across+data.free_axis*distance
			vertices.append(point)
			var nearest := INF
			var best_index := 0
			var best_blend := 0.0
			for i in range(points.size()-1):
				var segment := points[i+1]-points[i]
				var blend := clampf((point-points[i]).dot(segment)/segment.length_squared(), 0.0, 1.0)
				var separation := point.distance_squared_to(points[i].lerp(points[i+1], blend))
				if separation < nearest:
					nearest = separation
					best_index = i
					best_blend = blend
			var center := points[best_index].lerp(points[best_index+1], best_blend)
			var tangent := tangents[best_index].lerp(tangents[best_index+1], best_blend).normalized()
			var offset := point-center
			mappings.append(Vector4(best_index, best_blend, offset.dot(tangent), offset.dot(tangent.orthogonal())))
			var arc := lerpf(lengths[best_index], lengths[best_index+1], best_blend)
			# The cross-section pins the support. Further along a returning lock,
			# projection towards that line no longer resets its arc-length age.
			var proximal := 1.0-smoothstep(release, release*1.5, arc)
			var gate := lerpf(1.0, smoothstep(0.0, float(data.root_band), distance), proximal)
			if data.pin_return_tip:
				gate *= smoothstep(0.0, maxf(float(data.root_band), float(data.total_length)*0.35), float(data.total_length)-arc)
			influence.append(gate)
			fixed.append(1 if gate == 0.0 else 0)
	var triangles: Array[PackedInt32Array] = []
	for y in range(rows.size()-1):
		for x in range(columns.size()-1):
			var a := y*columns.size()+x
			triangles.append(PackedInt32Array([a, a+1, a+columns.size()+1]))
			triangles.append(PackedInt32Array([a, a+columns.size()+1, a+columns.size()]))
	mesh.polygon = vertices
	mesh.uv = vertices
	mesh.polygons = triangles
	var image: Image = mesh.texture.get_image()
	var visible_triangles: Array[PackedInt32Array] = []
	for triangle in triangles:
		var a := vertices[triangle[0]]
		var b := vertices[triangle[1]]
		var c := vertices[triangle[2]]
		for point in [a, b, c, (a+b+c)/3.0]:
			var pixel := Vector2i(roundi(point.x), roundi(point.y))
			if Rect2i(Vector2i.ZERO, image.get_size()).has_point(pixel) and image.get_pixelv(pixel).a > 0.03:
				visible_triangles.append(triangle)
				break
	data.mesh = mesh
	data.rest_vertices = vertices
	data.deformed_vertices = vertices
	data.mappings = mappings
	data.influence = influence
	data.fixed_flags = fixed
	data.visible_triangles = visible_triangles
	if data.pin_return_tip:
		_make_return_blends(data)


func _make_return_blends(data: Dictionary) -> void:
	# The filled belly of a U lies between two centerline branches. A closest
	# branch switch is discontinuous there, even though its native alpha is
	# solid. Blend local rigid frames smoothly in rest space instead.
	var stations: PackedVector2Array = data.points
	var source_vertices: PackedVector2Array = data.rest_vertices
	var indices: Array[PackedInt32Array] = []
	var weights: Array[PackedFloat32Array] = []
	for vertex in range(source_vertices.size()):
		var point := source_vertices[vertex]
		var nearest := INF
		for station in stations:
			nearest = minf(nearest, point.distance_to(station))
		var radius := nearest+64.0
		var local_indices := PackedInt32Array()
		var local_weights := PackedFloat32Array()
		var total := 0.0
		for i in range(stations.size()):
			var q := point.distance_to(stations[i])/radius
			if q < 1.0:
				var weight := pow(1.0-q, 4.0)*(4.0*q+1.0)
				local_indices.append(i)
				local_weights.append(weight)
				total += weight
		for i in range(local_weights.size()):
			local_weights[i] /= total
		indices.append(local_indices)
		weights.append(local_weights)
	data.return_indices = indices
	data.return_weights = weights


func _curve(data: Dictionary, time: float, amount: float) -> PackedVector2Array:
	var rest: PackedVector2Array = data.points
	var lengths: PackedFloat32Array = data.lengths
	var flow := wind_direction.normalized()
	var heading := (rest[mini(rest.size()-1, 3)]-rest[0]).normalized()
	var cross := heading.cross(flow)
	var turn := signf(cross) if absf(cross) > 0.001 else 1.0
	var amplitude := deg_to_rad(float(data.amplitude_deg))*amount*turn
	var angles := PackedFloat32Array()
	for i in range(rest.size()):
		var controlled_arc := minf(lengths[i], float(data.control_length))
		var u := clampf((controlled_arc-lengths[1])/(float(data.control_length)-lengths[1]), 0.0, 1.0)
		var envelope := u*u*(3.0-2.0*u)
		# Sample the same advected wind field for every lock. The small traveling
		# term rides a sustained main bend instead of alternating whole sections.
		var sample_position := rest[0]+heading*controlled_arc
		var phase := TAU*(time-float(data.lag)*u-sample_position.dot(flow)/propagation_speed)/cycle+float(data.phase)
		var gust := 0.575+0.425*sin(phase+0.4)+0.04*sin(2.0*phase-0.6)
		gust += 0.03*sin(phase-TAU*controlled_arc/maxf(1.0, float(data.wavelength)))
		angles.append(amplitude*envelope*clampf(gust, 0.15, 1.0))
	var result := PackedVector2Array([rest[0]])
	for i in range(1, rest.size()):
		# Rotate each original segment, retaining its length. Frames below the
		# visible bend length carry that final rotation through the continuation.
		result.append(result[-1]+(rest[i]-rest[i-1]).rotated(0.5*(angles[i-1]+angles[i])))
	if data.pin_return_tip:
		# A returning U has two concealed attachments. Constrain those endpoints
		# and the first tangent while solving the intervening segment lengths.
		result[0] = rest[0]
		result[1] = rest[1]
		result[-1] = rest[-1]
		for iteration in range(240):
			for reverse_pass in range(2):
				for j in range(rest.size()-1):
					var i := j if reverse_pass == 0 else rest.size()-2-j
					var delta := result[i+1]-result[i]
					var correction := delta*(1.0-rest[i+1].distance_to(rest[i])/maxf(0.0001, delta.length()))
					var left := 0.0 if i <= 1 else 1.0
					var right := 0.0 if i+1 <= 1 or i+1 == rest.size()-1 else 1.0
					if left+right > 0.0:
						result[i] += correction*left/(left+right)
						result[i+1] -= correction*right/(left+right)
				result[0] = rest[0]
				result[1] = rest[1]
				result[-1] = rest[-1]
			if iteration % 8 == 7:
				var error := 0.0
				for i in range(rest.size()-1):
					error = maxf(error, absf(result[i].distance_to(result[i+1])/rest[i].distance_to(rest[i+1])-1.0))
				if error < 0.001:
					break
	return result


func _warp(data: Dictionary, curve: PackedVector2Array) -> PackedVector2Array:
	var tangents := _tangents(curve)
	var result := PackedVector2Array()
	var rest: PackedVector2Array = data.rest_vertices
	var mappings: PackedVector4Array = data.mappings
	var influence: PackedFloat32Array = data.influence
	for i in range(rest.size()):
		if influence[i] == 0.0:
			result.append(rest[i])
			continue
		var mapping := mappings[i]
		var index := int(mapping.x)
		var center := curve[index].lerp(curve[index+1], mapping.y)
		var tangent := tangents[index].lerp(tangents[index+1], mapping.y).normalized()
		var moved := center+tangent*mapping.z+tangent.orthogonal()*mapping.w
		if data.pin_return_tip:
			moved = Vector2.ZERO
			var indices: PackedInt32Array = data.return_indices[i]
			var weights: PackedFloat32Array = data.return_weights[i]
			var source: PackedVector2Array = data.points
			var source_tangents: PackedVector2Array = data.rest_tangents
			for j in range(indices.size()):
				var station := indices[j]
				var rotation := source_tangents[station].angle_to(tangents[station])
				moved += (curve[station]+(rest[i]-source[station]).rotated(rotation))*weights[j]
		result.append(rest[i].lerp(moved, influence[i]))
	return result


func _quality(data: Dictionary, posed: PackedVector2Array, curve: PackedVector2Array) -> Dictionary:
	var min_area := 1.0
	var max_area := 1.0
	var min_edge := 1.0
	var max_edge := 1.0
	var folded := 0
	var displacement := 0.0
	var length_error := 0.0
	var rest: PackedVector2Array = data.rest_vertices
	for triangle in data.visible_triangles:
		var a: int = triangle[0]
		var b: int = triangle[1]
		var c: int = triangle[2]
		var ratio := (posed[b]-posed[a]).cross(posed[c]-posed[a])/(rest[b]-rest[a]).cross(rest[c]-rest[a])
		min_area = minf(min_area, ratio)
		max_area = maxf(max_area, ratio)
		if ratio <= 0.0:
			folded += 1
		for j in range(3):
			var left: int = triangle[j]
			var right: int = triangle[(j+1)%3]
			var stretch := posed[left].distance_to(posed[right])/rest[left].distance_to(rest[right])
			min_edge = minf(min_edge, stretch)
			max_edge = maxf(max_edge, stretch)
		for index in triangle:
			displacement = maxf(displacement, posed[index].distance_to(rest[index]))
	var source: PackedVector2Array = data.points
	for i in range(source.size()-1):
		length_error = maxf(length_error, absf(curve[i].distance_to(curve[i+1])/source[i].distance_to(source[i+1])-1.0))
	return {"min_area_ratio": min_area, "max_area_ratio": max_area, "folded_triangles": folded,
		"min_edge_ratio": min_edge, "max_edge_ratio": max_edge,
		"max_displacement_px": displacement, "centerline_length_error": length_error}


func _within_bounds(quality: Dictionary) -> bool:
	return quality.min_area_ratio >= 0.30 and quality.max_area_ratio <= 2.5 and quality.min_edge_ratio >= 0.72 and quality.max_edge_ratio <= 1.32 and quality.centerline_length_error <= 0.025


func _calibrate(data: Dictionary, amount: float) -> float:
	var scale := 1.0
	# One scale for the entire period. It never changes on a gust threshold,
	# and an inspector/CLI strength value is calibrated only on its first use.
	for attempt in range(12):
		var passed := true
		for phase in range(24):
			var curve := _curve(data, cycle*float(phase)/24.0+wind_time_offset, amount*scale)
			var vertices := _warp(data, curve)
			var quality := _quality(data, vertices, curve)
			if not _within_bounds(quality):
				var factor := 0.85
				if quality.max_edge_ratio > 1.32:
					factor = minf(factor, 0.32/maxf(0.32, float(quality.max_edge_ratio)-1.0))
				if quality.min_edge_ratio < 0.72:
					factor = minf(factor, 0.28/maxf(0.28, 1.0-float(quality.min_edge_ratio)))
				scale *= clampf(factor, 0.20, 0.85)
				passed = false
				break
		if passed:
			print("REFERENCE_SAFE %s strength=%.4f scale=%.6f phases=24" % [data.definition.name, amount, scale*0.97])
			return scale*0.97
	push_error("Reference wind calibration failed for "+str(data.definition.name))
	return 0.0


func pose(time: float, amount: float) -> void:
	for data in strands:
		var scale := 1.0
		var curve: PackedVector2Array = data.points
		var vertices: PackedVector2Array = data.rest_vertices
		if absf(amount) > 0.000001:
			var key := "%.4f" % amount
			if not data.safety_cache.has(key):
				data.safety_cache[key] = _calibrate(data, amount)
			scale = float(data.safety_cache[key])
			curve = _curve(data, time+wind_time_offset, amount*scale)
			vertices = _warp(data, curve)
		data.deformed_vertices = vertices
		data.deformed_curve = curve
		data.mesh.polygon = vertices
		# Movie playback updates geometry only. Metrics are evaluated lazily
		# when a review explicitly requests this pose, then cached until next pose.
		data.quality = {}
		data.accepted_strength = amount*scale
		data.safety_scale = scale
	queue_redraw()


func _draw() -> void:
	if not show_bones:
		return
	for data in strands:
		var curve: PackedVector2Array = data.deformed_curve
		for i in range(curve.size()):
			draw_circle(curve[i], 2.5, Color(1.0, 0.7, 0.2))
			if i > 0:
				draw_line(curve[i-1], curve[i], Color(1.0, 0.7, 0.2), 1.0)


func pin_metrics() -> Dictionary:
	var fixed_count := 0
	var fixed_displacement := 0.0
	var support_displacement := 0.0
	var maximum := 0.0
	var min_area := 1.0
	var min_edge := 1.0
	var max_edge := 1.0
	var folded := 0
	var per_part := {}
	for data in strands:
		var rest: PackedVector2Array = data.rest_vertices
		var posed: PackedVector2Array = data.deformed_vertices
		for i in range(rest.size()):
			if data.fixed_flags[i] != 0:
				fixed_count += 1
				fixed_displacement = maxf(fixed_displacement, rest[i].distance_to(posed[i]))
		support_displacement = maxf(support_displacement, Vector2(data.points[0]).distance_to(data.deformed_curve[0]))
		if data.quality.is_empty():
			data.quality = _quality(data, posed, data.deformed_curve)
		var quality: Dictionary = data.quality.duplicate()
		quality.accepted_strength = data.accepted_strength
		quality.safety_scale = data.safety_scale
		quality.reference_amplitude_deg = data.amplitude_deg
		if data.pin_return_tip:
			quality.return_tip_displacement_px = Vector2(data.points[-1]).distance_to(data.deformed_curve[-1])
		maximum = maxf(maximum, float(quality.max_displacement_px))
		min_area = minf(min_area, float(quality.min_area_ratio))
		min_edge = minf(min_edge, float(quality.min_edge_ratio))
		max_edge = maxf(max_edge, float(quality.max_edge_ratio))
		folded += int(quality.folded_triangles)
		per_part[data.definition.name] = quality
	return {"fixed_vertices": fixed_count, "fixed_max_displacement_px": fixed_displacement,
		"support_max_displacement_px": support_displacement, "fixed_moving_weight_max": 0.0,
		"visible_max_displacement_px": maximum, "visible_min_area_ratio": min_area,
		"visible_min_edge_ratio": min_edge, "visible_max_edge_ratio": max_edge,
		"visible_folded_triangles": folded, "per_part": per_part}
