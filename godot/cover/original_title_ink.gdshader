shader_type canvas_item;
render_mode unshaded;
uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;

void fragment() {
    vec4 original = texture(TEXTURE, UV);
    vec3 backing = texture(screen_texture, SCREEN_UV).rgb;
    float brightness = dot(backing, vec3(0.2126, 0.7152, 0.0722));
    // Fine light ink over dark fabric; fine plum ink over paper / white fabric.
    // Only the ink changes tone. No thick outline or pale patch behind it.
    vec3 line_ink = mix(vec3(0.99, 0.975, 0.955), vec3(0.30, 0.265, 0.29),
                        smoothstep(0.46, 0.54, brightness));
    float rose = step(0.18, original.r - original.g) * step(0.08, original.b - original.g);
    vec3 rose_ink = mix(vec3(0.97, 0.74, 0.81), vec3(0.72, 0.22, 0.39),
                        smoothstep(0.46, 0.54, brightness));
    line_ink = mix(line_ink, rose_ink, rose);
    float accent = step(original.b, 0.55) * step(0.55, original.g);
    vec3 ink = mix(line_ink, vec3(0.77, 0.69, 0.22), accent);
    float koi_region = step(1270.0 / 1838.0, UV.x) * (1.0 - step(1694.0 / 1838.0, UV.x));
    if (koi_region > 0.5) {
        // A stable berry colour keeps the character continuous across the hair.
        ink = mix(ink, vec3(0.66, 0.09, 0.29), rose);
        float keyline = 0.0;
        for (int y = -1; y <= 1; y++) {
            for (int x = -1; x <= 1; x++) {
                vec4 neighbour = texture(TEXTURE, UV + vec2(float(x), float(y)) * TEXTURE_PIXEL_SIZE * 2.0);
                float rose_stroke = step(0.18, neighbour.r - neighbour.g) * step(0.08, neighbour.b - neighbour.g);
                keyline = max(keyline, neighbour.a * rose_stroke);
            }
        }
        // About one display pixel of ivory separation, restricted to 恋.
        float border = keyline * 0.92 * (1.0 - original.a);
        float coverage = original.a + border;
        COLOR = vec4((ink * original.a + vec3(0.99, 0.98, 0.96) * border) / max(coverage, 0.001), coverage);
    } else {
        COLOR = vec4(ink, original.a);
    }
}
