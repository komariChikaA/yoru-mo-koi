extends SceneTree
var root_scene:Node2D
var out:="../../工作文件夹/output/CGC14-15_scene4"
func snap(name:String) -> Image:
 await process_frame
 await RenderingServer.frame_post_draw
 var im:=root.get_texture().get_image()
 im.save_png(out+"/"+name+".png")
 return im
func _initialize() -> void:
 call_deferred("check")
func check() -> void:
 root_scene=load("res://main.tscn").instantiate();root.add_child(root_scene)
 await process_frame
 root_scene.set_process(false);root_scene.solo=1;root_scene.fixed_time=0.0;root_scene.hair_strength=0.0;root_scene.pose()
 var eye:Node2D=root_scene.eyes14
 var minimum:=INF
 var opening_uv:Array=[]
 for part in eye.parts:opening_uv.append(part.uv.duplicate())
 for step in range(91):
  eye.manual_close=float(step)/90.0;eye.manual_b=0.0;eye.pose(0.0)
  for part in eye.parts:
   var v:PackedVector2Array=part.vertices
   for j in range(0,part.indices.size(),3):
    var a:=v[part.indices[j]];var b:=v[part.indices[j+1]];var c:=v[part.indices[j+2]]
    minimum=minf(minimum,(b-a).cross(c-a)*.5)
  if step in [0,22,45,67,90]:await snap("CGC14-eye-state-%02d"%step)
 assert(minimum>0.0,"Eye mesh folded")
 var closed:Image=await snap("CGC14-eye-closed")
 eye.show_iris=false;eye.pose(0.0)
 var no_iris:Image=await snap("CGC14-eye-closed-noiris")
 assert(closed.get_data()==no_iris.get_data(),"Closed eye reveals iris")
 eye.show_iris=true;eye.manual_close=0.0;eye.pose(0.0)
 var baseline:Image=await snap("CGC14-eye-reset")
 for property in ["show_upper","show_lower","show_iris","show_creases","show_eyebrows"]:
  eye.set(property,false);eye.pose(0.0)
  var hidden:Image=await snap("CGC14-control-"+property)
  assert(hidden.get_data()!=baseline.get_data(),"Control has no effect: "+property)
  eye.set(property,true);eye.pose(0.0)
 eye.manual_close=1.0;eye.pose(0.0)
 var before:PackedVector2Array=eye.parts[0].vertices.duplicate()
 var pin:Marker2D=eye.pins.get_node("UpperLid1/Pin3")
 var saved:=pin.position;pin.position+=Vector2(0,5);eye.pose(0.0)
 assert(before!=eye.parts[0].vertices,"Pin is not editable")
 pin.position=saved;eye.pose(0.0)
 assert(before==eye.parts[0].vertices,"Pin reset changed geometry")
 eye.manual_close=0.0;eye.upper_close=Vector2(1,-1);eye.pose(0.0)
 assert(eye.eyebrows[0].position.length()>0.0 and eye.eyebrows[1].position==Vector2.ZERO,"Independent eyebrow follow failed")
 eye.upper_close=Vector2(-1,-1)
 eye.manual_close=0.0;eye.manual_b=1.0;eye.pose(0.0);await snap("CGC14-eye-b")
 for i in eye.parts.size():assert(opening_uv[i]==eye.parts[i].uv,"Native UV changed")
 var record={"mesh_states":91,"minimum_signed_triangle_area":minimum,"uv":"unchanged","closed_iris":"zero difference","controls":"upper/lower/iris/crease/eyebrow independently change GPU output","pins":"move and exact reset passed"}
 var file:=FileAccess.open(out+"/cgc14-eye-validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(record,"  ")+"\n")
 print("CGC14_EYE_CHECK ",JSON.stringify(record));quit()
