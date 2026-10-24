extends Node3D
## Native outgoing cords and city ribbon share world coordinates and a moving pen.
var controller: Node3D
var camera: Camera3D
var origin: Vector3
var metres_per_pixel: float
var incoming_speed: float
var city_speed: float
var paper_materials: Array[ShaderMaterial] = []
var blue_material: ShaderMaterial
var pink_material: ShaderMaterial
var blue_mesh: MeshInstance3D
var live_blue_mesh: ArrayMesh
var original_blue_mesh: Mesh
var original_blue_material: Material
var pink_mesh: MeshInstance3D
var cord_group: Node3D
var tip: Vector3
var prefix_distance: float = 0.0
var duration: float

func setup(owner_node: Node3D, view_camera: Camera3D) -> void:
    controller = owner_node
    duration = -float(controller.ENTRY_BEGIN)
    camera = view_camera
    var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/entry/geometry.json"))
    var drive = controller.drive_pose(0.0)
    # Native y=252 is on the same ground line z=210; exact 854x480 projection.
    metres_per_pixel = 2.0 * (float(controller.ENTRY_HEIGHT) - 0.04) * tan(deg_to_rad(34.0)) / 480.0
    origin = drive.position - drive.heading * 20.0
    origin.y = controller.ENTRY_HEIGHT
    origin.z -= 12.0 * metres_per_pixel
    incoming_speed = float(data.cruise_pixels_per_second) * metres_per_pixel
    var segment: Dictionary = controller.drive_segments[0]
    city_speed = (segment.end - segment.start) / (segment.duration * controller.CITY_END)
    make_paper("paper-base.png", 0.04)
    make_paper("paper-foreground.png", 0.08)
    cord_group = Node3D.new()
    add_child(cord_group)
    # Batch native sprite quads by material; preserve original texture/width/color.
    var batches: Dictionary = {}
    for record in data.sprites:
        if record.texture == "blue-cord.png": continue
        var key = record.texture + str(record.color)
        if not batches.has(key):
            var surface = SurfaceTool.new()
            surface.begin(Mesh.PRIMITIVE_TRIANGLES)
            batches[key] = {"surface": surface, "record": record}
        var surface: SurfaceTool = batches[key].surface
        for index in [0, 1, 2, 0, 2, 3]:
            var uv = [Vector2(0,0),Vector2(1,0),Vector2(1,1),Vector2(0,1)][index]
            surface.set_uv(uv)
            surface.set_normal(Vector3.UP)
            surface.add_vertex(pixel_to_world(record.corners[index], 0.06))
    for batch in batches.values():
        var record: Dictionary = batch.record
        var mesh = MeshInstance3D.new()
        mesh.mesh = batch.surface.commit()
        var material = ShaderMaterial.new()
        material.shader = load("res://entry_cord.gdshader")
        material.render_priority = 1
        material.set_shader_parameter("cord_texture",load("res://assets/entry/" + record.texture))
        material.set_shader_parameter("cord_color",Color(record.color[0],record.color[1],record.color[2],record.color[3]))
        mesh.material_override = material
        mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        cord_group.add_child(mesh)
    tip = pixel_to_world(data.tip, 0.06)
    var blue_points: Array[Vector3] = []
    for record in data.sprites:
        if record.texture != "blue-cord.png": continue
        var left = [(record.corners[0][0]+record.corners[3][0])*0.5,(record.corners[0][1]+record.corners[3][1])*0.5]
        blue_points.append(pixel_to_world(left,0.06))
    blue_points.append(tip)
    for i in range(1,blue_points.size()):
        prefix_distance += blue_points[i-1].distance_to(blue_points[i])
    for i in range(1, controller.blue_path.point_count):
        var point: Vector3 = controller.blue_path.get_point_position(i)
        point.y = 0.06
        blue_points.append(point)
    blue_mesh = controller.get_node("Routes/AiPathRibbon")
    original_blue_mesh = blue_mesh.mesh
    original_blue_material = blue_mesh.material_override
    live_blue_mesh = ribbon(blue_points)
    blue_mesh.mesh = live_blue_mesh
    blue_material = route_material(Color("549fc8"))
    blue_material.set_shader_parameter("use_cord_texture",true)
    blue_material.set_shader_parameter("cord_texture",load("res://assets/entry/blue-route.png"))
    blue_mesh.material_override = blue_material
    # The outgoing pink strand continues beside the same blue strand, then leaves
    # the entrance behind the camera; the separate city/map Ren route stays intact.
    var pink_records: Array = data.sprites.filter(func(record): return record.texture == "memory-cord.png")
    var last: Dictionary = pink_records[-1]
    var end_pixel = [(last.corners[1][0] + last.corners[2][0]) * 0.5, (last.corners[1][1] + last.corners[2][1]) * 0.5]
    var pink_tip = pixel_to_world(end_pixel, 0.062)
    pink_mesh = MeshInstance3D.new()
    pink_mesh.mesh = ribbon([pink_tip, pink_tip + drive.heading * 100.0])
    pink_material = route_material(Color("ef628f"))
    pink_material.set_shader_parameter("line_width",4.0 * metres_per_pixel)
    pink_mesh.material_override = pink_material
    pink_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(pink_mesh)
    print("ENTRY_MATCH speed_in=", incoming_speed, " speed_out=", city_speed, " tip=", tip, " destination=", drive.position)

func pixel_to_world(point: Array, height: float) -> Vector3:
    return Vector3(origin.x + (float(point[0]) - 427.0) * metres_per_pixel, height, origin.z + (float(point[1]) - 240.0) * metres_per_pixel)

func make_paper(texture_name: String, height: float) -> void:
    var paper = MeshInstance3D.new()
    var plane = PlaneMesh.new()
    plane.size = Vector2(854, 480) * metres_per_pixel
    paper.mesh = plane
    paper.position = Vector3(origin.x, height, origin.z)
    var material = ShaderMaterial.new()
    material.shader = load("res://entry_paper.gdshader")
    material.render_priority = 2 if texture_name == "paper-foreground.png" else 0
    material.set_shader_parameter("paper_texture", load("res://assets/entry/" + texture_name))
    paper.material_override = material
    paper.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    paper_materials.append(material)
    add_child(paper)

func route_material(color: Color) -> ShaderMaterial:
    var material = ShaderMaterial.new()
    material.shader = load("res://entry_route.gdshader")
    material.render_priority = 1
    material.set_shader_parameter("route_color", color)
    return material

func ribbon(points: Array[Vector3]) -> ArrayMesh:
    var surface = SurfaceTool.new()
    surface.begin(Mesh.PRIMITIVE_TRIANGLES)
    var distances: Array[float] = [0.0]
    var sides: Array[Vector3] = []
    for i in range(1,points.size()):
        distances.append(distances[-1] + points[i-1].distance_to(points[i]))
    for i in range(points.size()):
        var before = (points[i] - points[maxi(0,i-1)]).normalized()
        var after = (points[mini(points.size()-1,i+1)] - points[i]).normalized()
        if i == 0: before = after
        if i == points.size()-1: after = before
        var normal = after.cross(Vector3.UP)
        var miter = (before.cross(Vector3.UP)+normal).normalized()
        sides.append(miter/maxf(0.2,miter.dot(normal)))
    for i in range(points.size()-1):
        var indices = [i,i,i+1,i,i+1,i+1]
        var directions = [-1.0,1.0,1.0,-1.0,1.0,-1.0]
        for j in range(6):
            var index = indices[j]
            surface.set_normal(sides[index])
            surface.set_uv(Vector2(distances[index],directions[j]))
            surface.add_vertex(points[index])
    return surface.commit()

func pose(seconds: float) -> void:
    visible = seconds < 6.5
    blue_mesh.mesh = live_blue_mesh if visible else original_blue_mesh
    blue_mesh.material_override = blue_material if visible else original_blue_material
    var line_width = lerpf(4.0 * metres_per_pixel,1.8,controller.smootherstep01((seconds+duration)/duration))
    blue_material.set_shader_parameter("line_width",line_width)
    # A single pen clock continues from the original 320px / 0.36s native stroke.
    var distance = maxf(0.0, seconds + duration) * (320.0 * metres_per_pixel / 0.36)
    distance += 2200.0 * pow(maxf(0.0,seconds),2.0)
    blue_material.set_shader_parameter("pen_distance",prefix_distance+distance)
    pink_material.set_shader_parameter("pen_distance",maxf(0.0,seconds + duration - 0.06) * (296.0 * metres_per_pixel / 0.34))
    # Paper retreats spatially. Ink never shares this discard or an opacity fade.
    var amount = controller.smoothstep01((seconds + duration - 0.07) / 0.49)
    for material in paper_materials:
        material.set_shader_parameter("paper_edge",1.01 - 1.02*amount)

func camera_pose(progress: float) -> void:
    var t = clampf(progress,0.0,1.0)
    var drive = controller.drive_pose(0.0)
    # Hermite-equivalent Bezier: match incoming horizontal pan and outgoing drive
    # velocity instead of stopping at either end of the descending path.
    var p1 = origin + drive.heading * incoming_speed * duration / 3.0
    var p2 = drive.position - drive.heading * city_speed * duration / 3.0
    camera.position = origin.bezier_interpolate(p1,p2,drive.position,t)
    var turn = controller.smootherstep01(t)
    camera.rotation = Vector3(lerpf(-PI*0.5,0.0,turn),lerp_angle(0.0,atan2(-drive.heading.x,-drive.heading.z),turn),0)
    camera.fov = 68.0
