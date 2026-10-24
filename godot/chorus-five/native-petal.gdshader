shader_type spatial;
render_mode unshaded, cull_disabled, depth_prepass_alpha;

uniform sampler2D petal_image : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform float lighting = 1.0;
uniform float clock = 0.0;

void fragment() {
    vec4 petal = texture(petal_image, UV);
    // The source already contains its painted edge blur and colour falloff.
    // Keep those values; only inherit the scene's weak warm canopy light.
    float warm = lighting * (0.012 + 0.003 * sin(clock * 0.45 + 0.6));
    ALBEDO = 1.0 - (1.0 - petal.rgb) * (1.0 - vec3(1.0, 0.77, 0.52) * warm);
    ALPHA = petal.a;
}
