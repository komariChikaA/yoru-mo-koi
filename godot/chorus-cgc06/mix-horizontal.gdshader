shader_type canvas_item;
render_mode unshaded;
uniform sampler2D closeup : filter_linear, repeat_disable;
uniform sampler2D overview : filter_linear, repeat_disable;
uniform float blend_amount=0.0;
uniform float blur_px=0.0;
const float weights[9]=float[](0.0276306,0.0662822,0.1238315,0.1801738,0.2041638,0.1801738,0.1238315,0.0662822,0.0276306);
void fragment(){
    vec4 color=vec4(0.0);
    for(int i=0;i<9;i++){
        vec2 p=UV+vec2((float(i)-4.0)*blur_px/4.0/1920.0,0.0);
        color+=mix(texture(closeup,p),texture(overview,p),blend_amount)*weights[i];
    }
    COLOR=vec4(color.rgb,1.0);
}
