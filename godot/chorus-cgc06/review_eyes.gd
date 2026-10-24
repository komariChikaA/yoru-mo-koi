extends SceneTree
## GPU checks of actual layered puppet, including independent Inspector controls.
var scene:Node
var output_dir:String
var records:Array=[]
var pose_only:=false
var lower_rest:Dictionary={}
var review_blink:=0.0
const FACE:=Rect2i(770,60,285,380)

func _initialize() -> void:
	output_dir="user://eye-review"
	for argument in OS.get_cmdline_user_args():
		if argument=="--pose-only": pose_only=true
		if argument.begins_with("--eye-review-output="):
			output_dir=argument.trim_prefix("--eye-review-output=")
	DirAccess.make_dir_recursive_absolute(output_dir)
	call_deferred("capture")

func still(name:String) -> void:
	for tick in 4:
		await process_frame
		await RenderingServer.frame_post_draw
	root.get_texture().get_image().get_region(FACE).save_png(output_dir.path_join(name+".png"))

func inspection_pose() -> void:
	scene.pose()
	scene.transform_view(scene.wide_world,Vector2.ZERO,Vector2.ZERO,1.0,0.0)
	scene.horizontal.set_shader_parameter("blend_amount",1.0)
	scene.horizontal.set_shader_parameter("blur_px",0.0)
	scene.vertical.set_shader_parameter("blur_px",0.0)

func geometry() -> Array:
	var result:Array=[]
	for part in scene.lid_puppet.parts:
		var minimum:=INF
		var vertices:PackedVector2Array=part.vertices
		var indices:PackedInt32Array=part.indices
		for j in range(0,indices.size(),3):
			var a:=vertices[indices[j]];var b:=vertices[indices[j+1]];var c:=vertices[indices[j+2]]
			minimum=minf(minimum,(b-a).cross(c-a))
		var record:Dictionary={"eye":part.eye,"part":part.part,"minimum_triangle_area":minimum,"whole_cutout":part.whole,"mesh_vertex_count":vertices.size()}
		if part.part!="brow":
			var guides:Array=[]
			for point in part.points: guides.append([point.x,point.y])
			record["guide_points"]=guides
		if part.part=="upper":
			var probes:Array=[]
			for tip in part.tip_regions:
				var anchor:=Vector2(tip.anchor[0],tip.anchor[1])
				var point:=anchor+Vector2(tip.direction[0],tip.direction[1])*float(tip.length)
				var moved:Vector2=scene.lid_puppet.compress_tip(point,part,scene.eye_controls.upper_close[part.eye] if scene.eye_controls.manual else review_blink,scene.eye_controls)
				probes.append({"original_length":tip.length,"compressed_length":(moved-anchor).length(),"displacement":(moved-point).length()})
			record["tip_probes"]=probes
		if part.part=="lower":
			if not lower_rest.has(part.eye): lower_rest[part.eye]=vertices.duplicate()
			var baseline:PackedVector2Array=lower_rest[part.eye]
			var shift:Vector2=vertices[0]-baseline[0]
			var residual:=0.0
			for j in vertices.size(): residual=maxf(residual,(vertices[j]-baseline[j]-shift).length())
			record["translation"]=[shift.x,shift.y]
			record["rigid_translation_residual"]=residual
		result.append(record)
	return result

func capture() -> void:
	scene=load("res://main.tscn").instantiate()
	root.add_child(scene)
	scene.set_process(false)
	inspection_pose()
	var face=scene.wide_world.get_child(1)
	face.material=null
	scene.lid_puppet.visible=false
	await still("reference")
	face.material=scene.eye_material
	scene.lid_puppet.visible=true
	if pose_only:
		for value in [0.0,0.1,0.25,0.5,0.75,1.0]:
			scene.set_eye_blink(Vector2.ONE*value)
			await still("pose-%03d" % int(value*100))
		print("PIN_POSE_REVIEW_COMPLETE ",output_dir)
		quit()
		return
	var amounts=[0.0,0.000001,0.0001,0.001,0.01,0.99,0.999,0.9999,0.999999,1.0]
	for index in amounts.size():
		scene.set_eye_blink(Vector2.ONE*amounts[index])
		await still("edge-%02d" % index)
	for index in 91:
		var amount=smoothstep(0.0,1.0,float(index)/90.0)
		review_blink=amount
		scene.set_eye_blink(Vector2.ONE*amount)
		await still("close-%03d" % index)
		var edge_positions:Array=[];var edge_rotations:Array=[]
		for edge in scene.lid_puppet.edge_parts:
			var delta:Vector2=edge.instance.position-edge.anchor
			edge_positions.append([delta.x,delta.y]);edge_rotations.append(edge.instance.rotation)
		records.append({"frame":index,"blink":amount,"geometry":geometry(),"edge_positions":edge_positions,"edge_rotations":edge_rotations})
	var controls=scene.eye_controls
	inspection_pose()
	scene.set_eye_blink(Vector2.ONE)
	await still("closed-base")
	controls.lower_lids_visible=false
	scene.set_eye_blink(Vector2.ONE)
	await still("closed-without-lower")
	controls.lower_lids_visible=true
	scene.set_eye_blink(Vector2.ONE)
	for part in scene.lid_puppet.parts:
		for i in 5:
			var handle:Node2D=part.handles[i]
			var rest:Vector2=handle.position
			handle.position+=part.normal*3.0
			scene.set_eye_blink(Vector2.ONE)
			await still("pin-%s-%d-%d" % [part.part,part.eye,i])
			handle.position=rest
	scene.set_eye_blink(Vector2.ONE)
	for part in scene.lid_puppet.parts:
		part.instance.visible=part.part=="upper"
	await still("closed-upper-only")
	for part in scene.lid_puppet.parts:
		part.instance.visible=part.part=="lower"
	await still("closed-lower-only")
	controls.manual=true
	for part in ["brow","brow-right","upper","upper-right","upper-thickness","lower","lower-right","lower-thickness","lower-flatten","iris","iris-right","iris-scale","hide-brow","hide-iris","hide-body","hide-lower","edge-left","edge-right","edge-flatten","edge-follow","edge-gap","hide-edge","tip-left","tip-right","tip-threshold","reset"]:
		controls.reset()
		match part:
			"brow": controls.brow_left_offset=Vector2(0,2);controls.brow_bend=Vector2(1,0)
			"brow-right": controls.brow_right_offset=Vector2(0,2);controls.brow_bend=Vector2(0,1)
			"upper": controls.upper_close=Vector2(0.6,0)
			"upper-right": controls.upper_close=Vector2(0,0.6)
			"upper-thickness": controls.upper_close=Vector2(0.6,0);controls.upper_thickness=Vector2(0.4,0.78)
			"lower": controls.lower_close=Vector2(0.8,0);controls.lower_bend=Vector2(1,0)
			"lower-right": controls.lower_close=Vector2(0,0.8);controls.lower_bend=Vector2(0,1)
			"lower-thickness": controls.lower_close=Vector2(0.8,0);controls.lower_thickness=Vector2(0.3,0.55)
			"lower-flatten": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.lower_flatten=Vector2.ZERO
			"iris": controls.iris_left_offset=Vector2(2,0)
			"iris-right": controls.iris_right_offset=Vector2(2,0)
			"iris-scale": controls.iris_scale=Vector2(1.05,1)
			"edge-left": controls.edge_left_offset=Vector2(4,0)
			"edge-right": controls.edge_right_offset=Vector2(4,0)
			"edge-flatten": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.edge_flatten=Vector2.ZERO
			"edge-follow": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.edge_follow=Vector2.ZERO
			"edge-gap": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.edge_gap=Vector2(15,15)
			"hide-edge": controls.edge_details_visible=false
			"hide-brow": controls.eyebrows_visible=false
			"hide-iris": controls.iris_visible=false
			"hide-body": controls.eye_body_visible=false
			"hide-lower": controls.lower_lids_visible=false
			"tip-left": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.lash_tip_compress.x=0
			"tip-right": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.lash_tip_compress.y=0
			"tip-threshold": controls.upper_close=Vector2.ONE;controls.lower_close=Vector2.ONE;controls.long_tip_min_length=100.0
		inspection_pose()
		await still("control-"+part)
	controls.reset()
	controls.manual=false
	FileAccess.open(output_dir.path_join("samples.json"),FileAccess.WRITE).store_string(JSON.stringify({"crop":[FACE.position.x,FACE.position.y,FACE.size.x,FACE.size.y],"edge_amounts":amounts,"sequence":records},"  "))
	print("PINNED_MESH_EYE_REVIEW_COMPLETE ",output_dir)
	quit()
