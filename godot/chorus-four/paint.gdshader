shader_type canvas_item;
render_mode unshaded;
uniform sampler2D paper : source_color, filter_linear;
uniform sampler2D arrival : filter_linear;
uniform sampler2D surface : source_color, filter_linear;
uniform sampler2D bristles : filter_linear;
uniform float progress = 0.0;
void fragment() {
    float when = texture(arrival, UV).r;
    float fresh = (1.0 - smoothstep(0.0, 0.30, progress - when))
        * (1.0 - smoothstep(0.88, 1.0, progress));
    float cover = (1.0 - smoothstep(progress - 0.003, progress + 0.003, when))
        * (1.0 - 0.80 * (1.0 - texture(bristles, UV).r) * fresh);
    vec3 pigment = mix(texture(paper, UV).rgb, texture(surface, UV).rgb, fresh * 0.9);
    COLOR = vec4(pigment, cover);
}
