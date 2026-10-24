shader_type canvas_item;
render_mode unshaded;
uniform sampler2D original:source_color,filter_linear,repeat_disable;
uniform sampler2D opening:filter_linear,repeat_disable;
uniform sampler2D glints:source_color,filter_linear,repeat_disable;
uniform vec4 basis[2];
uniform vec2 upper_points[128];
uniform vec2 lower_points[128];
uniform vec2 glint_offset=vec2(0.0);
uniform bool iris_visible=true;

float ridge(int eye,vec2 p,bool upper){
    vec2 first=upper?upper_points[eye*64]:lower_points[eye*64];
    vec2 last=upper?upper_points[eye*64+63]:lower_points[eye*64+63];
    if(p.x<=first.x){return first.y;}
    if(p.x>=last.x){return last.y;}
    for(int j=0;j<63;j++){
        vec2 a=upper?upper_points[eye*64+j]:lower_points[eye*64+j];
        vec2 b=upper?upper_points[eye*64+j+1]:lower_points[eye*64+j+1];
        if(p.x>=a.x&&p.x<=b.x){return mix(a.y,b.y,(p.x-a.x)/max(b.x-a.x,0.0001));}
    }
    return last.y;
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
        float coverage=clamp(min(p.y-top,low-p.y)+.5,0.0,1.0)*clamp(low-top,0.0,1.0);
        coverage*=step(upper_points[i*64].x,p.x)*step(p.x,upper_points[i*64+63].x);
        // The eyeball always samples its original UV. Only the eyelid aperture
        // changes; no iris squash, remapping, or expression-image dissolve.
        vec3 iris=texture(original,UV).rgb;
        vec4 glint=texture(glints,UV-glint_offset/vec2(1920.0,1080.0));
        iris=mix(iris,glint.rgb,glint.a);
        base.rgb=mix(base.rgb,iris,native*coverage);
    }
    COLOR=base;
}
