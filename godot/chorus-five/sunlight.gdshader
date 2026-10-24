shader_type spatial;
render_mode unshaded, cull_disabled, blend_add, depth_draw_never;

uniform float lighting = 1.0;
uniform float clock = 0.0;

void fragment() {
    // Broad, feathered shafts in the canopy, behind the character cutout.
    float axis = UV.x - UV.y * 0.38;
    float ray = exp(-pow((axis - 0.12) / 0.095, 2.0)) * 0.34
              + exp(-pow((axis - 0.30) / 0.052, 2.0)) * 0.23;
    float taper = (1.0 - smoothstep(0.03, 0.95, UV.y))
                * smoothstep(0.0, 0.17, UV.x);
    ALBEDO = vec3(1.0, 0.84, 0.65);
    ALPHA = ray * taper * 0.095 * lighting * (0.96 + 0.04 * sin(clock * 0.45 + 0.6));
}
