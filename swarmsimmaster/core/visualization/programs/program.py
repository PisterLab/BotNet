import OpenGL.GL as GL
from abc import ABC, abstractmethod
import numpy as np

from core.visualization.utils import load_obj_file, VisualizationError, Level


class Program(ABC):

    def __init__(self, vertex_file, fragment_file, model_file):
        """
        Superclass for Opengl Programs.
        compiles the given shader source files, gives access to the shared uniform variables of the shaders,
        loads the model mesh and calls the abstract init_buffer function with the loaded data
        :param vertex_file: file path to the vertex shader
        :param fragment_file: file path to the fragment shader
        :param model_file: file path to the .obj file
        """
        # creating GL Program
        self._program = GL.glCreateProgram()
        # loading shader source files
        self._vertex = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        self._fragment = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        self.amount = 0

        try:
            vert_source = open(vertex_file).read()
        except IOError as e:
            raise VisualizationError("Vertex shader file couldn't be loaded:\n%s" % str(e), Level.CRITICAL)

        try:
            frag_source = open(fragment_file).read()
        except IOError as e:
            raise VisualizationError("Fragment shader file couldn't be loaded:\n%s" % str(e), Level.CRITICAL)

        self.vbos = []
        self._init_shaders(vert_source, frag_source)

        GL.glUseProgram(self._program)

        self.light_angle = 0
        v, n, t = load_obj_file("components/models/" + model_file)
        self.size = len(v)

        self._vao = GL.glGenVertexArrays(1)
        self.use()
        self._init_buffers(v, n, t)
        GL.glBindVertexArray(0)

        self._init_uniforms()

    def _init_uniforms(self):
        """
        initializes the shader uniform variables
        :return:
        """
        eye = np.eye(4, 4)
        self.set_projection_matrix(eye)
        self.set_view_matrix(eye)
        self.set_world_matrix(eye)
        self.set_world_scaling((1.0, 1.0, 1.0))
        self.rotate_light(0.0)
        self.set_model_scaling((1.0, 1.0, 1.0))
        self.set_ambient_light(0.2)
        self.set_light_color((1.0, 1.0, 1.0, 1.0))

    @abstractmethod
    def _init_buffers(self, verts, norms, uvs):
        """
        creates the vbos and uploads the model data
        :param verts: the model positional vectors
        :param norms: the model face normals
        :param uvs: the model texture coordinates
        :return:
        """
        pass

    def _init_shaders(self, vert, frag):
        """
        compiles and links shaders
        :param vert: vertex shader source string
        :param frag: fragment shader source string
        :return:
        """
        # set the sources
        GL.glShaderSource(self._vertex, vert)
        GL.glShaderSource(self._fragment, frag)
        # compile vertex shader
        GL.glCompileShader(self._vertex)
        if not GL.glGetShaderiv(self._vertex, GL.GL_COMPILE_STATUS):
            e = GL.glGetShaderInfoLog(self._vertex).decode()
            raise VisualizationError("Vertex shader couldn't be compiled:\n%s" % str(e), Level.CRITICAL)

        # compile fragment shader
        GL.glCompileShader(self._fragment)
        if not GL.glGetShaderiv(self._fragment, GL.GL_COMPILE_STATUS):
            e = GL.glGetShaderInfoLog(self._fragment).decode()
            raise VisualizationError("Fragment shader couldn't be compiled:\n%s" % str(e), Level.CRITICAL)

        # attach the shaders to the matter program
        GL.glAttachShader(self._program, self._vertex)
        GL.glAttachShader(self._program, self._fragment)

        # link the shaders to the matter program
        GL.glLinkProgram(self._program)
        if not GL.glGetProgramiv(self._program, GL.GL_LINK_STATUS):
            e = GL.glGetProgramInfoLog(self._program)
            raise VisualizationError("The shaders couldn't be linked to program:\n%s" % str(e), Level.CRITICAL)

        # detach the shaders from matter program
        GL.glDetachShader(self._program, self._vertex)
        GL.glDetachShader(self._program, self._fragment)

    def get_uniform_location(self, name: str):
        """
        gets and checks the uniform location with given name
        :param name: variable name (string)
        :return: location (int)
        """
        self.use()
        loc = GL.glGetUniformLocation(self._program, name)
        if loc < 0:
            raise VisualizationError("Uniform \"%s\" doesn't exist!\n"
                                     "(Maybe the compilation optimized the shader by removing the unused uniform?)" %
                                     name, Level.WARNING)
        else:
            return loc

    def get_attribute_location(self, name: str):
        """
        gets and checks the attribute location with given name
        :param name: variable name (string)
        :return: location (int)
        """
        loc = GL.glGetAttribLocation(self._program, name)
        if loc < 0:
            raise VisualizationError("Attribute \"%s\" doesn't exist!\n"
                                     "(Maybe the compilation optimized the shader by removing the unused attribute?)" %
                                     name, Level.WARNING)
        else:
            return loc

    def get_uniform(self, name, length):
        output = np.zeros(length, dtype=np.float32)
        loc = self.get_uniform_location(name)
        GL.glGetUniformfv(self._program, loc, output)
        return output

    def use(self):
        """
        sets the gl program to this one.
        :return:
        """
        GL.glBindVertexArray(self._vao)
        GL.glUseProgram(self._program)

    def set_projection_matrix(self, projection_matrix):
        """
        sets the projection matrix in the vertex shader program
        :param projection_matrix: 4x4 float32 projection matrix
        :return:
        """
        self.use()
        gpu_data = np.array(projection_matrix, dtype=np.float32).flatten()
        if len(gpu_data) != 16:
            raise VisualizationError(
                "Length of set_projection_matrix parameter not correct, expected 16 got %d " % len(gpu_data),
                Level.CRITICAL)
        else:
            loc = self.get_uniform_location("projection")
            GL.glUniformMatrix4fv(loc, 1, False, projection_matrix)

    def get_projection_matrix(self):
        """
        reads the projection matrix from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("projection", 16)

    def set_view_matrix(self, view_matrix):
        """
        sets the view matrix in the vertex shader
        :param view_matrix: 4x4 float32 view matrix
        :return:
        """
        self.use()
        gpu_data = np.array(view_matrix, dtype=np.float32).flatten()
        if len(gpu_data) != 16:
            raise VisualizationError(
                "Length of set_view_matrix parameter not correct, expected 16 got %d " % len(gpu_data),
                Level.WARNING)
        else:
            loc = self.get_uniform_location("view")
            GL.glUniformMatrix4fv(loc, 1, False, view_matrix)

    def get_view_matrix(self):
        """
        reads the view matrix from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("view", 16)

    def set_world_matrix(self, world_matrix):
        """
        sets the world matrix in the vertex shader
        :param world_matrix: 4x4 float32
        :return:
        """
        self.use()
        gpu_data = np.array(world_matrix, dtype=np.float32).flatten()
        if len(gpu_data) != 16:
            raise VisualizationError(
                "Length of set_world_matrix parameter not correct, expected 16 got %d " % len(gpu_data),
                Level.WARNING)
        else:
            loc = self.get_uniform_location("world")
            GL.glUniformMatrix4fv(loc, 1, False, world_matrix)

    def get_world_matrix(self):
        """
        reads the world matrix from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("world", 16)

    def set_world_scaling(self, scaling):
        """
        sets the world scaling uniform in the vertex shader
        :param scaling:
        :return:
        """
        self.use()
        gpu_data = np.array(scaling, dtype=np.float32).flatten()
        if len(gpu_data) != 3:
            raise VisualizationError(
                "Length of set_world_scaling parameter not correct, expected 3 got %d " % len(gpu_data),
                Level.WARNING)
        else:
            loc = self.get_uniform_location("world_scaling")
            GL.glUniform3f(loc, *gpu_data)

    def get_world_scaling(self):
        """
        reads the world scaling vector from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("world_scaling", 3)

    def rotate_light(self, angle: float):
        """
        rotates the parallel light source around the y axis
        :param angle: angle in degree
        :return:
        """
        self.use()
        self.light_angle += angle
        loc = self.get_uniform_location("light_direction")
        GL.glUniform3f(loc, np.sin(np.radians(self.light_angle)), 0.4, np.cos(np.radians(self.light_angle)))

    def get_light_direction(self):
        """
        reads the light direction vector from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("light_direction", 3)

    def set_model_scaling(self, scaling):
        """
        sets the size scaling of the model
        :param scaling: 3d float tuple/array
        :return:
        """
        self.use()
        gpu_data = np.array(scaling, dtype=np.float32).flatten()
        if len(gpu_data) != 3:
            raise VisualizationError(
                "Length of set_model_scaling parameter not correct, expected 3 got %d " % len(gpu_data),
                Level.WARNING)
        else:
            loc = self.get_uniform_location("model_scaling")
            GL.glUniform3f(loc, *gpu_data)

    def update_offsets(self, data):
        """
        updates the offsets/positions data (VBO 1)
        :param data: array of 3d positions
        :return:
        """
        self.use()
        gpu_data = np.array(data, dtype=np.float32).flatten()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[1])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, gpu_data.nbytes, gpu_data, GL.GL_DYNAMIC_DRAW)
        self.amount = len(gpu_data) / 3.0
        if len(gpu_data) % 3.0 != 0.0:
            raise VisualizationError(
                "Invalid offset data! Amount of coordinate components not dividable by 3 (not in xyz format?)!",
                Level.WARNING)
        self.amount = int(self.amount)

    def get_model_scaling(self):
        """
        reads the model scaling vector from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("model_scaling", 3)

    def set_ambient_light(self, ambient_light: float):
        """
        sets the ambient light strength
        :param ambient_light: float, minimal brightness / brightness in full shadow
        :return:
        """
        self.use()
        loc = self.get_uniform_location("ambient_light")
        GL.glUniform1f(loc, ambient_light)

    def get_ambient_light(self):
        """
        reads the ambient light value from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("ambient_light", 1)

    def set_light_color(self, light_color):
        """
        sets the color of the light
        :param light_color: tuple/array, rgba format
        :return:
        """
        self.use()
        gpu_data = np.array(light_color, dtype=np.float32).flatten()
        if len(gpu_data) != 4:
            raise VisualizationError(
                "Length of set_light_color parameter not correct, expected 4 got %d " % len(gpu_data),
                Level.WARNING)
        else:
            loc = self.get_uniform_location("light_color")
            GL.glUniform4f(loc, *light_color)

    def get_light_color(self):
        """
        reads the light color from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("light_color", 4)
