shader_type canvas_item;
render_mode unshaded;
uniform sampler2D original:source_color,filter_linear,repeat_disable;
uniform sampler2D opening:filter_linear,repeat_disable;
uniform vec4 basis[2];
uniform vec2 upper_points[128];
uniform vec2 lower_points[128];
uniform bool iris_visible=true;

float ridge(int eye,vec2 p,bool upper){
    float y=upper?upper_points[eye*64].y:lower_points[eye*64].y;
    for(int j=0;j<63;j++){
        vec2 a=upper?upper_points[eye*64+j]:lower_points[eye*64+j];
        vec2 b=upper?upper_points[eye*64+j+1]:lower_points[eye*64+j+1];
        if(p.x>=a.x&&p.x<=b.x){y=mix(a.y,b.y,(p.x-a.x)/max(b.x-a.x,0.0001));}
    }
    return y;
}
void fragment(){
    vec4 base=texture(TEXTURE,UV);
    vec2 pixel=UV*vec2(1920.0,1080.0)-vec2(.5);
    vec3 masks=texture(opening,UV).rgb;
    for(int i=0;i<2;i++){
        float native=i==0?masks.r:masks.g;
        if(native<.001||!iris_visible){continue;}
        vec2 axis=basis[i].zw;vec2 delta=pixel-basis[i].xy;
        vec2 p=vec2(dot(delta,axis),dot(delta,vec2(-axis.y,axis.x)));
        float top=ridge(i,p,true);float low=ridge(i,p,false);
        float gap=max(0.0,low-top);
        float coverage=clamp(min(p.y-top,low-p.y)+.5,0.0,1.0)*clamp(gap,0.0,1.0);
        float xmin=upper_points[i*64].x;float xmax=upper_points[i*64+63].x;
        coverage*=step(xmin,p.x)*step(p.x,xmax);
        base.rgb=mix(base.rgb,texture(original,UV).rgb,native*coverage);
    }
    COLOR=base;
}
