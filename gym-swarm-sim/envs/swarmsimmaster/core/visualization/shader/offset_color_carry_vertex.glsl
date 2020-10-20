#version 330

// VBO 0 - per vertex
// vector of a face
in vec3 position;
// normal vector of the vector/face
in vec3 normal;

// VBO 1 - per instance - position offset of the model
in vec3 offset;
// VBO 2 - per instance - color of the model
in vec4 color;
// VBO 3 - per instance - previous position, needed for animation
in vec3 prev_pos;
// VBO 4 - per instance - is carried
in float carried;

// uniforms
// projection matrix
uniform mat4 projection;
// view matrix
uniform mat4 view;
// world matrix
uniform mat4 world;
// scaling of the position
uniform vec3 world_scaling;
// scaling of the size
uniform vec3 model_scaling;
// min value of brightness
uniform float ambient_light;
// direction of the parallel lightsource
uniform vec3 light_direction;
// color of the parallel lightsource
uniform vec4 light_color;
// percentage of animation position between prev_pos and offset
uniform float animation_percentage;
// flag for using animation
uniform bool animation;

// varying color for fragment shader
out vec4 v_color;


void main(void)
{
    vec3 nn = normalize(normal);
    vec3 diffuseReflection = vec3(light_color) * vec3(color)
                             * max(max(ambient_light, dot(nn, light_direction)), dot(-nn, light_direction));

    mat4 use_world = world;
    vec3 real_offset;
    if(animation){
        real_offset = prev_pos+((offset-prev_pos)*animation_percentage);
    }else{
        real_offset = offset;
    }
    use_world[3] += vec4(real_offset * world_scaling, 0);
    float alpha = color[3];
    //taken
    if(carried > 0.8){
        use_world[0][0] = 0.5;
        use_world[1][1] = 0.5;
        use_world[2][2] = 0.5;
        use_world[3][0] += 0.2;
        use_world[3][1] += 0.2;
        use_world[3][2] += 0.2;
        alpha = 0.8;
    }else if(carried > 0.5){ // just taken
        use_world[0][0] = 1.0-0.5*animation_percentage;
        use_world[1][1] = 1.0-0.5*animation_percentage;
        use_world[2][2] = 1.0-0.5*animation_percentage;
        use_world[3][0] += 1.0-0.8*animation_percentage;
        use_world[3][1] += 1.0-0.8*animation_percentage;
        use_world[3][2] += 1.0-0.8*animation_percentage;
        alpha = 1.0-0.2*animation_percentage;
    }else if(carried > 0.2){ // just placed
        use_world[0][0] = 0.5+0.5*animation_percentage;
        use_world[1][1] = 0.5+0.5*animation_percentage;
        use_world[2][2] = 0.5+0.5*animation_percentage;
        use_world[3][0] += 0.2+0.8*animation_percentage;
        use_world[3][1] += 0.2+-0.8*animation_percentage;
        use_world[3][2] += 0.2+-0.8*animation_percentage;
        alpha = 0.8+0.2*animation_percentage;
    }

    v_color = vec4(diffuseReflection, alpha);

    gl_Position = projection  * view * use_world * vec4(position * model_scaling, 1.0);
}

