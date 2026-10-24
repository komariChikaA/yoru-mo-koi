shader_type canvas_item;
render_mode unshaded;

uniform sampler2D incoming : source_color, filter_linear, repeat_disable;
uniform float blend = 0.0;
uniform float outgoing_shift = 0.0;
uniform float incoming_shift = 0.0;
uniform float blur_px = 0.0;
uniform vec2 shock_px = vec2(0.0);
uniform float shock_roll = 0.0;
uniform float shock_zoom = 1.0;

void fragment() {
    vec4 outgoing_color = vec4(0.0);
    vec4 incoming_color = vec4(0.0);
    float total = 0.0;
    vec2 pixel = (UV-0.5)*vec2(1920.0,1080.0)/shock_zoom;
    float c = cos(shock_roll);
    float s = sin(shock_roll);
    vec2 outgoing_uv = (vec2(c*pixel.x-s*pixel.y,s*pixel.x+c*pixel.y)+shock_px)/vec2(1920.0,1080.0)+0.5;
    for (int i = -16; i <= 16; i++) {
        float q = float(i) / 16.0;
        float weight = exp(-2.0*q*q);
        vec2 shutter = vec2(q*blur_px/1920.0,0.0);
        outgoing_color += texture(TEXTURE,clamp(outgoing_uv+vec2(outgoing_shift,0.0)+shutter,vec2(0.001),vec2(0.999)))*weight;
        incoming_color += texture(incoming,clamp(UV-vec2(incoming_shift,0.0)+shutter,vec2(0.001),vec2(0.999)))*weight;
        total += weight;
    }
    COLOR = mix(outgoing_color,incoming_color,blend)/total;
}
