shader_type canvas_item;
render_mode unshaded;

uniform float silhouette:hint_range(0.0,1.0)=0.0;
uniform vec4 silhouette_colour:source_color=vec4(0.0,.72,.8,1.0);

void fragment(){
    vec4 original=texture(TEXTURE,UV);
    COLOR=vec4(mix(original.rgb,silhouette_colour.rgb,silhouette),original.a);
}
