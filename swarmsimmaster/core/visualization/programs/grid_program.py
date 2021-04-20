from core.visualization.programs.program import Program
import OpenGL.GL as GL
import numpy as np
import ctypes

from core.visualization.utils import VisualizationError, Level


class GridProgram(Program):
    """
    OpenGL Program for the visualization of the grid and the included coordinates
    """
    vertex_shader_file = "core/visualization/shader/grid_vertex.glsl"
    fragment_shader_file = "core/visualization/shader/frag.glsl"

    def __init__(self, grid, line_color, model_color, coordinate_model_file, border_size):
        """
        initializes/loads/creates all necessary data/buffers/shaders for drawing the Grid
        :param grid: the grid item to be visualized
        :param line_color: color of the grid lines
        :param model_color: color of the grid coordinate model
        :param coordinate_model_file: model file of the coordinates
        """
        self.grid = grid
        self.width = 1
        self.line_offset = 0
        self.line_length = 0
        self.border_offset = 0
        self.border_length = 0
        self.amount = 0
        self.show_coordinates = True
        self.show_lines = True
        self.show_border = False
        self.vbos = list()
        self.border_size = border_size
        super().__init__(self.vertex_shader_file, self.fragment_shader_file, coordinate_model_file)
        self.set_line_color(line_color)
        self.set_model_color(model_color)

    def _init_buffers(self, verts, normals, _):

        # get lines data
        lines = self.grid.get_lines()

        self.line_offset = len(verts)
        self.line_length = len(lines)

        border = self._calculate_border()
        self.border_offset = self.line_offset + self.line_length
        self.border_length = len(border)
        # prepare data for the gpu
        gpu_data = np.array(verts + lines + border + normals, dtype=np.float32)

        # create VBO
        self.vbos = list(GL.glGenBuffers(2))
        # init VBO
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbos[0])
        loc = self.get_attribute_location("position")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))

        loc = self.get_attribute_location("normal")
        GL.glEnableVertexAttribArray(loc)
        GL.glVertexAttribPointer(loc, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p((len(verts) + len(lines) + len(border)) * 12))
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

    def _calculate_border(self):
        lines = []

        if self.grid.get_dimension_count() == 3:
            lines = [(-self.border_size[0], -self.border_size[1], -self.border_size[2]),
                     (-self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (-self.border_size[0], -self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (self.border_size[0], self.border_size[1], self.border_size[2]),
                     (self.border_size[0], self.border_size[1], self.border_size[2]),
                     (self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], -self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], self.border_size[2]),
                     (self.border_size[0], self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], self.border_size[2]),
                     (-self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], self.border_size[1], -self.border_size[2]),
                     (-self.border_size[0], -self.border_size[1], -self.border_size[2]),
                     (self.border_size[0], -self.border_size[1], -self.border_size[2])]
        if self.grid.get_dimension_count() <= 2:
            lines = [(-self.border_size[0], -self.border_size[1], 0),
                     (-self.border_size[0], self.border_size[1], 0),
                     (-self.border_size[0], self.border_size[1], 0),
                     (self.border_size[0], self.border_size[1], 0),
                     (self.border_size[0], self.border_size[1], 0),
                     (self.border_size[0], -self.border_size[1], 0),
                     (self.border_size[0], -self.border_size[1], 0),
                     (-self.border_size[0], -self.border_size[1], 0)]
        return lines

    def _init_uniforms(self):
        """
        initializes the shader uniforms
        :return:
        """
        super()._init_uniforms()
        self.set_line_color((0.0, 0.0, 0.0, 1.0))
        self.set_border_color((1.0, 0.0, 0.0, 1.0))
        self.set_model_color((0.0, 0.0, 0.0, 0.0))
        self.set_line_scaling((1.0, 1.0, 1.0))

    def draw(self):
        """
        draws the grid lines
        :return:
        """
        self.use()
        if self.show_border:
            self._draw_part(2)
            GL.glDrawArrays(GL.GL_LINES, self.border_offset, self.border_length)
        if self.show_lines:
            self._draw_part(0)
            GL.glDrawArraysInstanced(GL.GL_LINES, self.line_offset, self.line_length, self.amount)
        if self.show_coordinates:
            self._draw_part(1)
            GL.glDrawArraysInstanced(GL.GL_TRIANGLES, 0, self.size, self.amount)

    def set_width(self, width):
        """
        sets the width of the grid lines (updates the glLineWidth globally!!!)
        :param width: the width (int)
        :return:
        """
        self.width = width
        GL.glLineWidth(self.width)

    def set_line_color(self, color):
        """
        sets the line_color uniform in the grid vertex shader
        :param color: the color (rgba)
        :return:
        """
        self.use()

        gpu_data = np.array(color, dtype=np.float32).flatten()
        if len(gpu_data) != 4:
            raise VisualizationError(
                "Length of set_line_color parameter not correct, expected 4 got %d " % len(gpu_data),
                Level.WARNING)
        loc = self.get_uniform_location("line_color")
        GL.glUniform4f(loc, *gpu_data)

    def get_line_color(self):
        """
        reads the line color from the vertex shader
        :return:
        """
        return self.get_uniform("line_color", 4)

    def set_border_color(self, color):
        """
        sets the border_color uniform in the grid vertex shader
        :param color: the color (rgba)
        :return:
        """
        self.use()

        gpu_data = np.array(color, dtype=np.float32).flatten()
        if len(gpu_data) != 4:
            raise VisualizationError(
                "Length of set_border_color parameter not correct, expected 4 got %d " % len(gpu_data),
                Level.WARNING)
        loc = self.get_uniform_location("border_color")
        GL.glUniform4f(loc, *gpu_data)

    def get_border_color(self):
        """
        reads the border color from the vertex shader
        :return:
        """
        return self.get_uniform("border_color", 4)

    def set_model_color(self, color):
        """
        sets the model_color uniform in the grid vertex shader
        :param color: the color (rgba)
        :return:
        """
        self.use()
        gpu_data = np.array(color, dtype=np.float32).flatten()
        if len(gpu_data) != 4:
            raise VisualizationError(
                "Length of set_model_color parameter not correct, expected 4 got %d " % len(gpu_data),
                Level.WARNING)
        loc = self.get_uniform_location("model_color")
        GL.glUniform4f(loc, *gpu_data)

    def get_model_color(self):
        """
        reads the model color from the vertex shader
        :return:
        """
        self.use()
        return self.get_uniform("model_color", 4)

    def _draw_part(self, part: int):
        loc = self.get_uniform_location("drawing_part")
        GL.glUniform1i(loc, part)

    def set_line_scaling(self, scaling):
        """
        sets the line_scaling uniform in the vertex shader
        :param scaling: the scaling vector
        :return:
        """
        self.use()
        gpu_data = np.array(scaling, dtype=np.float32).flatten()
        if len(gpu_data) != 3:
            raise VisualizationError(
                "Length of set_line_scaling parameter not correct, expected 3 got %d " % len(gpu_data),
                Level.WARNING)
        loc = self.get_uniform_location("line_scaling")
        GL.glUniform3f(loc, *gpu_data)

    def get_line_scaling(self):
        """
        reads the line scaling vector from the vertex shader
        :return:
        """
        return self.get_uniform("line_scaling", 3)
