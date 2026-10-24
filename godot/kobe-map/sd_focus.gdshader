shader_type spatial;
render_mode unshaded, cull_disabled;

uniform sampler2D character_texture : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform float highlight : hint_range(0.0, 1.0) = 0.0;
uniform float spin = 0.0;
uniform vec4 rim_color : source_color = vec4(1.0, 0.85, 0.65, 1.0);

void vertex() {
	// Keep the original upright billboard, then turn the card around its vertical axis.
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 front = normalize(vec3(INV_VIEW_MATRIX[2].x, 0.0, INV_VIEW_MATRIX[2].z));
	vec3 right = normalize(cross(up, front));
	vec3 side = right * cos(spin) - front * sin(spin);
	vec3 facing = right * sin(spin) + front * cos(spin);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		vec4(side * length(MODEL_MATRIX[0].xyz), 0.0),
		vec4(up * length(MODEL_MATRIX[1].xyz), 0.0),
		vec4(facing * length(MODEL_MATRIX[2].xyz), 0.0), MODEL_MATRIX[3]);
}

void fragment() {
	vec4 ink = texture(character_texture, UV);
	vec2 texel = vec2(10.0) / vec2(textureSize(character_texture, 0));
	float rim = ink.a;
	for (int x = -1; x <= 1; x++) {
		for (int y = -1; y <= 1; y++) {
			rim = max(rim, texture(character_texture, UV + vec2(float(x), float(y)) * texel).a);
		}
	}
	if (ink.a < 0.15 && rim * highlight < 0.15) discard;
	bool silhouette = ink.a < 0.15;
	ALBEDO = silhouette ? rim_color.rgb : mix(ink.rgb, vec3(1.0, 0.96, 0.90), highlight * 0.10);
	EMISSION = silhouette ? rim_color.rgb * highlight * 0.30 : ink.rgb * highlight * 0.06;
}
