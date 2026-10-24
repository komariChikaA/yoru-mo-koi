extends Node2D
## Five editable closed-pose pins for each native brow and eyelid.
## Pin positions live in source-image coordinates. No panel or pose-image switch.
var parts:Array=[]
var edge_parts:Array=[]
var face_material:ShaderMaterial
var gate_bounds:Array=[]
const COUNT:=64
const CANVAS:=Vector2(1376,752)

func normals(points:PackedVector2Array) -> PackedVector2Array:
	var result:=PackedVector2Array()
	for i in points.size():
		var tangent:Vector2=(points[mini(i+1,points.size()-1)]-points[maxi(i-1,0)]).normalized()
		result.append(Vector2(-tangent.y,tangent.x))
	return result

func ribbon_row(points:PackedVector2Array,directions:PackedVector2Array,distance:float) -> PackedVector2Array:
	var result:=PackedVector2Array()
	for i in points.size():
		var previous:=maxi(i-1,0);var next:=mini(i+1,points.size()-1)
		var offset:=distance
		# Exact discrete strip limits on both neighboring edges keep each
		# triangle positive even where the inner normal rays converge.
		var before:=directions[previous].cross(directions[i])
		if before*distance>0.000001:
			var limit:=0.9*absf((points[i]-points[previous]).cross(directions[previous])/before)
			offset=signf(distance)*minf(absf(offset),limit)
		var after:=directions[i].cross(directions[next])
		if after*distance>0.000001:
			var limit:=0.9*absf((points[next]-points[i]).cross(directions[next])/after)
			offset=signf(distance)*minf(absf(offset),limit)
		result.append(points[i]+directions[i]*offset)
	return result

func curve(pins:PackedVector2Array,u:float) -> Vector2:
	var location:=clampf(u,0,1)*4.0
	var j:=mini(int(location),3)
	var t:=location-float(j)
	var a:=pins[j];var b:=pins[j+1]
	var da:Vector2=(pins[j+1]-pins[maxi(j-1,0)])/(1.0 if j==0 else 2.0)
	var db:Vector2=(pins[mini(j+2,4)]-pins[j])/(1.0 if j==3 else 2.0)
	return (2*t*t*t-3*t*t+1)*a+(t*t*t-2*t*t+t)*da+(-2*t*t*t+3*t*t)*b+(t*t*t-t*t)*db

func configure(material:ShaderMaterial) -> void:
	face_material=material
	for eye in JSON.parse_string(FileAccess.get_file_as_string("res://rig.json")).eyes:
		gate_bounds.append(Vector2(eye.opening_x[0],eye.opening_x[1]))
	var definitions:Array=JSON.parse_string(FileAccess.get_file_as_string("res://assets/eyes/lid-meshes.json"))
	var pin_root:Node2D=load("res://pin_pose.tscn").instantiate();add_child(pin_root)
	var stationary_hair:=Sprite2D.new()
	stationary_hair.name="StationaryHair";stationary_hair.centered=false
	stationary_hair.texture=load("res://assets/eyes/stationary-hair.png")
	stationary_hair.z_index=4;add_child(stationary_hair)
	for definition in JSON.parse_string(FileAccess.get_file_as_string("res://assets/eyes/edge-details.json")):
		var sprite:Node2D
		if definition.get("mesh_link",false): sprite=Node2D.new()
		else:
			var image:=Sprite2D.new();image.centered=false
			image.texture=load("res://assets/eyes/"+definition.texture);sprite=image
		sprite.name="EyeEdgeDetail%d" % (int(definition.eye)+1);sprite.z_index=3
		var anchor:=Vector2(definition.anchor[0],definition.anchor[1])
		if sprite is Sprite2D: sprite.offset=-anchor
		sprite.position=anchor
		add_child(sprite)
		edge_parts.append({"eye":int(definition.eye),"anchor":anchor,"angle":float(definition.angle),"instance":sprite})
	for definition in definitions:
		var source:=PackedVector2Array();var rest_pins:=PackedVector2Array();var handles:Array=[]
		for value in definition.source: source.append(Vector2(value[0],value[1]))
		for value in definition.get("control_reference_pins",definition.source_pins): rest_pins.append(Vector2(value[0],value[1]))
		var source_normals:=normals(source)
		var whole:bool=definition.get("mode","")=="whole_cutout"
		var rows:Array=definition.grid_y if whole else definition.rows
		var origin:=Vector2(definition.basis[0],definition.basis[1])
		var axis:=Vector2(definition.basis[2],definition.basis[3])
		var normal:=Vector2(-axis.y,axis.x)
		var title:String=("Eyebrow" if definition.part=="brow" else str(definition.part).capitalize()+"Lid")+str(int(definition.eye)+1)
		# Stored Marker2D positions are the editable, persistent closed pose.
		var pin_group:Node2D=pin_root.get_node(NodePath(title))
		for i in 5:
			handles.append(pin_group.get_node(NodePath("Pin%d" % (i+1))))
		var uvs:=PackedVector2Array();var indices:=PackedInt32Array();var colors:=PackedColorArray()
		for row in rows.size():
			var distance:float=rows[row]
			var row_points:=ribbon_row(source,source_normals,float(distance)) if not whole else PackedVector2Array()
			for i in COUNT:
				var point:Vector2=Vector2(source[i].x,distance) if whole else row_points[i]
				uvs.append((origin+axis*point.x+normal*point.y+Vector2(0.5,0.5))/CANVAS)
				# The extracted native alpha already carries its antialiased edge.
				# A second mesh feather clipped original lash fibers at rest.
				colors.append(Color.WHITE)
		for row in rows.size()-1:
			for i in COUNT-1:
				var a:int=row*COUNT+i;var b:int=a+COUNT
				indices.append_array(PackedInt32Array([a,a+1,b,a+1,b+1,b]))
		var instance:=MeshInstance2D.new();instance.name=title
		instance.texture=load("res://assets/eyes/"+definition.texture) if definition.has("texture") else load("res://assets/eyes/eyebrow.png" if definition.part=="brow" else "res://assets/eyes/%s-lid.png" % definition.part)
		instance.z_index=2 if definition.part=="brow" else (1 if definition.part=="upper" else 0)
		if whole and definition.part!="brow":
			var native_material:=ShaderMaterial.new();native_material.shader=load("res://whole-lid.gdshader")
			instance.material=native_material
		instance.mesh=ArrayMesh.new();add_child(instance)
		parts.append({"eye":int(definition.eye),"part":definition.part,"source":source,"rest_pins":rest_pins,"handles":handles,"tip_regions":definition.get("tip_regions",[]),
			"whole":whole,"edge_link":int(definition.get("edge_link",-1)),"rows":rows,"stations":definition.stations,"origin":origin,"axis":axis,"normal":normal,
			"uvs":uvs,"colors":colors,"indices":indices,"instance":instance})

func gate_y(points:PackedVector2Array,x:float,upper:bool,amount:float) -> float:
	# Full-width grid stations also define the visible eye opening.
	var edge:Vector2=points[0] if x<points[0].x else points[-1]
	if x<points[0].x or x>points[-1].x:
		return edge.y+(-1.0 if upper else 1.0)*absf(x-edge.x)*0.25*(1.0-amount)
	for j in range(points.size()-1):
		if x<=points[j+1].x:
			return lerpf(points[j].y,points[j+1].y,(x-points[j].x)/maxf(points[j+1].x-points[j].x,0.00001))
	return edge.y

func target_y(pins:PackedVector2Array,x:float) -> float:
	var low:=0.0;var high:=1.0
	for step in 20:
		var middle:float=(low+high)*0.5
		if curve(pins,middle).x<x: low=middle
		else: high=middle
	return curve(pins,(low+high)*0.5).y

func station_y(points:PackedVector2Array,x:float) -> float:
	var u:=clampf((x-points[0].x)/(points[-1].x-points[0].x)*float(COUNT-1),0.0,float(COUNT-1))
	var j:=mini(int(u),COUNT-2)
	return lerpf(points[j].y,points[j+1].y,u-float(j))

func compress_tip(point:Vector2,part:Dictionary,amount:float,controls:Resource) -> Vector2:
	var result:=point
	for tip in part.tip_regions:
		if float(tip.length)<=controls.long_tip_min_length: continue
		var anchor:=Vector2(tip.anchor[0],tip.anchor[1])
		var offset:Vector2=point-anchor
		var direction:=Vector2(tip.direction[0],tip.direction[1]).normalized()
		var along:=maxf(0.0,offset.dot(direction))
		var lateral:=absf(offset.cross(direction))
		var weight:=1.0-smoothstep(float(tip.radius)*0.6,float(tip.radius),lateral)
		# C1 at the root, monotone along the tip. Keep every native alpha
		# sample; only shorten long tips geometrically as the lid closes.
		var reach:=along*along/(along+3.0)
		var tip_amount:=amount*(0.85+0.15*amount)
		result-=direction*reach*weight*tip_amount*clampf(controls.lash_tip_compress[part.eye],0.0,0.95)
	return result

func soften_closed_end(x:float,eye:int,amount:float) -> float:
	# Retract the long, needle-like outer tail slightly in late closure.
	# A monotone C1 coordinate map keeps the full native edge and its alpha.
	var side:float=-1.0 if eye==0 else 1.0
	var root:float=-35.0 if eye==0 else 20.0
	var distance:=maxf(0.0,(x-root)*side)
	var reach:=distance*distance/(distance+6.0)
	return x-side*0.35*smoothstep(0.55,1.0,amount)*reach

func deform(blink:Vector2,controls:Resource) -> void:
	var upper_points:=PackedVector2Array();upper_points.resize(COUNT*2)
	var lower_points:=PackedVector2Array();lower_points.resize(COUNT*2)
	for part in parts:
		var eye:int=part.eye;var upper:bool=part.part=="upper";var brow:bool=part.part=="brow"
		var amount:float=(controls.upper_close[eye] if upper or brow else controls.lower_close[eye]) if controls.manual else blink[eye]
		amount=clampf(amount,0,1)
		var root_amount:=amount/(amount+0.10*(1.0-amount)) if eye==0 and upper else amount
		var end_amount:=clampf(controls.upper_close[eye] if controls.manual else blink[eye],0,1)
		# The lower edge follows gently at first and meets the same final line.
		# This keeps the early opening broad while the upper lash leads closure.
		if not upper and not brow: amount*=0.7+0.3*amount
		var thickness:float=1.0 if brow else lerpf(1.0,controls.upper_thickness[eye] if upper else controls.lower_thickness[eye],amount)
		var closed_pins:=PackedVector2Array()
		for handle in part.handles:
			var delta:Vector2=handle.position-Vector2(0.5,0.5)-part.origin
			closed_pins.append(Vector2(delta.dot(part.axis),delta.dot(part.normal)))
		var points:=PackedVector2Array()
		for i in COUNT:
			var u:float=part.stations[i]
			var target:Vector2=curve(closed_pins,u)
			if part.whole:
				if not brow: target=Vector2(part.source[i].x,target_y(closed_pins,part.source[i].x))
				# The lower pins describe the meeting line, including its ends.
				# Sample both lids at the same native x; contracting only the lower
				# lid sideways made its corners slide away from the upper lash.
			# Preserve the exact native brow at rest even when the sparse curve
			# only approximates its visible ridge.
			if brow:
				if part.whole: target=part.source[i]+Vector2(0,target_y(closed_pins,part.source[i].x)-target_y(part.rest_pins,part.source[i].x))
				else: target=part.source[i]+target-curve(part.rest_pins,u)
			# Keep a broad, square opening through the half-close. All horizontal
			# stations travel together; no early tip pinching into an almond.
			var point:Vector2=part.source[i]*(1.0-amount)+target*amount
			if brow:
				point+=(controls.brow_left_offset if eye==0 else controls.brow_right_offset)
				point.y+=controls.brow_bend[eye]*sin(PI*u)
			elif not upper: point.y+=controls.lower_bend[eye]*sin(PI*u)
			points.append(point)
		var guide_points:=points.duplicate()
		if not brow:
			for i in COUNT:
				guide_points[i].x=soften_closed_end(guide_points[i].x,eye,end_amount)
		if upper:
			for edge in edge_parts:
				if edge.eye!=eye: continue
				var anchor_x:float=(edge.anchor-part.origin).dot(part.axis)
				var anchor_y:float=(edge.anchor-part.origin).dot(part.normal)
				# Independent native crease: move down in face coordinates until
				# it rests above the closed lash. No lateral pull toward a pin.
				var destination_y:float=target_y(closed_pins,anchor_x)-controls.edge_gap[eye]
				var delta:float=maxf(0.0,destination_y-anchor_y)*amount*controls.edge_follow[eye]
				edge.instance.position=edge.anchor+part.normal*delta+(controls.edge_left_offset if eye==0 else controls.edge_right_offset)
				# Rotate the original line about its own anchor toward face-flat.
				# Preserve native line thickness/alpha throughout the motion.
				edge.instance.rotation=angle_difference(edge.angle,part.axis.angle())*amount*controls.edge_flatten[eye]
				edge.instance.visible=controls.edge_details_visible
		if not brow:
			for i in COUNT:
				var x:=lerpf(gate_bounds[eye].x,gate_bounds[eye].y,float(i)/float(COUNT-1))
				# The skin gate follows the actual native lash mesh, not a separate
				# outer contour that could leave iris visible above the upper lid.
				var boundary:=Vector2(x,gate_y(guide_points,x,upper,amount))
				if upper: upper_points[eye*COUNT+i]=boundary
				else: lower_points[eye*COUNT+i]=boundary

		var directions:=normals(points);var vertices:=PackedVector2Array()
		var turns:=PackedFloat32Array()
		if part.whole:
			for i in COUNT:
				var before:=maxi(i-1,0);var after:=mini(i+1,COUNT-1)
				var source_tangent:Vector2=part.source[after]-part.source[before]
				var moving_tangent:Vector2=points[after]-points[before]
				var turn:=angle_difference(source_tangent.angle(),moving_tangent.angle())
				turns.append(0.35*tanh(turn/0.35) if upper else 0.0)
			# Bound local rotation and its spatial derivative. Unrestricted
			# column turns can fold the inner corner during late closure.
			for pass_index in 3:
				var filtered:=turns.duplicate()
				for i in COUNT:
					filtered[i]=0.25*turns[maxi(i-1,0)]+0.5*turns[i]+0.25*turns[mini(i+1,COUNT-1)]
				turns=filtered
		for distance in part.rows:
			var row_points:=ribbon_row(points,directions,float(distance)*thickness) if not part.whole else PackedVector2Array()
			for i in COUNT:
				var point:Vector2
				if part.whole:
					var native:=Vector2(part.source[i].x,float(distance))
					var warped:=compress_tip(native,part,amount,controls) if upper else native
					# Directional tip compression moves x too. Re-sample both ridges
					# there before transporting the section, keeping the maps composed.
					var from_ridge:float=warped.y-station_y(part.source,warped.x)
					# Turn the native stroke cross-section with the moving ridge;
					# pure column shear leaves thick lash edges at the old angle.
					# Bound the rotational reach smoothly to preserve whole walls.
					var width:=6.0 if part.part=="upper" else 4.0
					var depth:=from_ridge-(1.0-thickness)*width*tanh(from_ridge/width)
					if upper:
						# Gather the complete long-side root cross-section toward the
						# moving ridge, with a broad C1 join into the lash body.
						# Keep every native UV/alpha sample; do not hide the edge.
						var root_weight:=1.0-smoothstep(-38.0,-15.0,warped.x) if eye==0 else smoothstep(5.0,25.0,warped.x)
						var native_depth:=depth
						depth*=1.0-0.90*amount*root_weight
						if eye==0:
							# Shorten only the positive, long side wall. Preserve the
							# upper stroke and its first 3px; gathering the whole
							# section early would turn the native arch into a spike.
							var excess:=maxf(0.0,native_depth-3.0)
							var side_weight:=1.0-smoothstep(-26.0,-12.0,warped.x)
							depth-=(root_amount-amount)*side_weight*excess*excess/(excess+1.0)
					if not upper: depth*=1.0-amount*clampf(controls.lower_flatten[eye],0.0,0.97)
					var reach:=4.0*tanh(depth/4.0)
					var section:=Vector2(0,reach)
					point=Vector2(warped.x,station_y(points,warped.x)+depth)+section.rotated(turns[i])-section
				else: point=row_points[i]
				if not brow: point.x=soften_closed_end(point.x,eye,end_amount)
				var vertex:Vector2=part.origin+part.axis*point.x+part.normal*point.y+Vector2(0.5,0.5)
				if part.edge_link>=0:
					var edge:Dictionary=edge_parts[part.edge_link]
					vertex=edge.instance.position+(vertex-edge.anchor).rotated(edge.instance.rotation)
				vertices.append(vertex)
		var arrays:=[];arrays.resize(Mesh.ARRAY_MAX)
		part["points"]=guide_points
		part["vertices"]=vertices
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=part.uvs;arrays[Mesh.ARRAY_INDEX]=part.indices
		arrays[Mesh.ARRAY_COLOR]=part.colors
		part.instance.mesh.clear_surfaces();part.instance.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		part.instance.visible=controls.eyebrows_visible if brow else (controls.eye_body_visible if upper else controls.lower_lids_visible)
		if part.edge_link>=0: part.instance.visible=part.instance.visible and controls.edge_details_visible
	face_material.set_shader_parameter("upper_points",upper_points)
	face_material.set_shader_parameter("lower_points",lower_points)
