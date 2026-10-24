shader_type spatial;
render_mode unshaded, cull_disabled, depth_prepass_alpha;
uniform sampler2D paper_texture : source_color, filter_linear;
uniform float paper_edge = 1.0;
void fragment() {
    // A moving physical page edge exposes the city; never crossfade the route.
    if (UV.x > paper_edge) discard;
    vec4 ink = texture(paper_texture, UV);
    if (ink.a < 0.01) discard;
    ALBEDO = ink.rgb;
    ALPHA = ink.a;
}
