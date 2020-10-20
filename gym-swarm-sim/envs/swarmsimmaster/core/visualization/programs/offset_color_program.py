import OpenGL.GL as GL

from core.visualization.programs.program import Program
import numpy as np
import ctypes

from core.visualization.utils import VisualizationError, Level


class OffsetColorProgram(Program):
    """
    OpenGL Program for Models which are loaded from a model file (Wavefront / .obj format) and are drawn multiple times
    at different positions with different colors
    """

    vertex_shader_file = "core/visualization/shader/offset_color_vertex.glsl"
    fragment_shader_file = "core/visualization/shader/frag.glsl"

    def __init__(self, model_file: str):
        self.vbos = list()
        self.amount = 0
        super().__init__(self.vertex_shader_file, self.fragment_shader_file, model_file)

    def _init_buffers(self, vertices, normals, _):
        # prepare data for the gpu
        gpu_data = np.array(vertices + normals, dtype=np.float32)

        # create VBOs
        self.vbos = list(GL.glGenBuffers(3))

        # init VBO 0 - static mesh data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[0])
        loc = self.get_attribute_location("position")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
        loc = self.get_attribute_location("normal")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(self.size * 12))
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 12 * len(gpu_data), gpu_data, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # init VBO 1 - dynamic offset data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[1])
        loc = self.get_attribute_location("offset")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
        GL.glVertexAttribDivisor(loc, 1)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, np.array([], dtype=np.float32), GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # init VBO 2 - dynamic color data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[2])
        loc = self.get_attribute_location("color")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
        GL.glVertexAttribDivisor(loc, 1)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, np.array([], dtype=np.float32), GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def draw(self):
        """
        sets the vao and draws the scene
        :return:
        """
        self.use()
        GL.glBindVertexArray(self._vao)
        GL.glDrawArraysInstanced(GL.GL_TRIANGLES, 0, self.size, self.amount)

    def update_colors(self, data):
        """
        updates the color data (VBO2)
        :param data: list/array of rgba values. (dimensions are irrelevant)
        :return:
        """
        self.use()
        gpu_data = np.array(data, dtype=np.float32).flatten()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[2])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, gpu_data.nbytes, gpu_data, GL.GL_DYNAMIC_DRAW)
        if len(gpu_data) % 4.0 != 0.0:
            raise VisualizationError(
                "Invalid color data! Amount of color components not dividable by 4 (not in rgba format?)!",
                Level.WARNING)
