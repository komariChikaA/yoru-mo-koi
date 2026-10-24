shader_type spatial;
render_mode diffuse_lambert, specular_disabled;

uniform vec4 paint_color : source_color = vec4(0.8, 0.8, 0.8, 1.0);
uniform bool facade_enabled = false;
uniform sampler2D facade_texture : source_color, filter_nearest_mipmap;
uniform sampler2D paper_texture : filter_linear_mipmap, repeat_enable;
uniform float texture_clock = 0.0;
uniform float map_fade : hint_range(0.0, 1.0) = 0.0;
uniform float boil_fps : hint_range(1.0, 24.0) = 10.0;
uniform float grain_strength : hint_range(0.0, 0.4) = 0.10;
uniform float halftone_strength : hint_range(0.0, 0.4) = 0.14;
uniform float dot_spacing : hint_range(3.0, 12.0) = 5.5;
varying vec3 world_position;
varying vec3 world_normal;

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
	// Reveal the intact model at ground level, including during shadow rendering.
	if (world_position.y < 0.0) {
		discard;
	}
	float frame = floor(texture_clock * boil_fps);
	vec2 shift = vec2(hash21(vec2(frame, 4.0)), hash21(vec2(frame, 19.0)));
	vec3 weights = pow(abs(normalize(world_normal)), vec3(5.0));
	weights /= max(dot(weights, vec3(1.0)), 0.001);
	float fiber = texture(paper_texture, world_position.yz * 0.08 + shift).r * weights.x;
	fiber += texture(paper_texture, world_position.xz * 0.08 + shift).r * weights.y;
	fiber += texture(paper_texture, world_position.xy * 0.08 + shift).r * weights.z;
	float grain = hash21(floor(FRAGCOORD.xy / 1.4) + shift * 153.0) - 0.5;
	vec2 dot_position = mat2(vec2(0.7071, 0.7071), vec2(-0.7071, 0.7071)) * FRAGCOORD.xy;
	vec2 cell = fract((dot_position + (shift - 0.5) * 0.4) / dot_spacing) - 0.5;
	float distance_to_dot = length(cell);
	float aa = fwidth(distance_to_dot);
	float dots = 1.0 - smoothstep(0.20 - aa, 0.20 + aa, distance_to_dot);
	vec3 facade = facade_enabled ? texture(facade_texture, UV).rgb : vec3(1.0);
	vec3 printed = paint_color.rgb * facade * (1.0 + (fiber - 0.5) * 0.35 + grain * grain_strength);
	printed = mix(printed, printed * 0.58, dots * halftone_strength);
	ALBEDO = clamp(printed, vec3(0.0), vec3(1.0)) * (1.0 - map_fade);
	EMISSION = vec3(0.89, 0.92, 0.93) * map_fade;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
