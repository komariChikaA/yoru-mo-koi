shader_type spatial;
render_mode unshaded, cull_disabled;

uniform vec4 route_color : source_color = vec4(1.0);
uniform float reveal : hint_range(0.0, 1.0) = 1.0;

void fragment() {
	if (UV.x > reveal) discard;
	ALBEDO = route_color.rgb;
}
