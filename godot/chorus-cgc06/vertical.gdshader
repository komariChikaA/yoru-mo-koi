shader_type canvas_item;
render_mode unshaded;
uniform sampler2D image : filter_linear, repeat_disable;
uniform float blur_px=0.0;
const float weights[9]=float[](0.0276306,0.0662822,0.1238315,0.1801738,0.2041638,0.1801738,0.1238315,0.0662822,0.0276306);
void fragment(){
    vec4 color=vec4(0.0);
    for(int i=0;i<9;i++){
        color+=texture(image,UV+vec2(0.0,(float(i)-4.0)*blur_px/4.0/1080.0))*weights[i];
    }
    COLOR=vec4(color.rgb,1.0);
}
