shader_type canvas_item;
render_mode unshaded;

uniform sampler2D portrait_mask : filter_linear;
uniform vec4 paper : source_color = vec4(0.985, 0.976, 0.965, 1.0);

void fragment() {
    vec4 art = texture(TEXTURE, UV);
    float portrait = texture(portrait_mask, UV).a;
    // The original CG supplies the actual hair edges and the space between strands.
    // Retaining a little scenery around the silhouette conceals cutout remnants.
    vec2 aura_uv = (UV - vec2(0.555, 0.54)) / vec2(0.40, 0.88);
    float aura = 1.0 - smoothstep(0.45, 1.0, length(aura_uv));
    float left_clearance = smoothstep(0.28, 0.46, UV.x);
    float right_clearance = 1.0 - smoothstep(0.69, 0.98, UV.x);
    float scenery = aura * left_clearance * right_clearance * 0.32;
    float keep = max(portrait, scenery);
    COLOR = vec4(mix(paper.rgb, art.rgb, keep), 1.0);
}
