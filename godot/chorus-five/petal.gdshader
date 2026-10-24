shader_type spatial;
render_mode cull_disabled, specular_disabled, ambient_light_disabled;

uniform vec4 petal_color : source_color = vec4(1.0, 0.77, 0.85, 1.0);
uniform float lighting = 1.0;

void fragment() {
    float edge = smoothstep(0.26, 0.49, abs(UV.x - 0.5));
    float root = 1.0 - smoothstep(0.0, 0.80, UV.y);
    float vein = exp(-abs(UV.x - 0.5) * 62.0) * 0.025;
    vec3 pink = mix(petal_color.rgb, vec3(0.94, 0.43, 0.61), root * 0.13 + edge * 0.08);
    pink += vec3(vein * 0.75, vein * 0.45, vein * 0.50);
    ALBEDO = pink;
    ROUGHNESS = 1.0;
    // Painted translucency: turning petals never become black plastic chips.
    EMISSION = pink * mix(0.86, 0.62, lighting);
}

void light() {
    float wrapped = abs(dot(NORMAL, LIGHT));
    float band = 0.72 + 0.15 * smoothstep(0.18, 0.25, wrapped)
                      + 0.13 * smoothstep(0.67, 0.75, wrapped);
    DIFFUSE_LIGHT += ALBEDO * LIGHT_COLOR * band * ATTENUATION * 0.09 * lighting;
}
