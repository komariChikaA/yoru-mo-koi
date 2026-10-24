shader_type canvas_item;
render_mode unshaded;

uniform sampler2D portrait_mask : filter_linear;
uniform vec4 paper : source_color = vec4(0.985, 0.976, 0.965, 1.0);
uniform sampler2D title_texture : filter_linear;
uniform vec4 title_rect_px;
uniform float underlay_strength : hint_range(0.0, 1.0) = 0.74;

float title_coverage(vec2 uv) {
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
        return 0.0;
    }
    return smoothstep(0.14, 0.42, texture(title_texture, uv).a);
}

void fragment() {
    vec4 art = texture(TEXTURE, UV);
    float portrait = texture(portrait_mask, UV).a;
    // The original CG supplies the actual hair edges and the space between strands.
    // Retaining a little scenery around the silhouette conceals cutout remnants.
    vec2 aura_uv = (UV - vec2(0.555, 0.54)) / vec2(0.40, 0.88);
    float aura = 1.0 - smoothstep(0.45, 1.0, length(aura_uv));
    float left_clearance = smoothstep(0.28, 0.46, UV.x);
    float right_clearance = 1.0 - smoothstep(0.69, 0.98, UV.x);
    float scenery = aura * left_clearance * right_clearance * 0.32;
    float keep = max(portrait, scenery);
    vec3 background = mix(paper.rgb, art.rgb, keep);

    // Let the CG yield only beside overlapping strokes, with no rectangular
    // title band and no broad wash over the portrait or the face.
    vec2 px = UV * vec2(1920.0, 1080.0);
    vec2 title_uv = (px - title_rect_px.xy) / title_rect_px.zw;
    float halo = 0.0;
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            vec2 sample_offset = vec2(float(x), float(y));
            float softness = exp(-dot(sample_offset, sample_offset) * 0.30);
            halo = max(halo, title_coverage(title_uv + sample_offset * 1.8 / title_rect_px.zw) * softness);
        }
    }
    float overlap_zone = smoothstep(420.0, 560.0, px.x) * (1.0 - smoothstep(1510.0, 1650.0, px.x));
    background = mix(background, paper.rgb, halo * overlap_zone * underlay_strength);
    COLOR = vec4(background, 1.0);
}
