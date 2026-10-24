shader_type canvas_item;
render_mode unshaded;
uniform sampler2D screen_image : hint_screen_texture, filter_linear_mipmap;
uniform float clock = 0.0;
uniform float flash = 0.0;
void fragment() {
    vec3 ink=textureLod(screen_image,SCREEN_UV,0.0).rgb;
    vec3 focus=textureLod(screen_image,SCREEN_UV,2.2).rgb;
    vec3 soft=textureLod(screen_image,SCREEN_UV,3.5).rgb;
    vec3 broad=textureLod(screen_image,SCREEN_UV,5.0).rgb;
    vec3 halo=textureLod(screen_image,SCREEN_UV,6.5).rgb;
    float luma=dot(soft,vec3(.2126,.7152,.0722));
    // Deliberate screen soft focus; the original repaired surfaces stay intact.
    vec3 graded=mix(ink,focus,.62)*vec3(1.025,1.003,.965)+vec3(.008,.003,0.0);
    float canopy=exp(-dot((SCREEN_UV-vec2(.12,-.08))*vec2(1.0,1.1),(SCREEN_UV-vec2(.12,-.08))*vec2(1.0,1.1))*2.4);
    // Overlapping small glow and wide diffusion spread the warm highlights.
    vec3 bloom=max(soft-vec3(.60),vec3(0.0))*.32+max(broad-vec3(.58),vec3(0.0))*.30+max(halo-vec3(.55),vec3(0.0))*.26;
    float haze=(.035+.065*canopy)*(0.98+.02*sin(clock*.43));
    vec3 light=(bloom+vec3(1.0,.82,.59)*haze)*smoothstep(.12,.9,luma);
    vec3 result=1.0-(1.0-clamp(graded,0.0,1.0))*(1.0-light);
    // The canopy sun spreads from the upper left into a warm occluding veil.
    // A fully opaque crest hides the camera cut; the graded CG is unchanged
    // outside this short exposure event.
    vec2 sun_offset=(SCREEN_UV-vec2(-.10,-.18))*vec2(1.77778,1.0);
    float radius=mix(.12,2.7,smoothstep(0.0,.85,flash));
    float sun_halo=exp(-dot(sun_offset,sun_offset)/(radius*radius));
    float angle=atan(sun_offset.y,sun_offset.x);
    float shafts=pow(max(cos(angle*18.0+.35),0.0),5.0);
    float veil=clamp(flash*(.25+1.2*sun_halo),0.0,1.0);
    veil=mix(veil,1.0,smoothstep(.82,.99,flash));
    vec3 sun_color=mix(vec3(1.0,.962,.875),vec3(1.0,.992,.961),clamp(sun_halo+.12*shafts,0.0,1.0));
    vec3 scatter=vec3(1.0,.79,.42)*flash*(.12+.08*shafts)*sun_halo;
    vec3 exposed=1.0-(1.0-result)*(1.0-scatter);
    COLOR=vec4(mix(exposed,sun_color,veil),1.0);
}
