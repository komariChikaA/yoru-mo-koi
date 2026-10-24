shader_type canvas_item;
render_mode unshaded;

void fragment() {
    vec2 stride = TEXTURE_PIXEL_SIZE * 2.4;
    float low = 1.0;
    float high = 0.0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            float alpha = texture(TEXTURE, UV + vec2(float(x), float(y)) * stride).a;
            low = min(low, alpha);
            high = max(high, alpha);
        }
    }
    COLOR = vec4(0.78, 0.13, 0.25, high - low);
}
