shader_type spatial;
render_mode unshaded, cull_disabled;

uniform sampler2D source_image : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D occlusion : filter_linear, repeat_disable;
uniform sampler2D receiver : filter_linear, repeat_disable;
uniform bool character_layer = false;
uniform float lighting = 1.0;
uniform float clock = 0.0;

void fragment() {
    vec3 ink = texture(source_image, UV).rgb;
    float silhouette = texture(occlusion, UV).r;
    if (character_layer && silhouette < 0.5) discard;
    float skin_hair = texture(receiver, UV).r;
    // Retain the painted values. Added sunlight follows the existing top-left key.
    float sun = exp(-dot((UV - vec2(0.23, -0.04)) * vec2(1.20, 0.87),
                         (UV - vec2(0.23, -0.04)) * vec2(1.20, 0.87)) * 2.8);
    float breath = 0.96 + 0.04 * sin(clock * 0.45 + 0.6);
    float warm = lighting * breath * (0.027 * sun + 0.030 * skin_hair * sun);
    vec3 color = 1.0 - (1.0 - ink) * (1.0 - vec3(1.0, 0.77, 0.52) * warm);
    // A cool, low-amplitude fill keeps dark uniform folds readable.
    color += lighting * vec3(0.001, 0.002, 0.006) * (1.0 - ink) * (1.0 - sun);
    ALBEDO = color;
    // Opaque cutout writes depth for rear-petal occlusion and a sharp focal plane.
}
