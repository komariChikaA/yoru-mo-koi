shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;
uniform sampler2D cord_texture : source_color, filter_linear;
uniform vec4 cord_color : source_color = vec4(1.0);
void fragment() {
    vec4 ink = texture(cord_texture,UV) * cord_color;
    if (ink.a < 0.01) discard;
    ALBEDO = ink.rgb;
    ALPHA = ink.a;
}
