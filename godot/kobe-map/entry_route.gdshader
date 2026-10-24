shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;
uniform vec4 route_color : source_color = vec4(0.3294,0.6235,0.7843,1.0);
uniform float pen_distance = 0.0;
uniform float line_width = 1.8;
void vertex() {
    VERTEX += NORMAL * UV.y * line_width * 0.5;
}
uniform bool use_cord_texture = false;
uniform sampler2D cord_texture : source_color, repeat_enable, filter_linear;
void fragment() {
    if (UV.x > pen_distance) discard;
    vec4 ink = use_cord_texture ? texture(cord_texture,vec2(UV.x/1.348,UV.y*0.5+0.5)) : route_color;
    ALBEDO = ink.rgb;
    ALPHA = ink.a;
}
