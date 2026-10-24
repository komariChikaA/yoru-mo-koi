shader_type canvas_item;
render_mode unshaded;

uniform sampler2D receiver : filter_linear, repeat_disable;
uniform vec4 ink : source_color = vec4(0.47,0.22,0.17,0.15);
varying vec2 world_pixel;

void vertex() {
    world_pixel = (MODEL_MATRIX * vec4(VERTEX,0.0,1.0)).xy;
}

void fragment() {
    // The skinned silhouette moves with the bangs; only repaired facial skin
    // receives it. UV stays on the source hair while the receiver stays fixed.
    float coverage = texture(TEXTURE,UV).r;
    coverage *= texture(receiver,world_pixel / vec2(1920.0,1080.0)).r;
    COLOR = vec4(ink.rgb,ink.a*coverage);
}
