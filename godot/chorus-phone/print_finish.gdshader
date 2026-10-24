shader_type canvas_item;
uniform float blur_px = 0.0;
uniform float blocks = 0.0;
uniform float dots = 0.0;
uniform float pale = 0.0;
uniform float opacity = 1.0;
uniform vec2 subject = vec2(0.36, 0.5);

void fragment() {
	vec2 dx = TEXTURE_PIXEL_SIZE * blur_px * vec2(1.0, 0.0);
	vec2 dy = TEXTURE_PIXEL_SIZE * blur_px * vec2(0.0, 1.0);
	vec3 original = texture(TEXTURE, UV).rgb * 0.227027;
	original += (texture(TEXTURE,UV+dx*1.384615).rgb + texture(TEXTURE,UV-dx*1.384615).rgb
	           + texture(TEXTURE,UV+dy*1.384615).rgb + texture(TEXTURE,UV-dy*1.384615).rgb) * 0.158108;
	original += (texture(TEXTURE,UV+dx*3.230769).rgb + texture(TEXTURE,UV-dx*3.230769).rgb
	           + texture(TEXTURE,UV+dy*3.230769).rgb + texture(TEXTURE,UV-dy*3.230769).rgb) * 0.035135;
	vec2 cell = vec2(34.0, 19.0);
	vec2 pos = UV * cell;
	vec2 f = fract(pos);
	// Two staggered triangles per cell, retaining the room's composition.
	vec2 offset = f.x + f.y > 1.0 ? vec2(0.72) : vec2(0.28);
	vec3 block_color = texture(TEXTURE, (floor(pos) + offset) / cell).rgb;
	block_color = floor(block_color * 6.0 + 0.5) / 6.0;
	block_color = mix(block_color, vec3(1.0, 0.925, 0.873), 0.16);
	float phone_mask = 1.0 - smoothstep(0.12,0.19,length((UV-subject)*vec2(1.2,0.5)));
	vec3 phone_blocks = floor(original * 4.0 + 0.5) / 4.0;
	block_color = mix(block_color, phone_blocks, phone_mask);
	vec3 col = mix(original, block_color, blocks);
	float away = smoothstep(0.15, 0.28, length((UV - subject) * vec2(0.7, 1.0)));
	vec2 dot_uv = fract(UV * vec2(192.0, 108.0)) - 0.5;
	float dot_ink = 1.0 - smoothstep(0.13, 0.22, length(dot_uv));
	col *= 1.0 - dot_ink * dots * away * 0.19;
	col = mix(col, vec3(0.991, 0.966, 0.933), pale);
	float grain = fract(sin(dot(UV * vec2(1920.0,1080.0), vec2(12.9898,78.233))) * 43758.5453);
	COLOR = vec4(col + (grain - 0.5) * 0.008, opacity);
}
