shader_type canvas_item;
render_mode unshaded;

void fragment() {
    vec4 original = texture(TEXTURE, UV);
    // Tighten the existing raster's soft coverage; keep its actual letterforms
    // and coloured texture instead of substituting newly typeset glyphs.
    float surround = 0.0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            surround += texture(TEXTURE, UV + vec2(float(x), float(y)) * TEXTURE_PIXEL_SIZE * 1.2).a;
        }
    }
    float sharpened = clamp(original.a + (original.a - surround / 9.0) * 1.5, 0.0, 1.0);
    float coverage = smoothstep(0.14, 0.42, sharpened);
    // A faint remnant keeps the native textured shadow without its broad blur.
    COLOR = vec4(original.rgb, max(coverage, original.a * 0.035));
}
