shader_type canvas_item;
render_mode unshaded;
uniform vec4 frame_rect = vec4(-32.0, -32.0, 1952.0, 1112.0);
void fragment() {
    vec2 centre=(frame_rect.xy+frame_rect.zw)*.5;
    vec2 half_size=(frame_rect.zw-frame_rect.xy)*.5;
    vec2 edge=abs(FRAGCOORD.xy-centre)-half_size;
    float distance=max(edge.x,edge.y);
    float outside=smoothstep(-.65,.65,distance);
    float border=1.0-smoothstep(.85,2.15,abs(distance));
    vec3 color=mix(vec3(1.0),vec3(.22,.18,.22),border);
    COLOR=vec4(color,max(outside,border));
}
