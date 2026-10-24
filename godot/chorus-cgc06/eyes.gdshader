shader_type canvas_item;
render_mode unshaded;

uniform sampler2D face_base : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_body : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_iris : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_skin : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_region : filter_linear, repeat_disable;
uniform sampler2D eye_foreground : filter_linear, repeat_disable;
uniform sampler2D native_opening : filter_linear, repeat_disable;
uniform vec4 eye_basis[2];
uniform int eye_count = 0;
uniform vec4 iris_offsets = vec4(0.0);
uniform vec2 iris_scale = vec2(1.0);
uniform vec2 iris_centers[2];
uniform vec4 parts_visible = vec4(1.0); // brow, iris, eye body/upper lid, lower lid
uniform vec2 canvas_size = vec2(1376.0, 752.0);

uniform vec2 upper_points[128];
uniform vec2 lower_points[128];

vec2 opening_point(int eye, int index) {
    return index<64 ? upper_points[eye*64+index] : lower_points[eye*64+127-index];
}

float opening_coverage(int eye, vec2 p, float margin) {
    // Signed spatial coverage of the moving skin gate, intersected with
    // the native opening. Complete eyelid cutouts render as their own meshes.
    bool inside=false;
    float nearest=1e10;
    float top_distance=1e10;
    float bottom_distance=1e10;
    vec2 top_point=vec2(0.0);
    vec2 bottom_point=vec2(0.0);
    float top_y=upper_points[eye*64].y;
    float bottom_y=lower_points[eye*64].y;
    for (int j=0;j<128;j++) {
        vec2 a=opening_point(eye,j);
        vec2 b=opening_point(eye,(j+1)%128);
        vec2 edge=b-a;
        float t=clamp(dot(p-a,edge)/max(dot(edge,edge),0.00000001),0.0,1.0);
        vec2 closest=a+t*edge;
        if (j<63 && p.x>=a.x && p.x<=b.x) {
            top_y=mix(a.y,b.y,clamp((p.x-a.x)/max(b.x-a.x,0.00001),0.0,1.0));
        }
        if (j>=64 && j<127 && p.x>=b.x && p.x<=a.x) {
            bottom_y=mix(b.y,a.y,clamp((p.x-b.x)/max(a.x-b.x,0.00001),0.0,1.0));
        }
        float distance_squared=dot(p-closest,p-closest);
        nearest=min(nearest,distance_squared);
        if (j<63 && distance_squared<top_distance) { top_distance=distance_squared;top_point=closest; }
        if (j>=64 && j<127 && distance_squared<bottom_distance) { bottom_distance=distance_squared;bottom_point=closest; }
        if ((a.y>p.y)!=(b.y>p.y)) {
            float crossing=a.x+(p.y-a.y)*(b.x-a.x)/(b.y-a.y);
            if (p.x<crossing) { inside=!inside; }
        }
    }
    float signed_distance=sqrt(nearest)*(inside ? 1.0 : -1.0);
    // Spatial pixel coverage vanishes at contact, including the last slit.
    float gap=eye==1 ? bottom_y-top_y : length(top_point-bottom_point);
    return clamp(signed_distance+margin+0.5,0.0,1.0)*clamp(gap,0.0,1.0);
}

vec4 puppet(vec2 uv) {
    vec4 result=texture(face_base,uv);
    vec2 pixel=uv*canvas_size-vec2(0.5);
    for (int i=0; i<2; i++) {
        if (i>=eye_count) { break; }
        vec3 masks=texture(eye_region,uv).rgb;
        float influence=(i==0 ? masks.r : masks.g)*(1.0-texture(eye_foreground,uv).r);
        if (influence<=0.0) { continue; }
        vec2 axis=eye_basis[i].zw;
        vec2 normal=vec2(-axis.y,axis.x);
        vec2 delta=pixel-eye_basis[i].xy;
        float x=dot(delta,axis);
        float y=dot(delta,normal);
        vec4 body=texture(eye_body,uv);
        vec2 iris_offset=i==0 ? iris_offsets.xy : iris_offsets.zw;
        vec2 center=iris_centers[i];
        vec2 iris_pixel=center+(pixel-center-axis*iris_offset.x-normal*iris_offset.y)/clamp(iris_scale[i],0.7,1.3);
        vec4 iris=texture(eye_iris,(iris_pixel+vec2(0.5))/canvas_size);
        vec3 skin=texture(eye_skin,uv).rgb;
        vec3 fixed_eye=mix(skin,body.rgb,body.a*parts_visible.z);
        fixed_eye=mix(fixed_eye,iris.rgb,iris.a*parts_visible.y);
        // Spatial pixel coverage of the actual mesh opening; zero at contact.
        // Iris RGB/UV never deform with either lid.
        // Clip the iris and sclera directly at the actual eyelid mesh.
        // Only the separate native corner ink uses an expanded spatial gate.
        float native_inside=i==0 ? texture(native_opening,uv).r : texture(native_opening,uv).g;
        float inside=opening_coverage(i,vec2(x,y),0.0)*native_inside;
        vec3 eye=mix(skin,fixed_eye,inside);
        result.rgb=mix(result.rgb,eye,influence);
    }
    return result;
}

void fragment() {
    COLOR=puppet(UV);
}
