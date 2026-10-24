shader_type canvas_item;
render_mode unshaded, blend_premul_alpha;

void fragment() {
    vec4 entry = texture(TEXTURE, UV);
    // 3D alpha is premultiplied in linear light before the viewport's sRGB
    // transfer. Reassociate it in canvas space so a fading card stays neutral.
    vec3 linear = mix(entry.rgb / 12.92,
        pow((entry.rgb + .055) / 1.055, vec3(2.4)),
        step(vec3(.04045), entry.rgb));
    vec3 straight = max(linear / max(entry.a, .00001), vec3(0.0));
    vec3 encoded = mix(straight * 12.92,
        1.055 * pow(straight, vec3(1.0 / 2.4)) - .055,
        step(vec3(.0031308), straight));
    COLOR = vec4(clamp(encoded, 0.0, 1.0) * entry.a, entry.a);
}
