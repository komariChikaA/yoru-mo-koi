shader_type canvas_item;
render_mode unshaded;
uniform vec2 detail_offset=vec2(0.0);
void fragment(){
    vec4 native=texture(TEXTURE,UV);
    // Authored silhouette stays fixed; only the tear's internal highlight moves.
    vec3 detail=texture(TEXTURE,UV-detail_offset/vec2(1920.0,1080.0)).rgb;
    COLOR=vec4(detail,native.a);
}
