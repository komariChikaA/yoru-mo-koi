shader_type canvas_item;
render_mode unshaded;

uniform sampler2D weights0 : filter_linear, repeat_disable;
uniform sampler2D weights1 : filter_linear, repeat_disable;
uniform sampler2D weights2 : filter_linear, repeat_disable;
uniform sampler2D weights3 : filter_linear, repeat_disable;
uniform sampler2D eye_open : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_skin : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_region : filter_linear, repeat_disable;
uniform sampler2D eye_foreground : filter_linear, repeat_disable;
uniform sampler2D upper_lid : source_color, filter_linear, repeat_disable;
uniform sampler2D lower_lid : source_color, filter_linear, repeat_disable;
uniform sampler2D eye_curves : filter_linear, repeat_disable;
uniform sampler2D eye_ink : source_color, filter_nearest, repeat_disable;
uniform vec4 eye_basis[2]; // origin.xy, local horizontal axis.zw
uniform vec4 eye_bounds[2]; // x_min, x_max, lash width, original lash contour mode
uniform int eye_count = 0;
uniform vec4 motions[12]; // x/y in pixels, z in radians, w unused
uniform vec2 pivots[12];
uniform float blink_upper = 0.0;
uniform float blink_lower = 0.0;
uniform vec2 canvas_size = vec2(1920.0, 1080.0);

vec4 over(vec4 background, vec4 foreground) {
    return vec4(mix(background.rgb, foreground.rgb, foreground.a), background.a);
}

vec4 eyelids(vec4 original, vec2 uv) {
    if (eye_count == 0 || max(blink_upper, blink_lower) < 0.00001) {
        return original;
    }
    vec2 pixel = uv * canvas_size;
    for (int i = 0; i < 2; i++) {
        if (i >= eye_count) { break; }
        vec2 axis = eye_basis[i].zw;
        vec2 normal = vec2(-axis.y, axis.x);
        vec2 delta = pixel-eye_basis[i].xy;
        float x = dot(delta, axis);
        float y = dot(delta, normal);
        float u = (x-eye_bounds[i].x)/(eye_bounds[i].y-eye_bounds[i].x);
        float margin = 14.0/(eye_bounds[i].y-eye_bounds[i].x);
        if (u < -margin || u > 1.0+margin) { continue; }
        float curve_x = (clamp(u,0.0,1.0)*511.0+0.5)/512.0;
        vec4 upper_curve = texture(eye_curves,vec2(curve_x,(float(i)*3.0+0.5)/6.0));
        vec4 lower_curve = texture(eye_curves,vec2(curve_x,(float(i)*3.0+1.5)/6.0));
        float top = upper_curve.r*255.0+upper_curve.g*(255.0/256.0)-128.0;
        float bottom = lower_curve.r*255.0+lower_curve.g*(255.0/256.0)-128.0;
        vec4 closed_curve = texture(eye_curves,vec2(curve_x,(float(i)*3.0+2.5)/6.0));
        float meet = closed_curve.r*255.0+closed_curve.g*(255.0/256.0)-128.0;
        // Source-lid outlines include the small crease above the lash where it
        // crosses the bangs. Its exact extent is still limited by eye_region.
        float upper_margin = eye_bounds[i].w > 0.5 ? 32.0 : 8.0;
        if (y < top-eye_bounds[i].z-upper_margin || y > bottom+10.0) { continue; }
        float new_top = mix(top,meet,blink_upper);
        float new_bottom = mix(bottom,meet,blink_lower);
        float inside = smoothstep(new_top-0.6,new_top+0.6,y) * (1.0-smoothstep(new_bottom-0.6,new_bottom+0.6,y));
        inside *= step(0.0,u)*step(u,1.0);
        inside *= 1.0-smoothstep(0.0,0.8,new_top-new_bottom+0.8);
        vec4 result = texture(eye_skin,uv);
        vec4 fixed_eye = texture(eye_open,uv);
        if (eye_bounds[i].w > 0.5) {
            // Original lash ink travels on its own layer. Remove the old ink
            // from the fixed-eye sample to prevent a second stationary rim.
            float source_ink = max(texture(upper_lid,uv).a,texture(lower_lid,uv).a);
            fixed_eye = mix(fixed_eye,result,step(0.0001,source_ink));
        }
        result = mix(result,fixed_eye,inside);
        // Eyeball samples stay fixed. Only the eyelid/lash strips are remapped.
        vec2 upper_uv = uv-normal*(new_top-top)/canvas_size;
        vec2 lower_uv = uv-normal*(new_bottom-bottom)/canvas_size;
        vec4 lower_ink = texture(lower_lid,lower_uv);
        if (eye_bounds[i].w > 0.5) {
            lower_ink.a *= 1.0-smoothstep(0.65,0.98,min(blink_upper,blink_lower));
        }
        result = over(result,lower_ink);
        vec4 upper_ink = texture(upper_lid,upper_uv);
        if (eye_bounds[i].w > 0.5) {
            // Morph the lash contour into the clean, tapered band seen in the
            // closed CGC14_c drawing. This is a moving contour, not a closed CG.
            float taper = pow(max(sin(3.14159265*clamp(u,0.0,1.0)),0.0),0.65);
            float thickness = eye_bounds[i].z*0.95*taper;
            float aa = max(fwidth(y-new_top)*0.7,0.6);
            float band = smoothstep(new_top-thickness-aa,new_top-thickness+aa,y);
            band *= 1.0-smoothstep(new_top-aa,new_top+aa,y);
            band *= step(0.0,u)*step(u,1.0);
            vec3 ink_color = texture(eye_ink,vec2((float(i)+0.5)/2.0,0.5)).rgb;
            float contour_morph = smoothstep(0.25,0.95,blink_upper);
            upper_ink.rgb = mix(upper_ink.rgb,ink_color,contour_morph);
            upper_ink.a = mix(upper_ink.a,band,contour_morph);
        }
        result = over(result,upper_ink);
        // Restrict every eye operation, including moving lashes, to the outline.
        // Bangs in front retain their original pixels and occlude the eyelids.
        float influence = texture(eye_region,uv).r*(1.0-texture(eye_foreground,uv).r);
        if (eye_bounds[i].w > 0.5) {
            // Leave unswept skin untouched. A tiny lid displacement must not
            // replace the entire eye neighborhood with the repaired plate.
            float original_inside = smoothstep(top-0.6,top+0.6,y)*(1.0-smoothstep(bottom-0.6,bottom+0.6,y));
            original_inside *= step(0.0,u)*step(u,1.0);
            float ink_area = max(max(texture(upper_lid,uv).a,texture(lower_lid,uv).a),max(upper_ink.a,lower_ink.a));
            // Bring the smooth skin continuation in across the whole outline;
            // a hard swept-area cut would leave a visible patch inside it.
            float skin_continuation = smoothstep(0.0,0.25,max(blink_upper,blink_lower));
            influence *= max(max(abs(inside-original_inside),ink_area),skin_continuation);
            // Reconstruct the source antialias fringe for subpixel movement.
            // This correction falls away over 1.5 px of actual lid travel.
            vec4 source_pose = mix(texture(eye_skin,uv),fixed_eye,original_inside);
            source_pose = over(source_pose,texture(lower_lid,uv));
            source_pose = over(source_pose,texture(upper_lid,uv));
            float travel = max(abs(new_top-top),abs(new_bottom-bottom));
            result.rgb += (texture(eye_open,uv).rgb-source_pose.rgb)*(1.0-smoothstep(0.0,1.5,travel));
        }
        return mix(original,result,influence);
    }
    return original;
}

void fragment() {
    vec2 p = UV * canvas_size;
    vec3 w0 = texture(weights0, UV).rgb;
    vec3 w1 = texture(weights1, UV).rgb;
    vec3 w2 = texture(weights2, UV).rgb;
    vec3 w3 = texture(weights3, UV).rgb;
    vec2 displacement = vec2(0.0);
    for (int i = 0; i < 12; i++) {
        float weight = i < 3 ? w0[i] : (i < 6 ? w1[i - 3] : (i < 9 ? w2[i - 6] : w3[i - 9]));
        vec2 relative = p - pivots[i];
        float a = motions[i].z;
        vec2 rotated = vec2(cos(a) * relative.x - sin(a) * relative.y,
                            sin(a) * relative.x + cos(a) * relative.y);
        displacement += weight * (motions[i].xy + rotated - relative);
    }
    // Small inverse-mapped displacements preserve continuous skin at part boundaries.
    vec2 sample_uv = clamp(UV - displacement / canvas_size, vec2(0.0), vec2(1.0));
    vec4 base = texture(TEXTURE, sample_uv);
    COLOR = eyelids(base, sample_uv);
}
