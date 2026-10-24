shader_type spatial;
render_mode unshaded;
uniform sampler2D street_texture : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D overview_texture : source_color, filter_linear_mipmap_anisotropic;
uniform float map_emphasis : hint_range(0.0, 1.0) = 0.0;
void fragment() {
	ALBEDO = mix(texture(street_texture, UV).rgb, texture(overview_texture, UV).rgb, map_emphasis);
}
