shader_type canvas_item;
uniform float silhouette = 0.0;
void fragment() {
	vec4 source = texture(TEXTURE, UV);
	COLOR = vec4(mix(source.rgb, vec3(1.0), silhouette), source.a);
}
