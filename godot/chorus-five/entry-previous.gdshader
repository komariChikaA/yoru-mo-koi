shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;
uniform sampler2D source_image : source_color, filter_linear_mipmap, repeat_disable;
uniform float opacity = 1.0;
void fragment() {
    ALBEDO=texture(source_image,UV).rgb;
    ALPHA=opacity;
}
