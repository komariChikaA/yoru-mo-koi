shader_type canvas_item;
render_mode unshaded;
uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;
uniform float strength : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec3 source = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
    // Exposure blooms the light areas first, then the entire frame reaches white.
    vec3 lifted = source * (1.0 + 2.0 * strength);
    float whiteout = smoothstep(0.15, 1.0, strength);
    COLOR = vec4(mix(lifted, vec3(1.0), whiteout), 1.0);
}
