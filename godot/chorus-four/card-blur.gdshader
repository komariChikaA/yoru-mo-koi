shader_type canvas_item;
render_mode unshaded;
uniform float blur_px = 0.0;
uniform float opacity = 1.0;

// Nominal softness in source pixels. The dense Gaussian disk has a 2*blur_px
// support radius and approximately 0.74*blur_px standard deviation, matching
// the previous sparse kernel's spread without its separate image contours.
const int SAMPLE_COUNT = 128;
const float GOLDEN_ANGLE = 2.399963229728653;

void fragment() {
    if (blur_px < 0.01) {
        vec4 sharp = texture(TEXTURE, UV);
        COLOR = vec4(sharp.rgb, sharp.a * opacity);
    } else {
        vec2 radius = TEXTURE_PIXEL_SIZE * blur_px * 2.0;
        vec2 edge = TEXTURE_PIXEL_SIZE * 0.5;
        vec4 col = vec4(0.0);
        float total = 0.0;
        // The sunflower distribution avoids the repeated offset silhouettes
        // produced by sparse cardinal/diagonal taps at large blur strengths.
        for (int i = 0; i < SAMPLE_COUNT; i++) {
            float area = (float(i) + 0.5) / float(SAMPLE_COUNT);
            float angle = float(i) * GOLDEN_ANGLE;
            vec2 offset = sqrt(area) * vec2(cos(angle), sin(angle));
            float weight = exp(-3.125 * area);
            vec4 sampled = texture(TEXTURE, clamp(UV + radius * offset, edge, vec2(1.0) - edge));
            col += vec4(sampled.rgb * sampled.a, sampled.a) * weight;
            total += weight;
        }
        col /= total;
        COLOR = vec4(col.rgb / max(col.a, 0.00001), col.a * opacity);
    }
}
