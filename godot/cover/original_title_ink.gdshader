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
    COLOR = vec4(mix(line_ink, vec3(0.77, 0.69, 0.22), accent), original.a);
}
