shader_type canvas_item;
render_mode unshaded;

void fragment() {
    vec4 original = texture(TEXTURE, UV);
    // The original artwork and its textured shadows stay intact. Its ink is
    // translucent (maximum source alpha 212), so strengthen coverage for CG use.
    COLOR = vec4(original.rgb, min(original.a * 1.6, 1.0));
}
