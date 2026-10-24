extends ColorRect

var settings:Dictionary
var portraits:Array
var ink:ShaderMaterial
var state:Dictionary
var footer:Control
var footer_columns:Array[Control]=[]
var footer_widths:Array[float]=[]
const SECTOR:=TAU/5.0

func soft_curve(p:float) -> float:
    p=clampf(p,0.0,1.0)
    return p*p*p*(p*(p*6.0-15.0)+10.0)

func settle_curve(p:float) -> float:
    p=clampf(p,0.0,1.0)
    # Asymmetric C2 easing: peak speed in the first third, then a long landing.
    return p*p*p*(35.0-p*(105.0-p*(126.0-p*(70.0-15.0*p))))

func pull_curve(p:float) -> float:
    p=clampf(p,0.0,1.0)
    # Beta(3,4) CDF: zero endpoint speed/acceleration, peak speed at 40%.
    # With a 2.5-beat action, the speed peak lands exactly one beat after onset.
    return p*p*p*(20.0-p*(45.0-p*(36.0-10.0*p)))

func travel_arc(a:Vector2,b:Vector2,p:float) -> Vector2:
    var c1:=a+Vector2(-190,-72)
    var c2:=b+Vector2(220,38)
    var q:=1.0-p
    return a*q*q*q+c1*3.0*q*q*p+c2*3.0*q*p*p+b*p*p*p

func transfer_position(a:Vector2,b:Vector2,p:float) -> Vector2:
    var anticipation:=sin(PI*clampf(p/.16,0.0,1.0))*14.0
    var route:=soft_curve((p-.06)/.94)
    return travel_arc(a,b,route)+Vector2(anticipation,0.0)

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    settings=JSON.parse_string(FileAccess.get_file_as_string("res://ending.json"))
    portraits=JSON.parse_string(FileAccess.get_file_as_string("res://assets/ending/portraits.json"))
    ink=ShaderMaterial.new()
    ink.shader=load("res://heroine-ending.gdshader")
    material=ink
    var colours:=PackedColorArray()
    var uvs:=PackedVector2Array()
    for i in 5:
        ink.set_shader_parameter("portrait_"+str(i),mipped_texture(portraits[i].texture))
        colours.append(Color(settings.palette[i]))
        uvs.append(Vector2(portraits[i].face_uv[0],portraits[i].face_uv[1]))
    ink.set_shader_parameter("inks",colours)
    ink.set_shader_parameter("face_uvs",uvs)
    ink.set_shader_parameter("narrowing",float(settings.triangle_width))
    for i in 3:
        ink.set_shader_parameter("memory_"+str(i),mipped_texture("res://assets/ending/memory-"+str(i)+".png"))
    for key in ["warmth","softness","glow","vignette","exposure"]:
        ink.set_shader_parameter("scene_"+key,float(settings.scene_filter[key]))
    ink.set_shader_parameter("cg_rect",Vector4(settings.cg_rect[0],settings.cg_rect[1],settings.cg_rect[2],settings.cg_rect[3]))
    build_footer()

func mipped_texture(path:String) -> ImageTexture:
    var image:Image=load(path).get_image()
    image.generate_mipmaps()
    return ImageTexture.create_from_image(image)

func build_footer() -> void:
    footer=Control.new()
    footer.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(footer)
    var font:=SystemFont.new()
    font.font_names=PackedStringArray(["Yu Gothic","Microsoft YaHei UI"])
    var columns:Array=[[135.0,"TOOLS","Storybrew  ·  Godot",27],[655.0,"GAME",str(settings.game_title),29],[1310.0,"MAD",str(settings.work_title),31]]
    for column in columns:
        var group:=Control.new()
        group.position=Vector2(column[0],945.0)
        group.mouse_filter=Control.MOUSE_FILTER_IGNORE
        group.clip_contents=true
        group.size=Vector2(500.0 if column[0]<1300.0 else 480.0,90.0)
        footer_widths.append(group.size.x)
        footer.add_child(group)
        footer_columns.append(group)
        for row in 2:
            var label:=Label.new()
            label.position=Vector2(0.0,0.0 if row==0 else 33.0)
            label.text=column[1] if row==0 else column[2]
            label.add_theme_font_override("font",font)
            label.add_theme_font_size_override("font_size",16 if row==0 else int(column[3]))
            label.add_theme_color_override("font_color",Color("b59b9e") if row==0 else Color("796468"))
            group.add_child(label)

func rotation_at(song:float) -> float:
    var start:=float(settings.unfold_end)
    var stop:=float(settings.rotation_stop)
    var beat:=float(settings.beat_seconds)
    var period:=beat*float(settings.rotation_beats_per_sector)
    var elapsed:=clampf(song-start,0.0,stop-start)
    var turns:=floorf(elapsed/period)
    var phase:=(elapsed-turns*period)/(beat*float(settings.rotation_move_beats))
    # Keep the action/hold cadence under the feng-logo fade until the
    # user-marked first hard cut takes over the screen.
    return SECTOR*(turns+pull_curve(phase))

func pose(song:float,camera:Camera3D) -> void:
    visible=song>=float(settings.frame_start) and song<float(settings.page_end)
    if not visible:return
    var screen:=get_viewport().get_visible_rect().size
    var live_face:=camera.unproject_position(Vector3((887.0-960.0)*.01,(540.0-270.0)*.01,0.0))
    var live_scale:=screen.y/(camera.size*100.0)
    var transfer_phase:=clampf((song-float(settings.transfer_start))/(float(settings.transfer_end)-float(settings.transfer_start)),0.0,1.0)
    var transfer:=soft_curve(transfer_phase)
    # Independent narrowed Reuleaux triangles orbit a shared centre, with
    # their tips stopping short of it. The seams and outer arcs stay apart.
    var hub:=Vector2(settings.group_center[0],settings.group_center[1])
    var group_scale:=lerpf(1.0,float(settings.group_scale),transfer)
    var unfold:=smoothstep(float(settings.transfer_end),float(settings.unfold_end),song)
    var radius:=lerpf(360.0,285.0,transfer)*group_scale
    var group_angle:=-PI*.5+rotation_at(song)
    var hubs:=PackedVector2Array()
    var angles:=PackedFloat32Array()
    var radii:=PackedFloat32Array()
    var alpha:=PackedFloat32Array()
    var centres:=PackedVector2Array()
    var sizes:=PackedFloat32Array()
    var uvs:=PackedVector2Array()
    for i in 5:
        var open_angle:=SECTOR*float(i)
        var target_angle:=group_angle+open_angle
        var reveal_duration:=float(settings.beat_seconds)*float(settings.fan_beats)
        var onset:=float(settings.fan_start)+float(i-1)*float(settings.beat_seconds)*float(settings.fan_interval_beats)
        var reveal_phase:=clampf((song-onset)/reveal_duration,0.0,1.0)
        # Acceleration peaks on the next beat, with a longer decelerating tail.
        var reveal:=pull_curve(reveal_phase)
        var angle:=target_angle
        var centre:=hub+Vector2(0,-float(settings.orbit_radius)*float(settings.group_scale)).rotated(target_angle)
        var card_radius:=285.0*float(settings.group_scale)
        var card_growth:=lerpf(.84,1.0,soft_curve(reveal_phase))
        if i==0:
            var destination:=hub+Vector2(0,-float(settings.orbit_radius)*float(settings.group_scale)).rotated(target_angle)
            centre=transfer_position(live_face,destination,transfer_phase)
            card_radius=radius
            card_growth=1.0
        else:
            # A new card starts behind its predecessor, already formed. It is
            # exposed by physical separation rather than an alpha/scale reveal.
            var parent:Vector2=centres[i-1]
            var chord:=centre-parent
            var bow:=chord.rotated(-PI*.5)*.19*sin(PI*reveal)
            centre=parent.lerp(centre,reveal)+bow
            angle=lerpf(angles[i-1],target_angle,reveal)
            angle+=deg_to_rad(4.0)*sin(TAU*reveal_phase)*pow(sin(PI*reveal_phase),2.0)
        hubs.append(centre)
        angles.append(angle)
        radii.append(card_radius*card_growth)
        alpha.append(1.0 if i==0 or song>onset else 0.0)
        centres.append(centre)
        var desired:=190.0/float(portraits[i].card_face_ratio)
        sizes.append(lerpf(600.0*live_scale,desired,transfer)*group_scale if i==0 else desired*float(settings.group_scale)*card_growth)
        var focus_uv:=Vector2(portraits[i].card_face_uv[0],portraits[i].card_face_uv[1])
        if i==0:focus_uv=Vector2(portraits[i].face_uv[0],portraits[i].face_uv[1]).lerp(focus_uv,transfer)
        uvs.append(focus_uv)
    var top_left:=camera.unproject_position(Vector3((660.0-960.0)*.01,(540.0-90.0)*.01,0.0))
    var bottom_right:=camera.unproject_position(Vector3((1110.0-960.0)*.01,(540.0-430.0)*.01,0.0))
    var capture_start:=float(settings.frame_start)
    var capture_end:=float(settings.capture_end)
    var capture_duration:=capture_end-capture_start
    var closing_rect:=Vector4(lerpf(-32.0,top_left.x,soft_curve((song-capture_start)/capture_duration)),lerpf(-32.0,top_left.y,soft_curve((song-capture_start-.04)/(capture_duration-.04))),lerpf(screen.x+32.0,bottom_right.x,soft_curve((song-capture_start-.08)/(capture_duration-.08))),lerpf(screen.y+32.0,bottom_right.y,soft_curve((song-capture_start-.12)/(capture_duration-.12))))
    var half_ratio:=(bottom_right-top_left)*.5/360.0
    var offset_ratio:=((top_left+bottom_right)*.5-live_face)/360.0
    if song>=capture_end:
        # Transport the rectangle with the portrait while its signed-distance
        # outline gradually becomes the curved triangle along the same path.
        var rect_mid:Vector2=centres[0]+offset_ratio*radius
        var rect_half:=half_ratio*radius
        closing_rect=Vector4(rect_mid.x-rect_half.x,rect_mid.y-rect_half.y,rect_mid.x+rect_half.x,rect_mid.y+rect_half.y)
    var curved:=soft_curve((song-float(settings.morph_start))/(float(settings.morph_end)-float(settings.morph_start)))
    var portrait_mix:=soft_curve((song-capture_end+.22)/.22)
    ink.set_shader_parameter("closing_rect",closing_rect)
    ink.set_shader_parameter("rect_half_ratio",half_ratio)
    ink.set_shader_parameter("rect_offset_ratio",offset_ratio)
    ink.set_shader_parameter("curved",curved)
    ink.set_shader_parameter("portrait_mix",portrait_mix)
    ink.set_shader_parameter("capture_marks",soft_curve((song-capture_start-.03)/.20)*(1.0-soft_curve((song-capture_end+.18)/.18)))
    ink.set_shader_parameter("hubs",hubs)
    ink.set_shader_parameter("angles",angles)
    ink.set_shader_parameter("radii",radii)
    ink.set_shader_parameter("opacities",alpha)
    ink.set_shader_parameter("face_centres",centres)
    ink.set_shader_parameter("image_sizes",sizes)
    ink.set_shader_parameter("face_uvs",uvs)
    var trail_hubs:=PackedVector2Array()
    var trail_radii:=PackedFloat32Array()
    for j in 2:
        var p:=clampf((song-float(settings.transfer_start)-.055*float(j+1))/(float(settings.transfer_end)-float(settings.transfer_start)),0.0,1.0)
        var scale:=lerpf(1.0,float(settings.group_scale),soft_curve(p))
        var target:=hub+Vector2(0,-float(settings.orbit_radius)*float(settings.group_scale)).rotated(-PI*.5)
        trail_hubs.append(transfer_position(live_face,target,p))
        trail_radii.append(lerpf(360.0,285.0,soft_curve(p))*scale)
    ink.set_shader_parameter("trail_hubs",trail_hubs)
    ink.set_shader_parameter("trail_radii",trail_radii)
    ink.set_shader_parameter("trail_mix",soft_curve((transfer_phase-.10)/.12)*(1.0-soft_curve((transfer_phase-.82)/.18)))
    ink.set_shader_parameter("page_mix",smoothstep(float(settings.transfer_start),float(settings.transfer_end),song))
    var cg_phase:=clampf((song-float(settings.cg_enter))/(float(settings.cg_land)-float(settings.cg_enter)),0.0,1.0)
    var cg_progress:=settle_curve(cg_phase)
    ink.set_shader_parameter("cg_mix",1.0 if song>=float(settings.cg_enter) else 0.0)
    ink.set_shader_parameter("cg_reveal",cg_progress)
    ink.set_shader_parameter("cg_outline",soft_curve((song-float(settings.cg_outline_start))/(float(settings.cg_land)-float(settings.cg_outline_start))))
    var card_offset:=Vector2(24.0,7.0)*(1.0-cg_progress)
    ink.set_shader_parameter("cg_rect",Vector4(float(settings.cg_rect[0])+card_offset.x,float(settings.cg_rect[1])+card_offset.y,float(settings.cg_rect[2])+card_offset.x,float(settings.cg_rect[3])+card_offset.y))
    var memory_index:=0
    var memory_previous:=0
    var memory_mix:=1.0
    for i in settings.memory_switches.size():
        var onset:=float(settings.memory_switches[i])
        if song>=onset:
            memory_previous=i%3
            memory_index=(i+1)%3
            memory_mix=soft_curve((song-onset)/(float(settings.beat_seconds)*float(settings.memory_transition_beats)))
    ink.set_shader_parameter("memory_previous",memory_previous)
    ink.set_shader_parameter("memory_current",memory_index)
    ink.set_shader_parameter("memory_mix",memory_mix)
    ink.set_shader_parameter("footer_rule",settle_curve((song-float(settings.cg_enter))/(float(settings.cg_land)-float(settings.cg_enter))))
    footer.modulate.a=1.0
    for i in footer_columns.size():
        var onset:=float(settings.footer_start)+float(i)*float(settings.beat_seconds)
        var phase:=clampf((song-onset)/float(settings.beat_seconds),0.0,1.0)
        footer_columns[i].visible=phase>0.0
        footer_columns[i].size.x=footer_widths[i]*settle_curve(phase)
        footer_columns[i].position.y=945.0+16.0*pow(1.0-phase,3.0)
    # Once the 3D world is hidden, array-uniform changes alone can leave
    # MovieWriter reusing its last viewport image. Invalidate the canvas draw.
    queue_redraw()
    var face_positions:Array=[]
    for centre in centres:face_positions.append([centre.x,centre.y])
    state={"song":song,"hub":[hub.x,hub.y],"scale":group_scale,"radius":radius,"radii":Array(radii),"orbit_radius":float(settings.orbit_radius)*float(settings.group_scale),"narrowing":float(settings.triangle_width),"angles":Array(angles),"opacity":Array(alpha),"unfold":unfold,"portrait_rotation":0.0,"rotation":rotation_at(song),"face_centres":face_positions,"image_sizes":Array(sizes),"cg_reveal":cg_progress,"memory_index":memory_index,"memory_mix":memory_mix,"curved":curved,"portrait_mix":portrait_mix,"closing_rect":[closing_rect.x,closing_rect.y,closing_rect.z,closing_rect.w]}
