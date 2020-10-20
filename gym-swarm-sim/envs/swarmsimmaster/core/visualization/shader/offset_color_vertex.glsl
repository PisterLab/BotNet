#version 330

// VBO 0 - per vertex
// vector of a face
in vec3 position;
// normal vector of the vector/face
in vec3 normal;

// VBO 1 - per instance
// position offset of the model
in vec3 offset;
// color of the model
in vec4 color;

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

// varying color for fragment shader
out vec4 v_color;


void main(void)
{
    vec3 nn = normalize(normal);
    vec3 diffuseReflection = vec3(light_color) * vec3(color)
                             * max(max(ambient_light, dot(nn, light_direction)), dot(-nn, light_direction));
    v_color = vec4(diffuseReflection, color[3]);

    mat4 use_world = world;
    use_world[3] += vec4(offset * world_scaling, 0);
    gl_Position = projection  * view * use_world * vec4(position * model_scaling, 1.0);
}