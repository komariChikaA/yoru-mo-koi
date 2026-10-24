shader_type spatial;
render_mode unshaded, cull_disabled, alpha_to_coverage;

uniform sampler2D hair_image : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D receiver : filter_linear, repeat_disable;
uniform vec4 source_rect;
uniform float lighting = 1.0;
uniform float clock = 0.0;

void fragment() {
    vec4 pixel = texture(hair_image, UV);
    // Opaque native cutout keeps the painted strands on the character's focal
    // plane. Transparent hair otherwise inherits the background's DOF depth.
    ALPHA = pixel.a;
    ALPHA_SCISSOR_THRESHOLD = 0.5;
    ALPHA_ANTIALIASING_EDGE = 0.3;
    ALPHA_TEXTURE_COORDINATE = UV * vec2(textureSize(hair_image, 0));
    vec2 source_uv = (source_rect.xy + UV * source_rect.zw) / vec2(1920.0,1080.0);
    float skin_hair = texture(receiver, source_uv).r;
    // Match the plate at the original art coordinates, including fixed roots.
    float sun = exp(-dot((source_uv - vec2(0.23, -0.04)) * vec2(1.20, 0.87),
                         (source_uv - vec2(0.23, -0.04)) * vec2(1.20, 0.87)) * 2.8);
    float breath = 0.96 + 0.04 * sin(clock * 0.45 + 0.6);
    float warm = lighting * breath * (0.027 * sun + 0.030 * skin_hair * sun);
    vec3 color = 1.0 - (1.0 - pixel.rgb) * (1.0 - vec3(1.0, 0.77, 0.52) * warm);
    color += lighting * vec3(0.001, 0.002, 0.006) * (1.0 - pixel.rgb) * (1.0 - sun);
    ALBEDO = color;
}
