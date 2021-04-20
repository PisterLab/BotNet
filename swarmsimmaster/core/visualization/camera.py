import numpy as np

from core.visualization.utils import (get_perspetive_projection_matrix, get_orthographic_projection_matrix,
                                      get_look_at_matrix, get_translation_matrix, VisualizationError,
                                      Level)


class Camera:
    def __init__(self, width, height, look_at, phi, theta, radius, fov,
                 cursor_offset, render_distance, projection_type, scaling):
        """
        The Camera Class manages the 3 matrices which are necessery for the 3D visualization
        and the position of the cursor.

        :param width: width of the viewport (screen, in pixel)
        :param height: height of the viewport (screen, in pixel)
        :param look_at: the initial position to look at
        :param phi: the initial rotation around the y axis
        :param theta: the initial rotation around the x-z plane
        :param radius: distance from the look_at position (positive)
        :param fov: field of view (only for perspective projection)
        :param cursor_offset: offset of the cursor_plane to the camera (negative)
        :param render_distance: the distance in which things are still rendered
        :param projection_type: either "perspective" or "ortho"
        :param scaling: scaling of the world, just for the cursor.
        """
        self._orig_look_at = np.array(look_at, dtype=np.float32)
        self._orig_phi = phi
        self._orig_theta = theta
        self._orig_radius = radius
        self._orig_fov = fov
        self._orig_cursor_offset = cursor_offset
        self._orig_render_distance = render_distance
        self._orig_projection_type = projection_type

        self._width = width
        self._height = height
        self._aspect = width / height

        self._look_at = None
        self._phi = None
        self._theta = None
        self._radius = None
        self._projection_type = None
        self._render_distance = None
        self._cursor_radius = None

        self._position = None
        self.view_matrix = None
        self.projection_matrix = None
        self.world_matrix = None
        self._right = None
        self._up = np.array([0, 1, 0], dtype=np.float32)
        self._forward = None
        self._fov = None
        self.cursor_position = None
        self._cursor_plane_size = [0, 0]
        self._mouse_position = [0, 0]
        self._scaling = scaling

        self.reset()

    def reset(self):
        self._look_at = np.array(self._orig_look_at, dtype=np.float32)
        self._phi = self._orig_phi
        self._theta = self._orig_theta
        self._radius = self._orig_radius
        self._fov = self._orig_fov
        self._cursor_radius = np.array(self._orig_cursor_offset, dtype=np.float32)
        self._render_distance = self._orig_render_distance
        self._projection_type = self._orig_projection_type
        self._update_position()
        self._update_projection()

    def _update_position(self):
        pos_y = np.sin(np.radians(self._theta)) * self._radius
        r_xz = np.cos(np.radians(self._theta)) * self._radius
        pos_x = np.cos(np.radians(self._phi)) * r_xz
        pos_z = np.sin(np.radians(self._phi)) * r_xz
        self._position = self._look_at + np.array([pos_x, pos_y, pos_z], dtype=np.float32)
        self._update_view()
        self._update_world()
        self._update_cursor()

    def _update_projection(self):
        if self._projection_type == "perspective":
            self.projection_matrix = get_perspetive_projection_matrix(self._fov, self._aspect, 1, self._render_distance)
        elif self._projection_type == "ortho":
            self.projection_matrix = get_orthographic_projection_matrix(-self._radius * self._aspect,
                                                                        self._radius * self._aspect,
                                                                        -self._radius, self._radius,
                                                                        0.001, self._render_distance)
        else:
            self._projection_type = "perspective"
            self.projection_matrix = get_perspetive_projection_matrix(self._fov, self._aspect, 1, self._render_distance)
            raise VisualizationError("Unknown projection type: \"" + self._projection_type +
                                     "\"! Setting projection to perspective.", Level.INFO)

    def _update_view(self):
        self.view_matrix = get_look_at_matrix(self._position, self._look_at, np.array([0, 1, 0], dtype=np.float32))
        self._right = np.array((self.view_matrix[0][0], self.view_matrix[1][0], self.view_matrix[2][0]))
        self._up = np.array((self.view_matrix[0][1], self.view_matrix[1][1], self.view_matrix[2][1]))
        self._forward = -1 * np.array((self.view_matrix[0][2], self.view_matrix[1][2], self.view_matrix[2][2]))

    def _update_world(self):
        self.world_matrix = get_translation_matrix(self._position)

    def _update_cursor(self):
        if self._projection_type == "perspective":
            height = 2.0 * np.tan(np.radians(self._fov / 2.0)) * self._cursor_radius
            width = 2.0 * np.tan(np.radians(self._fov / 2.0)) * self._cursor_radius * self._aspect
            self._cursor_plane_size[0] = width
            self._cursor_plane_size[1] = height
        else:
            height = - self._radius * 2
            width = - self._radius * 2 * self._aspect
            self._cursor_plane_size[0] = width
            self._cursor_plane_size[1] = height

        wx = - (self._mouse_position[0] - self._width / 2.0) / self._width * self._cursor_plane_size[0]
        wy = (self._mouse_position[1] - self._height / 2.0) / self._height * self._cursor_plane_size[1]

        tmp = np.dot(self.view_matrix,
                     np.array([[wx, wy, self._cursor_radius + self._radius, 1]]).transpose())

        self.cursor_position = ((tmp[0][0] - self._look_at[0]) / self._scaling[0],
                                (tmp[1][0] - self._look_at[1]) / self._scaling[1],
                                (tmp[2][0] - self._look_at[2]) / self._scaling[2])

    def rotate(self, delta_phi: float, delta_theta: float):
        self._phi += delta_phi
        self._theta += delta_theta
        if self._theta < -89.9:
            self._theta = -89.9
        if self._theta > 89.9:
            self._theta = 89.9
        self._update_position()

    def move(self, right: float, up: float, forward: float):
        self._look_at += self._right * right + self._up * up + self._forward * forward
        self._update_position()

    def set_viewport(self, width: float, height: float):
        self._width = width
        self._height = height
        self._aspect = width / height
        self._update_projection()

    def update_radius(self, delta_radius: float):
        self._radius += delta_radius
        if self._radius < 0.1:
            self._radius = 0.1
        self._update_position()
        self._update_projection()

    def update_cursor_radius(self, delta_cursor_radius: float):
        self._cursor_radius += delta_cursor_radius
        if self._cursor_radius > -2:
            self._cursor_radius = -2
        self._update_cursor()

    def set_cursor_radius(self, cursor_radius: float):
        self._cursor_radius = cursor_radius
        self._update_cursor()

    def update_mouse_position(self, mouse_position):
        self._mouse_position = mouse_position
        self._update_cursor()

    def set_scaling(self, scaling):
        self._scaling = scaling
        self._update_cursor()

    def get_radius(self):
        return self._radius

    def set_fov(self, fov):
        self._fov = fov
        self._update_projection()
        self._update_cursor()

    def get_fov(self):
        return self._fov

    def get_projection_type(self):
        return self._projection_type

    def set_projection_type(self, projection_type):
        self._projection_type = projection_type
        self._update_projection()

    def get_render_distance(self):
        return self._render_distance

    def set_render_distance(self, render_distance: float):
        self._render_distance = render_distance
        self._update_projection()

    def get_look_at(self):
        return self._look_at

    def get_position(self):
        return self._position
