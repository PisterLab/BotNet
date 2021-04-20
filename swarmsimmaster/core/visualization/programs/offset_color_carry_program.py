import OpenGL.GL as GL
import ctypes
import numpy as np
from core.visualization.programs.offset_color_program import OffsetColorProgram
from core.visualization.utils import VisualizationError, Level


class OffsetColorCarryProgram(OffsetColorProgram):
    """
    extended version of OffsetColorProgram.
    Has a carry flag and changes the position and alpha when flag is 1.0
    """

    vertex_shader_file = "core/visualization/shader/offset_color_carry_vertex.glsl"
    fragment_shader_file = "core/visualization/shader/frag.glsl"

    def _init_buffers(self, v, n, _):
        """
        extends the init_buffer of OffsetColorProgram class by creating the additional carry flag VBO
        :param v: the vertex model data (position vectors)
        :param n: the normal vector model data
        :return:
        """
        super()._init_buffers(v, n, _)

        self.vbos.append(GL.glGenBuffers(1))
        # init VBO 3 - dynamic previous position data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[3])
        loc = self.get_attribute_location("prev_pos")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
        GL.glVertexAttribDivisor(loc, 1)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, np.array([], dtype=np.float32), GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        self.vbos.append(GL.glGenBuffers(1))
        # init VBO 4 - dynamic carried flag data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[4])
        loc = self.get_attribute_location("carried")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 1, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
        GL.glVertexAttribDivisor(loc, 1)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, np.array([], dtype=np.float32), GL.GL_DYNAMIC_DRAW)

    def _init_uniforms(self):
        super(OffsetColorCarryProgram, self)._init_uniforms()
        self.set_animation(False)

    def update_carried(self, data):
        """
        updates the carry flag data (VBO3)
        :param data: list/array of floats (1.0 = True, 0.0 = False).
        """
        self.use()
        gpu_data = np.array(data, dtype=np.float32).flatten()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[4])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, gpu_data.nbytes, gpu_data, GL.GL_DYNAMIC_DRAW)

    def update_previous_positions(self, data):
        """
        updates the previous positions data (VBO 3)
        :param data: array of 3d positions
        """
        self.use()
        gpu_data = np.array(data, dtype=np.float32).flatten()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[3])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, gpu_data.nbytes, gpu_data, GL.GL_DYNAMIC_DRAW)
        if len(gpu_data) % 3.0 != 0.0:
            raise VisualizationError("Invalid previous positions data! Amount of coordinate "
                                     "components not dividable by 3 (not in xyz format?)!", Level.WARNING)

    def set_animation(self, animation: bool):
        """
        sets the animation flag
        :param animation: bool, if true the animation will be running
        """
        self.use()
        loc = self.get_uniform_location("animation")
        GL.glUniform1i(loc, animation)

    def get_animation(self):
        """
        reads the animation flag from the vertex shader
        :return: bool
        """
        self.use()
        return self.get_uniform("animation", 1)

    def set_animation_percentage(self, animation_percentage: float):
        """
        sets the animation flag
        :param animation_percentage: bool, if true the animation will be running
        """
        self.use()
        loc = self.get_uniform_location("animation_percentage")
        GL.glUniform1f(loc, animation_percentage)

    def get_animation_percentage(self):
        """
        reads the animation_percentage value from the vertex shader
        :return: float
        """
        self.use()
        return self.get_uniform("animation_percentage", 1)
