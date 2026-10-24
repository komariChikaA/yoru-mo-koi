extends SceneTree
var output:="../../工作文件夹/output/CGC14-15_scene4/眼型修复-20261018/gpu"
const CANVAS:=Vector2(1920.0,1080.0)
const SNAPSHOTS:=[0,5,10,12,20,25,30,37,40,50,60,62,70,75,80,85,87,90,92,95,97,99,100]

func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):
			output=argument.trim_prefix("--output=")
	call_deferred("run")

func snap(name:String) -> Image:
	# A background/covered window can skip the automatic draw entirely.
	await process_frame
	RenderingServer.force_draw(false)
	var image:=root.get_texture().get_image()
	assert(not image.is_empty(),"Eye validation requires a real GPU renderer")
	assert(image.save_png(output+"/"+name+".png")==OK,"Cannot save eye validation frame")
	return image

func run() -> void:
	DirAccess.make_dir_recursive_absolute(output)
	root.size=Vector2i(1920,1080)
	var world:=Node2D.new();root.add_child(world)
	var plate:=Sprite2D.new();plate.centered=false;plate.texture=load("res://assets/CGC15_c.png");world.add_child(plate)
	var layer:=Node2D.new();world.add_child(layer)
	var smile:Node2D=load("res://smile15.gd").new();layer.add_child(smile);smile.configure(plate,layer);smile.detail_strength=0.0
	var original_uv:Array=[]
	var original_pixels:Array=[]
	for part in smile.parts:
		original_uv.append(part.uv.duplicate())
		original_pixels.append(part.instance.texture.get_image().get_data())
	var opened:Image
	var half:Image
	var closed:Image
	var minimum_area:=INF
	var minimum_ratio:=INF
	for step in range(101):
		var state:=float(step)/100.0
		smile.manual_close=state;smile.pose(1.35)
		for i in smile.parts.size():
			var part:Dictionary=smile.parts[i]
			var vertices:PackedVector2Array=part.vertices
			var uv:PackedVector2Array=part.uv
			var indices:PackedInt32Array=part.indices
			assert(uv==original_uv[i],"Native eyelid UV changed")
			assert(part.instance.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]==original_uv[i],"Rendered eyelid UV changed")
			assert(part.instance.modulate.a==1.0 and part.instance.self_modulate.a==1.0,"Native eyelid alpha was faded")
			for triangle in range(0,indices.size(),3):
				var a:=indices[triangle];var b:=indices[triangle+1];var c:=indices[triangle+2]
				var native_area:=((uv[b]-uv[a])*CANVAS).cross((uv[c]-uv[a])*CANVAS)*.5
				var area:float=(vertices[b]-vertices[a]).cross(vertices[c]-vertices[a])*.5
				assert(native_area>0.0 and area>0.0,"Native eyelid mesh folded or collapsed")
				minimum_area=minf(minimum_area,area)
				minimum_ratio=minf(minimum_ratio,area/native_area)
		if step in SNAPSHOTS:
			var picture:Image=await snap("state-%03d"%step)
			if step==0:opened=picture
			elif step==50:half=picture
			elif step==100:closed=picture
	for i in smile.parts.size():
		assert(smile.parts[i].instance.texture.get_image().get_data()==original_pixels[i],"Native RGBA texture changed")
	var upper:PackedVector2Array=smile.material15.get_shader_parameter("upper_points")
	var lower:PackedVector2Array=smile.material15.get_shader_parameter("lower_points")
	assert(upper==lower,"Fully closed aperture does not meet at the shared line")
	smile.show_iris=false;smile.pose(1.35)
	var no_iris:Image=await snap("state-100-noiris")
	assert(closed.get_data()==no_iris.get_data(),"Fully closed state still reveals original iris")
	var samples:=[]
	for point in [Vector2i(918,550),Vector2i(1118,362)]:
		var a:=opened.get_pixelv(point);var b:=half.get_pixelv(point)
		assert(a==b,"Visible iris moved or compressed")
		samples.append([point.x,point.y,a.r,a.g,a.b])
	var report:={"mesh_states":101,"snapshots_percent":SNAPSHOTS,"native_eyelid_uv":"unchanged in all rendered mesh surfaces","native_alpha":"original RGBA texture unchanged; both lids retain alpha 1.0 at every state","minimum_signed_triangle_area":minimum_area,"minimum_triangle_area_ratio":minimum_ratio,"closed_aperture":"upper and lower stations exactly meet","closed_iris":"zero pixel difference with iris disabled","fixed_iris_samples":samples}
	var f:=FileAccess.open(output+"/smile15-validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n")
	print("SMILE15_GPU_PASS "+JSON.stringify(report))
	quit()
