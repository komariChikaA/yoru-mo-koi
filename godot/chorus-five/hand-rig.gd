extends MeshInstance3D
## Native palm: the wrist stays in its cuff; fingers follow with a small delay.
var base := PackedVector3Array()
var uvs := PackedVector2Array()
var indices := PackedInt32Array()
var palm_material: ShaderMaterial
var rect: Rect2
const PIVOT := Vector2(673,669)
const STEPS_X := 48
const STEPS_Y := 32

func build(light_amount: float) -> void:
	var info: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/hand/manifest.json"))
	rect=Rect2(float(info.rect[0]),float(info.rect[1]),float(info.rect[2]-info.rect[0]),float(info.rect[3]-info.rect[1]))
	for y in range(STEPS_Y+1):
		for x in range(STEPS_X+1):
			var uv:=Vector2(float(x)/STEPS_X,float(y)/STEPS_Y)
			var p:=rect.position+uv*rect.size
			base.append(Vector3((p.x-960)*.01,(540-p.y)*.01,.25))
			uvs.append(uv)
	for y in STEPS_Y:
		for x in STEPS_X:
			var a:=y*(STEPS_X+1)+x
			indices.append_array(PackedInt32Array([a,a+STEPS_X+1,a+1,a+1,a+STEPS_X+1,a+STEPS_X+2]))
	palm_material=ShaderMaterial.new()
	palm_material.shader=load("res://hair.gdshader")
	palm_material.set_shader_parameter("hair_image",load(info.texture))
	palm_material.set_shader_parameter("source_rect",Vector4(rect.position.x,rect.position.y,rect.size.x,rect.size.y))
	palm_material.set_shader_parameter("receiver",load("res://assets/light-receiver.png"))
	palm_material.set_shader_parameter("lighting",light_amount)
	material_override=palm_material
	pose(0.0)

func displaced(p: Vector2,t: float) -> Vector2:
	var weight:=1.0-smoothstep(632.0,670.0,p.x)
	var angle:=deg_to_rad(3.2*sin(TAU*t/4.8+.25)+.65*sin(TAU*t/2.9-.6))
	var lag:=deg_to_rad(.65)*(sin(TAU*t/4.8-.30)-sin(TAU*t/4.8+.25))
	var finger:=1.0-smoothstep(550.0,607.0,p.x)
	return PIVOT+(p-PIVOT).rotated(weight*(angle+lag*finger))

func pose(t: float) -> void:
	var vertices:=PackedVector3Array()
	for b in base:
		var p:=displaced(Vector2(b.x*100+960,540-b.y*100),t)
		vertices.append(Vector3((p.x-960)*.01,(540-p.y)*.01,b.z))
	var arrays:=[]
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_TEX_UV]=uvs
	arrays[Mesh.ARRAY_INDEX]=indices
	var updated:=ArrayMesh.new()
	updated.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	mesh=updated
	palm_material.set_shader_parameter("clock",t)
