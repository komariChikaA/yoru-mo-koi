extends Node2D
## Native upper/lower eyelash meshes over a static complete hidden-skin plate.
## The supplied user's tear pixels stay at their authored original positions.
@export_range(0.0,2.0,.05) var detail_strength:=1.0
@export_range(-1.0,1.0,.01) var manual_close:float=-1.0
@export var show_iris:=true
@export var show_upper:=true
@export var show_lower:=true
@export var show_tears:=true
const N:=64
var definitions:Dictionary
var parts:Array=[]
var material15:ShaderMaterial
var skin:Sprite2D
var tears:Sprite2D
var tear_material:ShaderMaterial
var start:=1.25
var finish:=1.46
var current_close:=0.0

func at(points:Array,x:float) -> float:
	for i in range(points.size()-1):
		if x<=float(points[i+1][0]):
			var t:=smoothstep(float(points[i][0]),float(points[i+1][0]),x)
			return lerpf(float(points[i][1]),float(points[i+1][1]),t)
	return float(points[-1][1])

func closed_at(eye:Dictionary,x:float) -> Vector2:
	# Every eye uses one correspondence between native and closed stations.
	# Extend the end segments for native lash tips outside the eye opening;
	# clamping their x would collapse several complete texture columns.
	var stations:Array=eye.gate_x
	var target:Array=eye.closed
	var segment:=N-2
	for i in range(N-1):
		if x<=float(stations[i+1]):
			segment=i
			break
	var t:float=(x-float(stations[segment]))/(float(stations[segment+1])-float(stations[segment]))
	return Vector2(lerpf(float(target[segment][0]),float(target[segment+1][0]),t),lerpf(float(target[segment][1]),float(target[segment+1][1]),t))

func soften_closed_end(x:float,eye:int,amount:float) -> float:
	# As in CGC06, gather only the outer tail during late closure. The
	# monotone C1 map retains the complete native texture, UV and alpha.
	var side:float=-1.0 if eye==0 else 1.0
	var root:float=-50.0 if eye==0 else 52.0
	var distance:=maxf(0.0,(x-root)*side)
	return x-side*.75*smoothstep(.55,1.0,amount)*distance*distance/(distance+6.0)

func configure(_plate:Sprite2D,_eye_layer:Node2D) -> void:
	definitions=JSON.parse_string(FileAccess.get_file_as_string("res://smile15.json"))
	var timeline:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://timeline.json"))
	start=float(timeline.smile_close[0])-float(timeline.cut_blend[0])
	finish=float(timeline.smile_close[1])-float(timeline.cut_blend[0])
	skin=Sprite2D.new();skin.centered=false;skin.texture=load("res://"+str(definitions.skin));add_child(skin)
	material15=ShaderMaterial.new();material15.shader=load("res://smile15.gdshader")
	material15.set_shader_parameter("original",load("res://"+str(definitions.original)))
	material15.set_shader_parameter("opening",load("res://"+str(definitions.opening)))
	material15.set_shader_parameter("glints",load("res://"+str(definitions.glints)))
	var bases:=PackedVector4Array()
	for e in definitions.eyes:
		assert(e.gate_x.size()==N and e.opening_upper.size()==N and e.opening_lower.size()==N and e.closed.size()==N,"Eye opening and closed pose must share 64 stations")
		var axis:=Vector2.from_angle(deg_to_rad(float(e.angle)))
		bases.append(Vector4(float(e.center[0]),float(e.center[1]),axis.x,axis.y))
	material15.set_shader_parameter("basis",bases);skin.material=material15
	for d in definitions.parts:
		assert(d.source.size()==N and float(d.closed_scale)>0.0,"Native lid needs 64 source stations and a positive closed scale")
		var instance:=MeshInstance2D.new();instance.name=str(d.part)+str(d.eye)
		instance.texture=load("res://"+str(d.texture));instance.mesh=ArrayMesh.new();add_child(instance)
		instance.z_index=1 if d.part=="lower" else 2
		var origin:=Vector2(float(d.basis[0]),float(d.basis[1]));var axis:=Vector2(float(d.basis[2]),float(d.basis[3]));var normal:=Vector2(-axis.y,axis.x)
		var uv:=PackedVector2Array();var indices:=PackedInt32Array()
		for y in d.grid_y:
			for point in d.source:uv.append((origin+axis*float(point[0])+normal*float(y)+Vector2(.5,.5))/Vector2(1920,1080))
		for row in range(d.grid_y.size()-1):
			for x in range(N-1):
				var a:=row*N+x;var b:=a+N;indices.append_array(PackedInt32Array([a,a+1,b,a+1,b+1,b]))
		parts.append({"definition":d,"instance":instance,"uv":uv,"indices":indices,"origin":origin,"axis":axis,"normal":normal})
	tears=Sprite2D.new();tears.centered=false;tears.texture=load("res://"+str(definitions.tears));tears.z_index=3;add_child(tears)
	tear_material=ShaderMaterial.new();tear_material.shader=load("res://tear15.gdshader");tears.material=tear_material
	pose(0.0)

func pose(local:float) -> void:
	var close:=smoothstep(start,finish,local) if manual_close<0 else clampf(manual_close,0.0,1.0)
	current_close=close
	var tops:=PackedVector2Array();tops.resize(N*2)
	var lows:=PackedVector2Array();lows.resize(N*2)
	var lower_amount:=close*(.78+.22*close)
	for eye in definitions.eyes.size():
		var e:Dictionary=definitions.eyes[eye]
		var micro:=sin(local*1.1+float(eye)*.7)*.15*detail_strength*close
		for j in N:
			# Horizontal correspondence is identical for both lids; only the
			# lower lid's vertical travel follows with a slight delay.
			var x:=soften_closed_end(lerpf(float(e.gate_x[j]),float(e.closed[j][0]),close),eye,close)
			var target_y:=float(e.closed[j][1])
			tops[eye*N+j]=Vector2(x,lerpf(float(e.opening_upper[j]),target_y,close)+micro)
			lows[eye*N+j]=Vector2(x,lerpf(float(e.opening_lower[j]),target_y,lower_amount)+micro)
	for part in parts:
		var d:Dictionary=part.definition
		var eye:=int(d.eye);var upper:bool=d.part!="lower"
		var amount:=close if upper else lower_amount
		var micro:=sin(local*1.1+float(eye)*.7)*.15*detail_strength*close
		var guides:=PackedVector2Array()
		var scales:=PackedFloat32Array()
		var wall_scales:=PackedFloat32Array()
		for point in d.source:
			var source:=Vector2(float(point[0]),float(point[1]))
			var target:=closed_at(definitions.eyes[eye],source.x)
			target.y+=float(d.get("closed_offset_y",0.0))
			guides.append(Vector2(soften_closed_end(lerpf(source.x,target.x,close),eye,close),lerpf(source.y,target.y,amount)+micro))
			var closed_scale:=at(d.closed_scale_curve,source.x) if d.has("closed_scale_curve") else float(d.closed_scale)
			assert(closed_scale>0.0,"Native cross-section scale must stay positive")
			scales.append(lerpf(1.0,closed_scale,amount))
			wall_scales.append(lerpf(1.0,float(d.get("corner_wall_scale",closed_scale)),amount))
		var vertices:=PackedVector2Array()
		for y in d.grid_y:
			for j in N:
				# Transport each complete native cross-section. Positive smooth
				# scales retain its fine alpha edges without dividing by noisy
				# ink widths or turning thin source columns into thick blocks.
				var dy:=float(y)-float(d.source[j][1])
				# The corner wall below the lash's inner edge gathers into its
				# own root. A smooth positive map retains the complete cutout.
				var offset:=.5*(scales[j]+wall_scales[j])*dy+.5*(wall_scales[j]-scales[j])*(sqrt(dy*dy+1.0)-1.0)
				var point:=guides[j]+Vector2(0.0,offset)
				vertices.append(part.origin+part.axis*point.x+part.normal*point.y+Vector2(.5,.5))
		var arrays:=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=part.uv;arrays[Mesh.ARRAY_INDEX]=part.indices
		part.instance.mesh.clear_surfaces();part.instance.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		part.instance.visible=show_upper if upper else show_lower
		part.instance.modulate.a=1.0
		part["vertices"]=vertices
	material15.set_shader_parameter("upper_points",tops)
	material15.set_shader_parameter("lower_points",lows)
	# Full closure is proved by the meeting aperture, rather than by hiding
	# the iris at a threshold just before the last animation state.
	material15.set_shader_parameter("iris_visible",show_iris)
	material15.set_shader_parameter("glint_offset",Vector2(sin(local*1.6)*.50,cos(local*1.3)*.35)*detail_strength)
	tears.visible=show_tears
	tear_material.set_shader_parameter("detail_offset",Vector2(sin(local*1.4)*.3,cos(local*1.1)*.25)*detail_strength)
