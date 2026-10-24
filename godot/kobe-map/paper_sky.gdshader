shader_type sky;

uniform sampler2D paper_texture : filter_linear_mipmap, repeat_enable;
uniform vec4 paper_tint : source_color = vec4(0.9804, 0.9765, 0.9647, 1.0);
uniform float paper_strength : hint_range(0.0, 1.0) = 0.32;

void sky() {
	// A screen-facing printed backdrop, without spherical stretching or poles.
	float fiber = texture(paper_texture, SCREEN_UV * vec2(1.4, 0.7875)).r - 0.5;
	COLOR = paper_tint.rgb * (1.0 + fiber * paper_strength);
}
