extends Node2D
## Native whole upper/lower cutouts. Closed c pins and b shape are geometric.
@export_range(-1.0,1.0,.01) var manual_close:float=-1.0
@export_range(0.0,1.0,.01) var manual_b:float=0.0
@export var show_upper:=true
@export var show_lower:=true
@export var show_iris:=true
@export var show_creases:=true
@export var show_eyebrows:=true
@export var eyebrow_follow:=Vector2(6,6)
@export var upper_close:=Vector2(-1,-1)
@export var lower_close:=Vector2(-1,-1)
var definitions:Dictionary
var parts:Array=[]
var creases:Array[Sprite2D]=[]
var eyebrows:Array[Sprite2D]=[]
var material14:ShaderMaterial
var pins:Node2D
var mouth:=Polygon2D.new()
const N:=64

func at(points:PackedVector2Array,x:float) -> float:
	for i in range(points.size()-1):
		if x<=points[i+1].x:return lerpf(points[i].y,points[i+1].y,clampf((x-points[i].x)/(points[i+1].x-points[i].x),0,1))
	return points[-1].y

func configure(plate:Sprite2D) -> void:
	definitions=JSON.parse_string(FileAccess.get_file_as_string("res://cgc14-eyes.json"))
	pins=load("res://cgc14-pin-pose.tscn").instantiate();add_child(pins);pins.get_node("Reference").visible=false
	material14=ShaderMaterial.new();material14.shader=load("res://cgc14-eye.gdshader")
	material14.set_shader_parameter("original",load("res://assets/CGC14_a.png"))
	material14.set_shader_parameter("opening",load("res://assets/CGC14-eyes/native-opening.png"))
	var bases:=PackedVector4Array()
	for eye in definitions.eyes:bases.append(Vector4(eye.basis[0],eye.basis[1],eye.basis[2],eye.basis[3]))
	material14.set_shader_parameter("basis",bases);plate.material=material14
	for d in definitions.parts:
		var instance:=MeshInstance2D.new();instance.name=str(d.part)+str(d.eye)
		instance.texture=load("res://"+str(d.texture));instance.mesh=ArrayMesh.new();add_child(instance)
		instance.z_index=2 if d.part=="upper" else 1
		var uv:=PackedVector2Array();var indices:=PackedInt32Array()
		var origin:=Vector2(d.basis[0],d.basis[1]);var axis:=Vector2(d.basis[2],d.basis[3]);var normal:=Vector2(-axis.y,axis.x)
		for y in d.grid_y:
			for point in d.source:uv.append((origin+axis*float(point[0])+normal*float(y)+Vector2(.5,.5))/Vector2(1920,1080))
		for row in range(d.grid_y.size()-1):
			for x in range(N-1):
				var a:=row*N+x;var b:=a+N
				indices.append_array(PackedInt32Array([a,a+1,b,a+1,b+1,b]))
		parts.append({"definition":d,"instance":instance,"uv":uv,"indices":indices,"origin":origin,"axis":axis,"normal":normal})
	for i in 2:
		var crease:=Sprite2D.new();crease.centered=false;crease.texture=load("res://assets/CGC14-eyes/crease-%d.png"%i);crease.z_index=3;add_child(crease);creases.append(crease)
		var brow:=Sprite2D.new();brow.centered=false;brow.texture=load("res://assets/CGC14-eyes/eyebrow-%d.png"%i);brow.z_index=3;add_child(brow);eyebrows.append(brow)
	var foreground:=Sprite2D.new();foreground.centered=false;foreground.texture=load("res://assets/CGC14-eyes/fixed-hair.png");foreground.z_index=4;add_child(foreground)
	mouth.texture=load("res://assets/CGC14-eyes/mouth-b.png");add_child(mouth)
	var uvs:=PackedVector2Array()
	var axis:=Vector2.from_angle(deg_to_rad(54.0));var normal:=Vector2(-axis.y,axis.x)
	for p in [Vector2(-12,-7),Vector2(12,-7),Vector2(12,7),Vector2(-12,7)]:uvs.append(Vector2(1528,366.5)+axis*p.x+normal*p.y)
	mouth.uv=uvs

func closure(t:float) -> float:
	# One ordinary blink: 120 ms close, 35 ms contact, 160 ms reopen.
	return smoothstep(1.32,1.44,t)*(1.0-smoothstep(1.475,1.635,t))

func pose(t:float) -> void:
	var close:=closure(t) if manual_close<0 else manual_close
	var shape_b:=smoothstep(1.475,1.635,t) if manual_close<0 else manual_b
	var tops:=PackedVector2Array();tops.resize(N*2)
	var lows:=PackedVector2Array();lows.resize(N*2)
	for part in parts:
		var d:Dictionary=part.definition
		var eye:=int(d.eye);var upper:bool=d.part=="upper"
		var p:=close if upper else close*(.7+.3*close)
		if upper and upper_close[eye]>=0:p=upper_close[eye]
		elif not upper and lower_close[eye]>=0:p=lower_close[eye]
		var group:Node2D=pins.get_node(NodePath(("Upper" if upper else "Lower")+"Lid"+str(eye+1)))
		var target:=PackedVector2Array()
		for pin in group.get_children():
			var local:Vector2=pin.position-part.origin
			target.append(Vector2(local.dot(part.axis),local.dot(part.normal)))
		var guide:=PackedVector2Array();var xs:=PackedFloat32Array()
		var source:=PackedVector2Array()
		for pair in d.source:source.append(Vector2(pair[0],pair[1]))
		var left:float=d.opening[0];var right:float=d.opening[1]
		for j in N:
			var x:=source[j].x
			var u:float=(x-left)/(right-left)
			var to_x:float=lerpf(target[0].x,target[-1].x,u)
			var b_lower:=11.0*pow(maxf(0.0,sin(clampf(u,0,1)*PI)),.7)*shape_b if upper else 0.0
			guide.append(Vector2(lerpf(x,to_x,close),lerpf(source[j].y+b_lower,at(target,to_x),p)))
			xs.append(x)
		var vertices:=PackedVector2Array()
		for y in d.grid_y:
			for j in N:
				var depth:float=float(y)-source[j].y
				# Gather the complete native sidewalls without clipping their alpha.
				var u:=clampf((source[j].x-left)/(right-left),0,1)
				var edge:=smoothstep(.65,.90,absf(2*u-1))
				var squeeze:=1.0-p*(.45+.53*edge) if upper else 1.0-p*.97
				var local:=guide[j]+Vector2(0,depth*squeeze)
				vertices.append(part.origin+part.axis*local.x+part.normal*local.y+Vector2(.5,.5))
		var arrays:=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=part.uv;arrays[Mesh.ARRAY_INDEX]=part.indices
		part.instance.mesh.clear_surfaces();part.instance.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		part.instance.visible=show_upper if upper else show_lower
		part["vertices"]=vertices
		for j in N:
			var x:float=lerpf(guide[0].x,guide[-1].x,float(j)/float(N-1))
			var boundary:=Vector2(x,at(guide,x))
			if upper:tops[eye*N+j]=boundary
			else:lows[eye*N+j]=boundary
	for i in 2:
		var axis:=Vector2(definitions.eyes[i].basis[2],definitions.eyes[i].basis[3])
		var follow:=close if upper_close[i]<0 else upper_close[i]
		creases[i].position=Vector2(-axis.y,axis.x)*follow*8.0
		creases[i].visible=show_creases
		eyebrows[i].position=Vector2(-axis.y,axis.x)*follow*eyebrow_follow[i]
		eyebrows[i].visible=show_eyebrows
	material14.set_shader_parameter("upper_points",tops)
	material14.set_shader_parameter("lower_points",lows)
	material14.set_shader_parameter("iris_visible",show_iris)
	var mouth_points:=PackedVector2Array()
	var mouth_axis:=Vector2.from_angle(deg_to_rad(54.0));var mouth_normal:=Vector2(-mouth_axis.y,mouth_axis.x)
	for v in mouth.uv:
		var delta:Vector2=v-Vector2(1528,366.5)
		mouth_points.append(Vector2(1528,366.5)+mouth_axis*delta.dot(mouth_axis)+mouth_normal*delta.dot(mouth_normal)*lerpf(.16,1.0,shape_b))
	mouth.polygon=mouth_points
