extends Node3D
## Native hair ribbons, adapted from chorus-four/hair-redo/reference-wind.gd.
## The arc-length curve moves; source pixels and their UV coordinates stay fixed.

const DURATION := 11.5
# One shared breeze, with smaller gusts that do not repeat within this shot.
# x = strength, y = period in seconds, z = initial phase.
const WIND_MODES := [Vector3(0.40,6.7,0.65),Vector3(0.18,3.83,-1.1),Vector3(0.06,1.81,1.7)]
var wind_direction := Vector2(-1.0, 0.5)
var strands: Array[Dictionary] = []
var lighting := 1.0

func _catmull(a: Vector2, b: Vector2, c: Vector2, d: Vector2, u: float) -> Vector2:
	return 0.5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)

func _resample(chain: Array) -> PackedVector2Array:
	var controls := PackedVector2Array()
	for p in chain: controls.append(Vector2(float(p[0]),float(p[1])))
	var dense := PackedVector2Array()
	for i in range(controls.size()-1):
		var steps := maxi(4,ceili(controls[i].distance_to(controls[i+1])/4))
		for j in steps:
			dense.append(_catmull(controls[maxi(0,i-1)],controls[i],controls[i+1],controls[mini(controls.size()-1,i+2)],float(j)/steps))
	dense.append(controls[-1])
	var arc := PackedFloat32Array([0.0])
	for i in range(1,dense.size()): arc.append(arc[-1]+dense[i].distance_to(dense[i-1]))
	var count := maxi(3,ceili(arc[-1]/12)+1)
	var result := PackedVector2Array()
	var index := 0
	for i in count:
		var distance := arc[-1]*float(i)/(count-1)
		while index<dense.size()-2 and arc[index+1]<distance: index+=1
		result.append(dense[index].lerp(dense[index+1],(distance-arc[index])/maxf(0.0001,arc[index+1]-arc[index])))
	return result

func _tangents(points: PackedVector2Array) -> PackedVector2Array:
	var result := PackedVector2Array()
	for i in points.size(): result.append((points[mini(i+1,points.size()-1)]-points[maxi(0,i-1)]).normalized())
	return result

func _axis(low: float, high: float, anchors: Array) -> Array[float]:
	var values: Array[float] = [low,high]
	for i in range(1,ceili((high-low)/8)): values.append(minf(low+8*i,high))
	for a in anchors:
		if float(a)>low and float(a)<high: values.append(float(a))
	values.sort()
	var result: Array[float] = []
	for v in values:
		if result.is_empty() or v-result[-1]>0.001: result.append(v)
	return result

func build(manifest: Dictionary, light_amount: float) -> void:
	lighting=light_amount
	for original in manifest.parts:
		var part: Dictionary=original
		var points := _resample(part.chain)
		var lengths := PackedFloat32Array([0.0])
		for i in range(1,points.size()): lengths.append(lengths[-1]+points[i].distance_to(points[i-1]))
		var heading := (points[1]-points[0]).normalized()
		var seam := points[0]
		var across := heading.orthogonal()
		if part.has("cut_line"):
			seam=Vector2(float(part.cut_line[0][0]),float(part.cut_line[0][1]))
			across=(Vector2(float(part.cut_line[1][0]),float(part.cut_line[1][1]))-seam).normalized()
		var free := across.orthogonal()
		if free.dot(heading)<0: free=-free
		var texture: Texture2D=load(part.texture)
		var material := ShaderMaterial.new()
		material.shader=load("res://hair.gdshader")
		material.set_shader_parameter("hair_image",texture)
		material.set_shader_parameter("receiver",load("res://assets/light-receiver.png"))
		material.set_shader_parameter("source_rect",Vector4(float(part.rect[0]),float(part.rect[1]),float(part.rect[2]),float(part.rect[3])))
		material.set_shader_parameter("lighting",lighting)
		var node := MeshInstance3D.new()
		node.name="Hair_"+str(part.id)
		node.material_override=material
		add_child(node)
		var data := {"part":part,"points":points,"lengths":lengths,"tangents":_tangents(points),
			"length":lengths[-1],"seam":seam,"across":across,"free":free,
			"root_arc":maxf(lengths[1],lengths[-1]*float(manifest.get("root_fixed_fraction",0.15))),
			"band":float(part.get("root_band",16)),"pin_tip":bool(part.get("pin_tip",false)),
			"delay":float(part.response_delay),"propagation":float(part.propagation),
			"frequency_hz":float(part.frequency_hz),"damping":0.68,
			"amplitude_deg":10.0,"texture":texture,"material":material,"node":node,
			"depth":float(part.get("depth",0.08)),"scale":1.0}
		_make_mesh(data)
		_calibrate(data,float(part.get("amplitude_px",16)))
		strands.append(data)
	pose(0,1)
	print("SCENE5_HAIR parts=",strands.size()," native_uv=true shared_wind=true damped_response=true duration=",DURATION)

func _make_mesh(data: Dictionary) -> void:
	var rect: Array=data.part.rect
	var origin := Vector2(float(rect[0]),float(rect[1]))
	var size := Vector2(float(rect[2]),float(rect[3]))
	var across: Vector2=data.across
	var free: Vector2=data.free
	var seam: Vector2=data.seam
	var low := Vector2(INF,INF)
	var high := Vector2(-INF,-INF)
	for x in [origin.x,origin.x+size.x]:
		for y in [origin.y,origin.y+size.y]:
			var delta := Vector2(x,y)-seam
			var projected := Vector2(delta.dot(across),delta.dot(free))
			low=low.min(projected)
			high=high.max(projected)
	var columns := _axis(low.x,high.x,[])
	var rows := _axis(low.y,high.y,[0.0,float(data.band)*0.5,float(data.band)])
	var vertices := PackedVector2Array()
	var uv := PackedVector2Array()
	var mappings := PackedVector4Array()
	var weights := PackedFloat32Array()
	var points: PackedVector2Array=data.points
	var tangents: PackedVector2Array=data.tangents
	var lengths: PackedFloat32Array=data.lengths
	for distance in rows:
		for column in columns:
			var point := seam+across*column+free*distance
			vertices.append(point)
			uv.append((point-origin)/size)
			var nearest := INF
			var index := 0
			var blend := 0.0
			for i in range(points.size()-1):
				var segment := points[i+1]-points[i]
				var u := clampf((point-points[i]).dot(segment)/segment.length_squared(),0,1)
				var separation := point.distance_squared_to(points[i].lerp(points[i+1],u))
				if separation<nearest: nearest=separation;index=i;blend=u
			var center := points[index].lerp(points[index+1],blend)
			var tangent := tangents[index].lerp(tangents[index+1],blend).normalized()
			var offset := point-center
			mappings.append(Vector4(index,blend,offset.dot(tangent),offset.dot(tangent.orthogonal())))
			var arc := lerpf(lengths[index],lengths[index+1],blend)
			var release: float=maxf(float(data.band),float(data.length)*0.5)
			var proximal := 1-smoothstep(release,release*1.5,arc)
			var gate := lerpf(1,smoothstep(0,float(data.band),distance),proximal)
			gate*=smoothstep(float(data.root_arc),float(data.root_arc)+float(data.band),arc)
			if data.pin_tip: gate*=smoothstep(float(data.root_arc),maxf(float(data.root_arc)+float(data.band),float(data.length)*0.35),float(data.length)-arc)
			weights.append(gate)
	var indices := PackedInt32Array()
	var visible: Array[Vector3i] = []
	var image: Image=data.texture.get_image()
	for y in range(rows.size()-1):
		for x in range(columns.size()-1):
			var a := y*columns.size()+x
			for triangle in [Vector3i(a,a+1,a+columns.size()+1),Vector3i(a,a+columns.size()+1,a+columns.size())]:
				indices.append_array(PackedInt32Array([triangle.x,triangle.y,triangle.z]))
				for p in [vertices[triangle.x],vertices[triangle.y],vertices[triangle.z],(vertices[triangle.x]+vertices[triangle.y]+vertices[triangle.z])/3]:
					var pixel := Vector2i(Vector2(p)-origin)
					if Rect2i(Vector2i.ZERO,image.get_size()).has_point(pixel) and image.get_pixelv(pixel).a>0.03:
						visible.append(triangle)
						break
	data.rest=vertices
	data.mappings=mappings
	data.weights=weights
	data.uv=uv
	data.indices=indices
	data.visible=visible
	data.mesh=ArrayMesh.new()
	data.node.mesh=data.mesh
	_return_blends(data)

func _return_blends(data: Dictionary) -> void:
	var points: PackedVector2Array=data.points
	var all_indices: Array[PackedInt32Array] = []
	var all_weights: Array[PackedFloat32Array] = []
	for point in data.rest:
		var nearest := INF
		for p in points: nearest=minf(nearest,Vector2(point).distance_to(p))
		var indices := PackedInt32Array()
		var weights := PackedFloat32Array()
		var total := 0.0
		for i in points.size():
			var u: float=Vector2(point).distance_to(points[i])/(nearest+64)
			if u<1:
				var w := pow(1-u,4)*(4*u+1)
				indices.append(i);weights.append(w);total+=w
		for i in weights.size(): weights[i]/=total
		all_indices.append(indices);all_weights.append(weights)
	data.return_indices=all_indices
	data.return_weights=all_weights

func _wind_response(data: Dictionary, u: float, t: float) -> float:
	var root: Vector2=data.points[0]
	var travel := (root-Vector2(1400,180)).dot(wind_direction.normalized())/1800.0
	var time := t-travel-float(data.delay)-float(data.propagation)*u
	# Steady-state solution of x'' + 2*zeta*w0*x' + w0^2*x = w0^2*wind.
	# Absolute-time sampling gives the same inertia when seeking or rendering.
	var natural_hz := lerpf(1.1,float(data.frequency_hz),u)
	# A light mean wind leaves room for visible swaying on both sides of rest.
	var gust := 0.10
	for mode in WIND_MODES:
		var ratio: float=1.0/(mode.y*natural_hz)
		var real := 1.0-ratio*ratio
		var imaginary := 2.0*float(data.damping)*ratio
		var gain := 1.0/sqrt(real*real+imaginary*imaginary)
		var lag := atan2(imaginary,real)
		gust+=mode.x*gain*sin(TAU*time/mode.y+mode.z-lag)
	return gust

func _curve(data: Dictionary, t: float, amount: float) -> PackedVector2Array:
	var rest: PackedVector2Array=data.points
	var lengths: PackedFloat32Array=data.lengths
	var heading := (rest[mini(3,rest.size()-1)]-rest[0]).normalized()
	var turn := signf(heading.cross(wind_direction))
	if turn==0: turn=1
	var amplitude := deg_to_rad(float(data.amplitude_deg))*amount*turn
	# The left locks have a drawn return/curl. Preserve that silhouette instead
	# of winding every successive segment farther and squeezing the lower arc.
	if str(data.part.id)=="left-loop":
		var result := PackedVector2Array()
		var direction := wind_direction.normalized()
		var gust := _wind_response(data,0.5,t)
		for i in rest.size():
			var start := float(data.root_arc)+float(data.band)
			var u := clampf((lengths[i]-start)/(float(data.length)-start),0,1)
			var envelope := pow(sin(PI*u),2)
			result.append(rest[i]+direction*amplitude*float(data.length)*0.3*envelope*gust)
		return result
	var angles := PackedFloat32Array()
	for i in rest.size():
		var u := clampf((lengths[i]-float(data.root_arc))/(float(data.length)-float(data.root_arc)),0,1)
		var is_left_tail := str(data.part.id).begins_with("left-tail-")
		var gust := _wind_response(data,0.65 if is_left_tail else u,t)
		var bending := smoothstep(0,0.38,u) if is_left_tail else u*u*(3-2*u)
		angles.append(amplitude*bending*gust)
	var result := PackedVector2Array([rest[0]])
	for i in range(1,rest.size()): result.append(result[-1]+(rest[i]-rest[i-1]).rotated(0.5*(angles[i-1]+angles[i])))
	if data.pin_tip:
		result[0]=rest[0];result[1]=rest[1];result[-1]=rest[-1]
		for iteration in 240:
			for pass_index in 2:
				for j in range(rest.size()-1):
					var i := j if pass_index==0 else rest.size()-2-j
					var delta := result[i+1]-result[i]
					var correction := delta*(1-rest[i+1].distance_to(rest[i])/maxf(0.0001,delta.length()))
					var left := 0.0 if i<=1 else 1.0
					var right := 0.0 if i+1<=1 or i+1==rest.size()-1 else 1.0
					if left+right>0: result[i]+=correction*left/(left+right);result[i+1]-=correction*right/(left+right)
				result[0]=rest[0];result[1]=rest[1];result[-1]=rest[-1]
			if iteration%8==7:
				var error := 0.0
				for i in range(rest.size()-1): error=maxf(error,absf(result[i].distance_to(result[i+1])/rest[i].distance_to(rest[i+1])-1))
				if error<0.001: break
	return result

func _warp(data: Dictionary, curve: PackedVector2Array) -> PackedVector2Array:
	var rest: PackedVector2Array=data.rest
	var tangents := _tangents(curve)
	var result := PackedVector2Array()
	for i in rest.size():
		if float(data.weights[i])==0: result.append(rest[i]);continue
		# Blend neighbouring rigid frames in image space. A single nearest
		# curve segment jumps between stations across a wide, forked lock.
		var moved := Vector2.ZERO
		for j in data.return_indices[i].size():
			var k: int=data.return_indices[i][j]
			var rotation: float=Vector2(data.tangents[k]).angle_to(tangents[k])
			moved+=(curve[k]+(rest[i]-Vector2(data.points[k])).rotated(rotation))*float(data.return_weights[i][j])
		result.append(rest[i].lerp(moved,float(data.weights[i])))
	return result

func _quality(data: Dictionary, posed: PackedVector2Array) -> Dictionary:
	var rest: PackedVector2Array=data.rest
	var folded := 0
	var min_area := 1.0
	var max_move := 0.0
	var fixed_move := 0.0
	for i in rest.size():
		var distance := rest[i].distance_to(posed[i])
		if float(data.weights[i])==0: fixed_move=maxf(fixed_move,distance)
	for triangle in data.visible:
		var a: int=triangle.x
		var b: int=triangle.y
		var c: int=triangle.z
		var area := (posed[b]-posed[a]).cross(posed[c]-posed[a])/(rest[b]-rest[a]).cross(rest[c]-rest[a])
		for index in [a,b,c]: max_move=maxf(max_move,rest[index].distance_to(posed[index]))
		min_area=minf(min_area,area)
		if area<=0: folded+=1
	return {"folded_triangles":folded,"min_area_ratio":min_area,"max_displacement_px":max_move,"fixed_max_displacement_px":fixed_move}

func _calibrate(data: Dictionary, target_px: float) -> void:
	var maximum := 0.0
	for i in 48:
		var posed := _warp(data,_curve(data,DURATION*i/47.0,1))
		maximum=maxf(maximum,float(_quality(data,posed).max_displacement_px))
	data.scale=target_px/maxf(maximum,0.001)
	for attempt in 10:
		var okay := true
		for i in 48:
			var posed := _warp(data,_curve(data,DURATION*i/47.0,float(data.scale)))
			var quality := _quality(data,posed)
			var minimum_area := 0.74 if str(data.part.id).begins_with("left-") else 0.3
			if int(quality.folded_triangles)>0 or float(quality.min_area_ratio)<minimum_area: okay=false;break
		if okay:
			print("HAIR_CALIBRATED ",data.part.id," target_px=",target_px," scale=",data.scale)
			return
		data.scale*=0.8
	push_error("Hair deformation calibration failed: "+str(data.part.id))

func pose(t: float, amount: float, show_hair: bool=true) -> void:
	for data in strands:
		var curve: PackedVector2Array=data.points if absf(amount)<0.000001 else _curve(data,t,float(data.scale)*amount)
		var posed: PackedVector2Array=data.rest if absf(amount)<0.000001 else _warp(data,curve)
		data.posed=posed
		data.curve=curve
		var vertices := PackedVector3Array()
		var normals := PackedVector3Array()
		for p in posed: vertices.append(Vector3((p.x-960)*0.01,(540-p.y)*0.01,float(data.depth)));normals.append(Vector3(0,0,1))
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices
		arrays[Mesh.ARRAY_NORMAL]=normals
		arrays[Mesh.ARRAY_TEX_UV]=data.uv
		arrays[Mesh.ARRAY_INDEX]=data.indices
		data.mesh.clear_surfaces()
		data.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		data.node.visible=show_hair
		data.material.set_shader_parameter("clock",t)

func review_motion() -> Dictionary:
	var report := {"samples":139,"duration":DURATION,"shared_wind":true,"damped_response":true,"parts":{},"folded_triangles":0,"fixed_max_displacement_px":0.0}
	for data in strands:
		var record := {"min_area_ratio":1.0,"max_displacement_px":0.0,"time_at_max_displacement":0.0,"fixed_max_displacement_px":0.0,"return_tip_displacement_px":0.0,"folded_triangles":0,"motion_trace":[]}
		for i in 139:
			var curve := _curve(data,DURATION*i/138.0,float(data.scale))
			var quality := _quality(data,_warp(data,curve))
			var marker := curve.size()/2 if data.pin_tip else curve.size()-1
			record.motion_trace.append([DURATION*i/138.0,curve[marker].x,curve[marker].y])
			record.min_area_ratio=minf(float(record.min_area_ratio),float(quality.min_area_ratio))
			if float(quality.max_displacement_px)>float(record.max_displacement_px):
				record.max_displacement_px=float(quality.max_displacement_px)
				record.time_at_max_displacement=DURATION*i/138.0
			record.fixed_max_displacement_px=maxf(float(record.fixed_max_displacement_px),float(quality.fixed_max_displacement_px))
			record.folded_triangles+=int(quality.folded_triangles)
			if data.pin_tip: record.return_tip_displacement_px=maxf(float(record.return_tip_displacement_px),curve[-1].distance_to(data.points[-1]))
		report.parts[data.part.id]=record
		report.folded_triangles+=int(record.folded_triangles)
		report.fixed_max_displacement_px=maxf(float(report.fixed_max_displacement_px),float(record.fixed_max_displacement_px))
	return report
