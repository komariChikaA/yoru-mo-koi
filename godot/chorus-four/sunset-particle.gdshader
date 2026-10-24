shader_type canvas_item;
render_mode unshaded, blend_mix;

uniform sampler2D exclusion_mask : filter_linear, repeat_disable;
uniform vec2 native_size = vec2(1920.0, 1080.0);

varying vec2 native_position;
varying vec4 sprite_tint;

void vertex() {
    // The camera acts on the finished card, after this native-space viewport.
    native_position = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
    sprite_tint = COLOR;
}

void fragment() {
    vec2 mask_uv = clamp(native_position / native_size, vec2(0.0), vec2(1.0));
    float allowed = 1.0 - clamp(texture(exclusion_mask, mask_uv).r, 0.0, 1.0);
    vec4 mote = texture(TEXTURE, UV);
    // Preserve the actual CG highlight's color, shape and padded native alpha.
    COLOR = vec4(mote.rgb * sprite_tint.rgb, mote.a * sprite_tint.a * allowed);
    if (allowed <= 0.0) {
        COLOR = vec4(0.0);
    }
}
