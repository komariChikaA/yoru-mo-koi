extends SceneTree

func bounds(n: Node3D, tx: Transform3D = Transform3D.IDENTITY) -> AABB:
	var b := AABB()
	var first := true
	var current := tx * n.transform
	if n is MeshInstance3D:
		b = current * n.get_aabb()
		first = false
	for c in n.get_children():
		if c is Node3D:
			var cb := bounds(c, current)
			if cb.size.length() > 0.0:
				b = cb if first else b.merge(cb)
				first = false
	return b

func _initialize() -> void:
	for f in ["Bed_01", "Table_01", "Table_02", "Chair_01", "Chair_02", "Chair_03", "Cupboard_01", "Cupboard_02"]:
		var n: Node3D = load("res://assets/bedroom-kit/FBX/Furniture/" + f + ".fbx").instantiate()
		print(f, " ", bounds(n))
		inspect(n)
		n.free()
	quit()

func inspect(n: Node) -> void:
	if n is MeshInstance3D:
		for i in n.mesh.get_surface_count():
			var m = n.get_active_material(i)
			print(n.name," ",i," ",m.resource_name," ",m.albedo_color," ",m.albedo_texture.resource_path if m.albedo_texture else "none"," vertex ",m.vertex_color_use_as_albedo)
	for c in n.get_children(): inspect(c)
