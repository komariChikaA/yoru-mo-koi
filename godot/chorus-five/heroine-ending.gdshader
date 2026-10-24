shader_type canvas_item;
render_mode unshaded;
uniform sampler2D screen_image : hint_screen_texture, filter_linear;
uniform sampler2D portrait_0 : filter_linear_mipmap;
uniform sampler2D portrait_1 : filter_linear_mipmap;
uniform sampler2D portrait_2 : filter_linear_mipmap;
uniform sampler2D portrait_3 : filter_linear_mipmap;
uniform sampler2D portrait_4 : filter_linear_mipmap;
uniform vec2 hubs[5];
uniform float angles[5];
uniform float radii[5];
uniform float opacities[5];
uniform vec2 face_centres[5];
uniform vec2 face_uvs[5];
uniform float image_sizes[5];
uniform vec4 inks[5];
uniform float narrowing = .78;
uniform sampler2D memory_0 : filter_linear_mipmap;
uniform sampler2D memory_1 : filter_linear_mipmap;
uniform sampler2D memory_2 : filter_linear_mipmap;
uniform int memory_previous = 0;
uniform int memory_current = 0;
uniform float memory_mix = 1.0;
uniform float scene_warmth = .95;
uniform float scene_softness = .78;
uniform float scene_glow = .72;
uniform float scene_vignette = .025;
uniform float scene_exposure = 1.15;
uniform vec4 cg_rect = vec4(770.0,235.0,1820.0,885.0);
uniform float page_mix = 0.0;
uniform float cg_mix = 0.0;
uniform float cg_reveal = 0.0;
uniform float cg_outline = 0.0;
uniform float footer_rule = 0.0;
uniform float capture_marks = 0.0;
uniform vec2 trail_hubs[2];
uniform float trail_radii[2];
uniform float trail_mix = 0.0;
uniform vec2 rect_half_ratio;
uniform vec2 rect_offset_ratio;
uniform vec4 closing_rect = vec4(-32.0,-32.0,1952.0,1112.0);
uniform float curved = 0.0;
uniform float portrait_mix = 0.0;

// Three circular arcs of a Reuleaux triangle, narrowed across its width.
// Each piece has its own centre; there is no shared pentagon boundary.
float triangle_distance(vec2 p) {
    p.x/=narrowing;
    float d = -10.0;
    for (int j=0;j<3;j++) {
        float a=1.5707963268+float(j)*2.0943951024;
        d=max(d,length(p-vec2(cos(a),sin(a)))-1.7320508076);
    }
    return d*narrowing;
}

float rounded_box(vec2 p, vec2 half_size, float radius) {
    vec2 q=abs(p)-half_size+radius;
    return length(max(q,vec2(0.0)))+min(max(q.x,q.y),0.0)-radius;
}

float line_distance(vec2 p, vec2 a, vec2 b) {
    vec2 v=b-a;
    return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.0,1.0));
}

vec3 memory_source(int index, vec2 uv) {
    if(index==0) return texture(memory_0,uv).rgb;
    if(index==1) return texture(memory_1,uv).rgb;
    return texture(memory_2,uv).rgb;
}

vec3 memory_soft_source(int index, vec2 uv, float lod) {
    if(index==0) return textureLod(memory_0,uv,lod).rgb;
    if(index==1) return textureLod(memory_1,uv,lod).rgb;
    return textureLod(memory_2,uv,lod).rgb;
}

vec3 scene_filtered(int index, vec2 uv, float transition_blur) {
    vec3 original=memory_source(index,uv);
    vec2 texel=vec2(1.0/1920.0,1.0/1080.0);
    vec3 soft=vec3(0.0);
    vec3 bloom=vec3(0.0);
    float blur_radius=8.0+32.0*transition_blur;
    float blur_lod=3.0+2.25*transition_blur;
    // Overlapping mip footprints make a continuous Gaussian veil rather than
    // separated ring copies of sharp window and brick edges.
    for(int y=-2;y<=2;y++) {
        float wy=y==0?6.0:(abs(y)==1?4.0:1.0);
        for(int x=-2;x<=2;x++) {
            float wx=x==0?6.0:(abs(x)==1?4.0:1.0);
            soft+=memory_soft_source(index,uv+vec2(float(x),float(y))*texel*blur_radius,blur_lod)*wx*wy;
        }
    }
    for(int j=0;j<8;j++) {
        float a=float(j)*.7853981634;
        vec2 direction=vec2(cos(a),sin(a));
        vec3 sample_colour=memory_soft_source(index,uv+direction*texel*(24.0+20.0*transition_blur),4.0+1.4*transition_blur);
        bloom+=max(sample_colour-vec3(.55),vec3(0.0));
    }
    vec3 colour=mix(original,soft/256.0,mix(scene_softness,1.0,transition_blur));
    colour*=scene_exposure;
    colour*=mix(vec3(1.0),vec3(1.045,1.013,.955),scene_warmth);
    colour+=vec3(.012,.007,.001)*scene_warmth;
    colour+=bloom/8.0*scene_glow;
    // Broad upper-left daylight veil, with a small warm lift in the shadows.
    float sunlight=exp(-dot((uv-vec2(.12,.02))*vec2(.8,1.0),(uv-vec2(.12,.02))*vec2(.8,1.0))*3.2);
    colour=mix(colour,vec3(1.0,.985,.95),sunlight*.070*scene_warmth);
    colour=mix(colour,vec3(1.0,.985,.97),.045*scene_warmth);
    float edge=smoothstep(.36,.76,length((uv-.5)*vec2(1.1,1.0)));
    return clamp(colour*(1.0-edge*scene_vignette),vec3(0.0),vec3(1.0));
}

vec3 paper(vec2 pixel) {
    vec2 grid=mat2(vec2(.707107,-.707107),vec2(.707107,.707107))*pixel;
    float dots=1.0-smoothstep(.35,.95,length(mod(grid,vec2(26.0))-13.0));
    vec2 motif=mod(pixel+vec2(floor(pixel.y/235.0)*83.0,0.0),vec2(305.0,235.0))-vec2(152.5,117.5);
    float theta=atan(motif.y,motif.x);
    float flower=1.0-smoothstep(-.7,.7,length(motif)-(6.0+2.0*cos(theta*5.0)));
    vec3 base=vec3(1.0,.997,.989);
    return mix(base,vec3(.95,.72,.77),dots*.055+flower*.045);
}

vec4 source(int i, vec2 uv) {
    if (i==0) return texture(portrait_0,uv);
    if (i==1) return texture(portrait_1,uv);
    if (i==2) return texture(portrait_2,uv);
    if (i==3) return texture(portrait_3,uv);
    return texture(portrait_4,uv);
}

vec3 separation(vec3 rgb, vec3 ink) {
    float l=dot(rgb,vec3(.2126,.7152,.0722));
    // Reference-style ink + white with one pale plate. Deep source shadows
    // use the full chromatic ink rather than multiplying it towards black.
    float aa=clamp(fwidth(l)*.65,.007,.045);
    vec3 c=mix(ink,mix(ink,vec3(1.0),.72),smoothstep(.61-aa,.61+aa,l));
    return mix(c,vec3(1.0),smoothstep(.78-aa,.78+aa,l));
}

void fragment() {
    vec2 pixel=FRAGCOORD.xy;
    vec3 result=mix(vec3(1.0),paper(pixel),page_mix);
    vec2 card_centre=(cg_rect.xy+cg_rect.zw)*.5;
    vec2 card_half=(cg_rect.zw-cg_rect.xy)*.5;
    float card_d=rounded_box(pixel-card_centre,card_half,34.0);
    float shadow_d=rounded_box(pixel-card_centre-vec2(0.0,7.0),card_half,34.0);
    float shadow=exp(-max(shadow_d,0.0)/8.0)*.055*cg_mix*smoothstep(0.0,.3,cg_reveal);
    result=mix(result,vec3(.70,.60,.61),shadow);
    vec2 photo_uv=(pixel-cg_rect.xy)/(cg_rect.zw-cg_rect.xy);
    float sweep=(photo_uv.x+.30*photo_uv.y)/1.30;
    float photo_aspect=(cg_rect.z-cg_rect.x)/(cg_rect.w-cg_rect.y);
    photo_uv.x=(photo_uv.x-.5)*photo_aspect/(16.0/9.0)+.5;
    float wipe_edge=cg_reveal*1.04-.02;
    float wipe=1.0-smoothstep(wipe_edge-.006,wipe_edge+.006,sweep);
    float card_mask=(1.0-smoothstep(-.8,.8,card_d))*cg_mix*wipe;
    if(card_mask>0.0) {
        vec3 photo;
        if(memory_mix>=.99999) photo=scene_filtered(memory_current,photo_uv,0.0);
        else if(memory_mix<=.00001) photo=scene_filtered(memory_previous,photo_uv,0.0);
        else {
            float progress=clamp(memory_mix,0.0,1.0);
            float transition_blur=sin(progress*3.1415926536);
            // A stationary frame: blur out, crossfade, then return to focus.
            // Both sources use the same UV throughout the transition.
            photo=mix(scene_filtered(memory_previous,photo_uv,transition_blur),scene_filtered(memory_current,photo_uv,transition_blur),progress);
        }
        result=mix(result,photo,card_mask);
    }
    float trace_phase=fract((atan((pixel.y-card_centre.y)/card_half.y,(pixel.x-card_centre.x)/card_half.x)+2.35619449)/6.28318531+1.0);
    float outline=(1.0-smoothstep(.7,1.8,abs(card_d)))*(1.0-smoothstep(cg_outline,cg_outline+.008,trace_phase))*step(.000001,cg_outline);
    result=mix(result,vec3(.88,.68,.73),outline*.65);
    float glint=exp(-pow((sweep-wipe_edge)/.004,2.0))*step(.01,cg_reveal)*(1.0-step(.99,cg_reveal))*card_mask;
    result=mix(result,vec3(1.0,.98,.96),glint*.40);
    float divider=(1.0-smoothstep(.4,1.0,abs(pixel.y-922.0)))*step(mix(1120.0,130.0,footer_rule),pixel.x)*step(pixel.x,mix(1120.0,1790.0,footer_rule))*page_mix;
    result=mix(result,vec3(.88,.76,.78),divider*.30);
    if(trail_mix>0.0) {
        for(int j=0;j<2;j++) {
            // The delayed positions share the live frame's morph, so neither
            // echo leaves a rectangular outline behind a curved window.
            vec2 mid=trail_hubs[j]+rect_offset_ratio*trail_radii[j];
            vec2 edge=abs(pixel-mid)-rect_half_ratio*trail_radii[j];
            float rect_d=max(edge.x,edge.y);
            vec2 v=pixel-trail_hubs[j];
            float ca=cos(angles[0]), sa=sin(angles[0]);
            vec2 local=vec2(ca*v.x+sa*v.y,-sa*v.x+ca*v.y)/trail_radii[j];
            float triangle_d=triangle_distance(local)*trail_radii[j];
            float d=abs(mix(rect_d,triangle_d,curved));
            float trace=(1.0-smoothstep(.6,1.5,d))*trail_mix*(.17-float(j)*.055);
            result=mix(result,inks[0].rgb,trace);
        }
    }
    // New cards peel out from BEHIND the preceding card, not on top of its face.
    for (int i=4;i>=0;i--) {
        if(opacities[i]<=0.0) continue;
        vec2 v=pixel-hubs[i];
        float ca=cos(angles[i]), sa=sin(angles[i]);
        vec2 local=vec2(ca*v.x+sa*v.y,-sa*v.x+ca*v.y)/radii[i];
        float d=triangle_distance(local)*radii[i];
        if(i==0 && curved<1.0) {
            vec2 e=abs(pixel-(closing_rect.xy+closing_rect.zw)*.5)-(closing_rect.zw-closing_rect.xy)*.5;
            d=mix(max(e.x,e.y),d,curved);
        }
        float coverage=(1.0-smoothstep(-.8,.8,d))*opacities[i];
        if(coverage<=0.0) continue;
        // Intentionally use SCREEN axes here, never `local`: the window and
        // its orbital position rotate while every portrait keeps its angle.
        vec2 uv=(pixel-face_centres[i])/image_sizes[i]+face_uvs[i];
        vec4 raw=source(i,uv);
        vec3 plate=separation(mix(vec3(1.0),raw.rgb,raw.a),inks[i].rgb);
        if(i==0 && portrait_mix<1.0) {
            float colour_coord=clamp((pixel.x-hubs[i].x)/(radii[i]*2.0)+.5,0.0,1.0);
            float colour_wipe=1.0-smoothstep(portrait_mix*1.10-.057,portrait_mix*1.10-.043,colour_coord);
            plate=mix(texture(screen_image,SCREEN_UV).rgb,plate,colour_wipe);
        }
        float rim=smoothstep(-4.2,-3.0,d);
        plate=mix(plate,inks[i].rgb,rim);
        result=mix(result,plate,coverage);
    }
    if(capture_marks>0.0) {
        for(int j=0;j<4;j++) {
            vec2 side=vec2(j%2==0?1.0:-1.0,j<2?1.0:-1.0);
            vec2 corner=vec2(j%2==0?closing_rect.x:closing_rect.z,j<2?closing_rect.y:closing_rect.w)-side*8.0;
            float d=min(line_distance(pixel,corner,corner+vec2(side.x*28.0,0.0)),line_distance(pixel,corner,corner+vec2(0.0,side.y*28.0)));
            result=mix(result,inks[0].rgb,(1.0-smoothstep(.8,1.8,d))*capture_marks*.8);
        }
    }
    COLOR=vec4(result,1.0);
}
