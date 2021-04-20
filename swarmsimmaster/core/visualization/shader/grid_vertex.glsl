#version 330
// position vector of location model or direction line VBO 0
in vec3 position;
// normal vector of location model face VBO 0
in vec3 normal;
// offsets of the model (location & lines) VBO 1
in vec3 offset;

//projection matrix
uniform mat4 projection;
// view matrix
uniform mat4 view;
// world matrix
uniform mat4 world;
// color of the grid lines
uniform vec4 line_color;
// color of the border
uniform vec4 border_color;
// color of the locaiton model
uniform vec4 model_color;
// scaling of the world
uniform vec3 world_scaling;
// scaling of the model size
uniform vec3 model_scaling;
// scaling of the line length
uniform vec3 line_scaling;
// min value of brightness
uniform float ambient_light;
// direction of the parallel lightsource
uniform vec3 light_direction;
// color of the parallel lightsource
uniform vec4 light_color;
// flag for distinction of drawing the grid's connections (0), the location model (1) or the border (2)
uniform int drawing_part;

// varying color for fragment shader
out vec4 v_color;
void main(void)
{
   if(drawing_part == 0){
      v_color = line_color;
      gl_Position = projection * view * world * vec4((position * line_scaling + offset) * world_scaling, 1.0);
   }else if(drawing_part == 1){
      vec3 nn = normalize(normal);
      vec3 diffuseReflection = vec3(light_color) * vec3(model_color)
                             * max(max(ambient_light, dot(nn, light_direction)), dot(-nn, light_direction));
      v_color = vec4(diffuseReflection, model_color[3]);

      mat4 use_world = world;
      use_world[3] += vec4(offset * world_scaling, 0);
      gl_Position = projection  * view * use_world * vec4(position * model_scaling, 1.0);
   }else if(drawing_part == 2){
      v_color = border_color;
      gl_Position = projection * view * world * vec4(position * world_scaling, 1.0);
   }
}
