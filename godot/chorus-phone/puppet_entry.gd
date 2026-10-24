extends Node2D
## Selected existing CGC14 rig, independent hair mesh and fixed-iris eyelids.
var ink := ShaderMaterial.new()
var hair: Node2D
var rig: Dictionary

func _ready() -> void:
	var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://puppet/cgc14.json"))
	rig = config.rig
	ink.shader = load("res://puppet/puppet.gdshader")
	var sprite := Sprite2D.new()
	sprite.centered = false
	sprite.texture = load("res://assets/puppet/CGC14_a-plate.png")
	sprite.material = ink
	add_child(sprite)
	for i in 4:
		ink.set_shader_parameter("weights%d" % i,load("res://assets/puppet/CGC14/weights%d.png" % i))
	ink.set_shader_parameter("eye_open",load("res://assets/puppet/CGC14_a.png"))
	for name in ["eye_skin","eye_region","eye_foreground","upper_lid","lower_lid","eye_curves","eye_ink"]:
		ink.set_shader_parameter(name,load("res://assets/puppet/CGC14/%s.png" % name.replace("_","-")))
	var bases := PackedVector4Array()
	var bounds := PackedVector4Array()
	for eye in config.eyes:
		bases.append(Vector4(eye.basis[0],eye.basis[1],eye.basis[2],eye.basis[3]))
		bounds.append(Vector4(eye.bounds[0],eye.bounds[1],eye.bounds[2],eye.bounds[3]))
	ink.set_shader_parameter("eye_basis",bases)
	ink.set_shader_parameter("eye_bounds",bounds)
	ink.set_shader_parameter("eye_count",bases.size())
	var pivots := PackedVector2Array()
	for pin in rig.pins: pivots.append(Vector2(pin.pivot[0],pin.pivot[1]))
	ink.set_shader_parameter("pivots",pivots)
	hair = load("res://puppet/hair-sway.gd").new()
	add_child(hair)
	hair.build(config.hair,6.0)
	update_at(6.40)

func update_at(song_local: float) -> void:
	# Continue the existing six-second rig through a blink after the whip lands.
	var t := maxf(song_local-6.72,0.0)+1.10
	var motions := PackedVector4Array()
	for pin in rig.pins:
		if str(pin.name).contains("hair") or str(pin.name) == "head":
			motions.append(Vector4.ZERO)
			continue
		var phase := float(pin.get("phase",0.0))
		var wave := sin(TAU*float(pin.get("frequency",1.0))*t/6.0+phase)-sin(phase)
		motions.append(Vector4(pin.move[0]*wave,pin.move[1]*wave,deg_to_rad(float(pin.get("angle",0.0)))*wave,0.0))
	ink.set_shader_parameter("motions",motions)
	hair.pose(t,1.0)
	var age := t-1.50
	var blink := smoothstep(0.0,0.07,age) if age < 0.07 else 1.0-smoothstep(0.125,0.225,age)
	ink.set_shader_parameter("blink_upper",blink)
	ink.set_shader_parameter("blink_lower",blink)
