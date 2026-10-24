shader_type canvas_item;
uniform sampler2D alternate:source_color;
uniform sampler2D region;
uniform float amount=0.0;
void fragment(){
    COLOR=mix(texture(TEXTURE,UV),texture(alternate,UV),texture(region,UV).r*amount);
}
