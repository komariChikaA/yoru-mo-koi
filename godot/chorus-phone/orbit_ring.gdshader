shader_type spatial;
render_mode unshaded, cull_disabled;
uniform float reveal = 0.0;
uniform float opacity = 0.0;
uniform float head = 0.0;
uniform float dashes = 0.0;
uniform vec4 ink : source_color = vec4(0.596,0.478,0.671,1.0);
varying vec2 radial;
void vertex() { radial = VERTEX.xz; }
void fragment() {
	float angle = (atan(radial.x, radial.y) + 3.14159265) / 6.2831853;
	if (angle > reveal || (dashes > 0.0 && fract(angle * dashes) > 0.58)) discard;
	float distance = abs(fract(angle - head + 0.5) - 0.5);
	ALBEDO = mix(ink.rgb, vec3(1.0,0.94,0.85), 1.0-smoothstep(0.0,0.10,distance));
	ALPHA = opacity;
}
