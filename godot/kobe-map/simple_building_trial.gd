extends RefCounted
## Optional B-model trial; existing parcel nodes still drive all height animation.

const DIRECTORY = "res://assets/buildings/quaternius-simple/"

static func apply(stage: Node3D) -> void:
	var models: Array[Mesh] = [load(DIRECTORY + "OBJ/Flat-simple.obj"), load(DIRECTORY + "OBJ/House2-simple.obj")]
	var palette: Texture2D = load(DIRECTORY + "Textures/simple-palette.png")
	var materials: Dictionary = {}
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world-map.json"))
	var count = 0
	for parcel in stage.get_node("Buildings").get_children():
		var volume: MeshInstance3D = parcel.get_node("Volume")
		var size: Vector3 = volume.mesh.size
		var original: ShaderMaterial = volume.material_override
		var color: Color = original.get_shader_parameter("paint_color")
		var key = str(color)
		if not materials.has(key):
			var mat: ShaderMaterial = original.duplicate()
			mat.set_shader_parameter("facade_enabled", true)
			mat.set_shader_parameter("facade_texture", palette)
			materials[key] = mat
		var model: Mesh = models[1 if size.y < 12.0 else 0]
		var bounds = model.get_aabb()
		var center = Vector2(parcel.position.x, parcel.position.z)
		var street = center
		var nearest = INF
		for road in layout.roads:
			var point = Geometry2D.get_closest_point_to_segment(center,
				Vector2(road.a[0], road.a[1]), Vector2(road.b[0], road.b[1]))
			var distance = center.distance_to(point) - float(road.width) * 0.5
			if distance < nearest:
				nearest = distance
				street = point
		var direction = street - center
		var angle = snappedf(atan2(direction.x, direction.y), PI * 0.5)
		var rotated_bounds: AABB = Transform3D(Basis(Vector3.UP, angle), Vector3.ZERO) * bounds
		var holder = Node3D.new()
		holder.name = "SimpleBuildingTrial"
		holder.scale = size / rotated_bounds.size
		holder.position.y = 0.006
		var instance = MeshInstance3D.new()
		instance.name = "Facade"
		instance.mesh = model
		instance.material_override = materials[key]
		# Align the feet and fit the same map footprint; no city parent scaling.
		instance.rotation.y = angle
		instance.position = Vector3(-rotated_bounds.get_center().x,
			-rotated_bounds.position.y, -rotated_bounds.get_center().z)
		for part in parcel.get_children():
			part.visible = false
		parcel.add_child(holder)
		holder.add_child(instance)
		count += 1
	print("SIMPLE_BUILDING_TRIAL parcels=", count, " models=Flat/House2 frames_removed=true")
