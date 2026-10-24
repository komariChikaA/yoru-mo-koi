shader_type canvas_item;
uniform float blur_px = 0.0;

void fragment() {
	vec4 colour = texture(TEXTURE,UV);
	if (blur_px > 0.05) {
		// Dense Gaussian taps avoid separate image ghosts during the focus reveal.
		vec2 step_uv = TEXTURE_PIXEL_SIZE * blur_px / 6.0;
		vec3 sum = vec3(0.0);
		float total = 0.0;
		for (int y = -6; y <= 6; y++) {
			for (int x = -6; x <= 6; x++) {
				vec2 offset = vec2(float(x),float(y));
				float weight = exp(-dot(offset,offset)/12.5);
				sum += texture(TEXTURE,UV+offset*step_uv).rgb*weight;
				total += weight;
			}
		}
		colour.rgb = sum/total;
	}
	COLOR = colour;
}
