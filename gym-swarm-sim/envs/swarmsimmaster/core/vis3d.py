import importlib
import os
from threading import Thread

import cv2
from PyQt5.QtWidgets import QApplication, QSplitter, QWidget

from core.matter import MatterType
from core.visualization.recorder import Recorder
from core.visualization.OGLWidget import OGLWidget
import time
from core.visualization.camera import Camera
from core.visualization.toms_svg_generator import create_svg
from core.visualization.utils import LoadingWindow, show_msg, TopQFileDialog, VisualizationError, Level


class ResetException(Exception):
    def __init__(self):
        super(ResetException, self).__init__()


def close(_):
    exit(0)


class Visualization:
    def __init__(self, world):
        """
        Main Interface between the OpenGL stuff and the simulator.
        Initializes the camera, and the opengl-widget.
        controlls the speed of the simulation.
        :param world: the world class
        """
        self._world = world
        self._last_light_rotation = 0
        self._rounds_per_second = 10
        self._reset_flag = False
        self._running = False
        self._app = None
        self._viewer = None
        self._gui = None
        self._splitter = None
        self._recording = False
        self._animation = world.config_data.animation
        self._auto_animation = world.config_data.auto_animation
        self._manual_animation_speed = world.config_data.manual_animation_speed
        self.light_rotation = False
        self.grid_size = world.grid.size

        # create the QApplication
        self._app = QApplication([])

        # create camera for the visualization
        # if grid is 2D, set to orthographic projection (it is better for 2D)
        if self._world.grid.get_dimension_count() == 2:
            self._camera = Camera(self._world.config_data.window_size_x, self._world.config_data.window_size_y,
                                  self._world.config_data.look_at, self._world.config_data.phi,
                                  self._world.config_data.theta, self._world.config_data.radius,
                                  self._world.config_data.fov, self._world.config_data.cursor_offset,
                                  self._world.config_data.render_distance, "ortho", self._world.grid.get_scaling())
        else:
            self._camera = Camera(self._world.config_data.window_size_x, self._world.config_data.window_size_y,
                                  self._world.config_data.look_at, self._world.config_data.phi,
                                  self._world.config_data.theta, self._world.config_data.radius,
                                  self._world.config_data.fov, self._world.config_data.cursor_offset,
                                  self._world.config_data.render_distance,
                                  "perspective", self._world.grid.get_scaling())

        # create the opengl widget
        self._viewer = OGLWidget(self._world, self._camera)
        self._viewer.glInit()
        self.recorder = Recorder(self._world, self._viewer)

        # create and show the main Window
        self._splitter = QSplitter()
        self._splitter.closeEvent = close
        self._splitter.setMinimumWidth(self._world.config_data.window_size_x)
        self._splitter.setMinimumHeight(self._world.config_data.window_size_y)
        self._splitter.setWindowTitle("Simulator")

        self._splitter.show()

        # create gui
        # creating the gui has to happen after showing the window, so the gui can access
        # opengl variables and programs during creation
        self._gui_module = importlib.import_module('components.gui.' + self._world.config_data.gui)

        # the key press handler
        def key_press_event(event):
            self._gui_module.key_handler(event.key(), self._world, self)

        # loading key handler from gui module
        if "key_handler" in dir(self._gui_module):
            self._viewer.keyPressEventHandler = key_press_event
            self._splitter.keyPressEvent = key_press_event
        else:
            show_msg("No key_handler(key, vis) function found in gui module!", Level.WARNING, self._splitter)

        # loading gui from gui module
        if "create_gui" in dir(self._gui_module):
            self._gui = self._gui_module.create_gui(self._world, self)
            if self._gui is not None and issubclass(self._gui.__class__, QWidget):
                self._splitter.addWidget(self._gui)
                self._splitter.keyPressEvent = self._viewer.keyPressEvent
                self._splitter.keyReleaseEvent = self._viewer.keyReleaseEvent
                self._splitter.addWidget(self._viewer)
                self._splitter.setSizes(
                    [self._world.config_data.window_size_x * 0.25, self._world.config_data.window_size_x * 0.75])
            else:
                # noinspection PyUnresolvedReferences
                show_msg("The create_gui(world, vis) function in gui module didn't return a QWidget." +
                         "Expected a QWidget or a subclass, but got %s."
                         % self._gui.__class__.__name__, Level.WARNING, self._splitter)
                self._splitter.addWidget(self._viewer)

        else:
            show_msg("No create_gui(world, vis) function found in gui module. GUI not created", Level.INFO,
                     self._splitter)
            self._splitter.addWidget(self._viewer)

        # waiting for the simulation window to be fully active
        while not self._splitter.windowHandle().isExposed():
            self._process_events()
        # first update and draw call.
        self._viewer.update_scene()

    def is_recording(self):
        return self._recording

    def _process_events(self):
        self._app.processEvents()
        if self._reset_flag:
            raise ResetException()

    def reset(self):
        """
        stops the simulation.
        deletes all data in the visualization.
        resets the camera
        :return:
        """
        self._reset_flag = False
        self._running = False
        self._viewer.agent_offset_data = {}
        self._viewer.agent_update_flag = True
        self._viewer.item_offset_data = {}
        self._viewer.item_update_flag = True
        self._viewer.location_offset_data = {}
        self._viewer.location_update_flag = True
        self._viewer.update_data()
        self._camera.reset()
        self._viewer.update_scene()

    def wait_for_thread(self, thread: Thread, window_message, window_title):
        """
        executes a thread and shows a loading window till the thread stops.
        blocks the gui, while thread runs.
        :param thread: the thread
        :param window_message: the displayed message
        :param window_title: the title of the loading window
        :return:
        """

        loading_window = LoadingWindow(window_message, window_title)
        if self._gui is not None and issubclass(self._gui.__class__, QWidget):
            self._gui.setDisabled(True)
        thread.start()
        while thread.is_alive():
            try:
                self._process_events()
            except VisualizationError as ve:
                show_msg(ve, Level.CRITICAL, self._splitter)
                exit(1)
        thread.join()
        loading_window.close()
        self._gui.setDisabled(False)

    def rotate_light(self):
        """
        rotates the light direction at a steady degrees/second velocity independent of the CPU-clock or framerate.
        :return:
        """
        # rotation of light only in 3d
        if self._world.grid.get_dimension_count() > 2:
            # 20° per second rotation
            if self._last_light_rotation == 0:
                self._last_light_rotation = time.perf_counter()
            else:
                angle = (time.perf_counter() - self._last_light_rotation) * 20
                self._last_light_rotation = time.perf_counter()
                self._viewer.rotate_light(angle)
                self._viewer.glDraw()

    def start_stop(self):
        """
        starts and pauses the simulation
        :return:
        """
        self._running = not self._running

    def _wait_while_not_running(self):
        """
        helper function.
        waits until the running flag is set.
        :return:
        """
        sleep_time = 1.0 / 120.0
        self._process_events()
        if self.light_rotation:
            self.rotate_light()
        while not self._running:
            # sleeping for 1/120 secs, for responsive GUI
            time.sleep(sleep_time)
            if self.light_rotation:
                self.rotate_light()
            self._process_events()

    def animate(self, round_start_time, speed):
        """
        loop for animating the movement of agents and carried items
        :param round_start_time: the start of the round
        :param speed: speed of the animation in 1/steps. less or equal zero = automatic mode
        """
        if speed < 0:
            # draw at location according to the passed time and the rps
            half_round_time = (1.0 / self._rounds_per_second) / 2.0
            now = time.perf_counter()
            while (now - round_start_time) < half_round_time:
                self._viewer.set_animation_percentage(min(1, (now - round_start_time) / half_round_time))
                self._process_events()
                self._viewer.glDraw()
                now = time.perf_counter()
        else:
            # draw at location according to the selected animation speed
            for i in range(1, max(1, speed)):
                self._viewer.set_animation_percentage(float(i / max(1, speed)))
                self._process_events()
                self._viewer.glDraw()

        self._viewer.set_animation_percentage(1)
        self._viewer.glDraw()

        # reset the previous position after animation.
        # not reseting it causes a visual bug if the matter didn't move.
        for agent in self._viewer.agent_offset_data:
            current_data = self._viewer.agent_offset_data[agent]
            self._viewer.agent_offset_data[agent] = (current_data[0], current_data[1], agent.coordinates,
                                                     current_data[3])
        for item in self._viewer.item_offset_data:
            current_data = self._viewer.item_offset_data[item]
            self._viewer.item_offset_data[item] = (current_data[0], current_data[1], item.coordinates,
                                                   current_data[3])
        self._viewer.agent_update_flag = True
        self._viewer.item_update_flag = True

    def run(self, round_start_timestamp):
        """
        main function for running the simulation with the visualization.
        At this time, its just error handling here.. the simulation and drawing stuff starts in the run_iteration method
        :param round_start_timestamp: timestamp of the start of the round.
        :return:
        """
        try:
            self._run_iteration(round_start_timestamp)
        except VisualizationError as ve:
            if ve.level == Level.INFO:
                show_msg(ve.msg, ve.level, self.get_main_window())
            if ve.level == Level.CRITICAL:
                show_msg(ve.msg, ve.level, self.get_main_window())
                exit(1)
            if ve.level == Level.WARNING:
                try:
                    self._run_iteration(round_start_timestamp)
                    show_msg(ve.msg, ve.level, self.get_main_window())
                except VisualizationError as ve:
                    show_msg(ve.msg, ve.level, self.get_main_window())
                    if ve.level != Level.INFO:
                        exit(1)

    def _run_iteration(self, round_start_timestamp):
        """
        Controls the "waiting time", so the rounds_per_second value is being kept at the specified value.
        :param round_start_timestamp: timestamp of the start of the round.
        :return:
        """
        # update and draw/animate scene
        self._viewer.update_data()
        if self._animation:
            self.animate(round_start_timestamp, -1 if self._auto_animation else self._manual_animation_speed)
        else:
            self._viewer.glDraw()

        # waiting until simulation starts
        self._wait_while_not_running()

        # record round
        if self._recording:
            self.recorder.record_round()
            self._splitter.setWindowTitle("Simulator, recorded: %d rounds" % len(self.recorder.records))

        # waiting until enough time passed to do the next simulation round.
        time_elapsed = time.perf_counter() - round_start_timestamp
        # sleeping time - max 1/120 s for a responsive GUI
        sleep_time = min(1.0 / 120, (1.0 / self._rounds_per_second) / 10.0)
        max_wait_time = 1 / self._rounds_per_second
        while time_elapsed < max_wait_time:
            time.sleep(sleep_time)
            # check if still running... if not wait (important for low rounds_per_second values)
            self._wait_while_not_running()
            time_elapsed = time.perf_counter() - round_start_timestamp

    def remove_agent(self, agent):
        """
        removes an agent from the visualization.
        it wont be deleted immediately! not until the next round.
        if you want an immediate deletion of the agent, then call this function, then, update_data and after that
        glDraw of the OpenGLWidget.

        :param agent: the agent (not the id, the instance) to be deleted
        :return:
        """
        self._viewer.agent_update_flag = True
        if agent in self._viewer.agent_offset_data:
            del self._viewer.agent_offset_data[agent]

    def agent_changed(self, agent):
        """
        updates the offset, color and carry data of the agent in the visualization.
        it wont be an immediate update. it will update in the beginning of the next "run" call / after current round.
        :param agent: the agent that has changed (the instance)
        :return:
        """
        self._viewer.agent_update_flag = True
        prev_pos = agent.coordinates
        if agent in self._viewer.agent_offset_data:
            prev_pos = self._viewer.agent_offset_data[agent][0]
        self._viewer.agent_offset_data[agent] = (agent.coordinates, agent.color, prev_pos,
                                                 1.0 if agent.is_carried() else 0.0)

    def remove_item(self, item):
        """
        removes an item from the visualization.
        :param item: the item (not the id, the instance) to be deleted
        :return:
        """
        self._viewer.item_update_flag = True
        if item in self._viewer.item_offset_data:
            del self._viewer.item_offset_data[item]

    def item_changed(self, item):
        """
        updates the offset, color and carry data of the item in the visualization.
        :param item: the item ( not the id, the instance) to be deleted
        :return:
        """
        self._viewer.item_update_flag = True
        prev_pos = item.coordinates
        if item in self._viewer.item_offset_data:
            prev_pos = self._viewer.item_offset_data[item][0]

        self._viewer.item_offset_data[item] = (item.coordinates, item.color, prev_pos,
                                               1.0 if item.is_carried() else 0.0)

    def remove_location(self, location):
        """
        removes a location from the visualization.
        :param location: the location (not the id, the instance) to be deleted
        :return:
        """
        self._viewer.location_update_flag = True
        if location in self._viewer.location_offset_data:
            del self._viewer.location_offset_data[location]

    def location_changed(self, location):
        """
        updates the offset and color data of the location in the visualization.
        :param location: the location ( not the id, the instance) to be deleted
        :return:
        """
        self._viewer.location_update_flag = True
        self._viewer.location_offset_data[location] = (location.coordinates, location.color)

    def update_visualization_data(self):
        self._viewer.update_data()

    # setters and getters for various variables in the visualization

    def set_rounds_per_second(self, rounds_per_second):
        self._rounds_per_second = rounds_per_second

    def get_rounds_per_second(self):
        return self._rounds_per_second

    def reset_camera_position(self):
        self._camera.reset()
        self._viewer.update_scene()

    def set_field_of_view(self, fov: float):
        self._camera.set_fov(fov)
        self._viewer.update_programs_projection_matrix()
        self._viewer.update_cursor_data()
        self._viewer.glDraw()

    def get_field_of_view(self):
        return self._camera.get_fov()

    def set_drag_sensitivity(self, s: float):
        self._viewer.drag_sensitivity = s

    def get_drag_sensitivity(self):
        return self._viewer.drag_sensitivity

    def set_zoom_sensitivity(self, s: float):
        self._viewer.zoom_sensitivity = s

    def get_zoom_sensitivity(self):
        return self._viewer.zoom_sensitivity

    def set_rotation_sensitivity(self, s: float):
        self._viewer.rotation_sensitivity = s

    def get_rotation_sensitivity(self):
        return self._viewer.rotation_sensitivity

    def get_projection_type(self):
        return self._camera.get_projection_type()

    def set_projection_type(self, projection_type):
        self._camera.set_projection_type(projection_type)
        self._viewer.update_programs_projection_matrix()
        self._viewer.glDraw()

    def get_background_color(self):
        return self._viewer.background

    def set_background_color(self, color):
        self._viewer.set_background_color(color)

    def get_grid_line_color(self):
        return self._viewer.programs["grid"].get_line_color()

    def set_grid_line_color(self, color):
        self._viewer.programs["grid"].set_line_color(color)

    def get_grid_border_color(self):
        return self._viewer.programs["grid"].get_border_color()

    def set_grid_border_color(self, color):
        self._viewer.programs["grid"].set_border_color(color)

    def get_grid_line_width(self):
        return self._viewer.programs["grid"].width

    def set_grid_line_width(self, width):
        self._viewer.programs["grid"].set_width(width)
        self._viewer.glDraw()

    def get_grid_line_scaling(self):
        return self._viewer.programs["grid"].get_line_scaling()

    def set_grid_line_scaling(self, scaling):
        self._viewer.programs["grid"].set_line_scaling(scaling)
        self._viewer.glDraw()

    def get_grid_coordinates_color(self):
        return self._viewer.programs["grid"].get_model_color()

    def set_grid_coordinates_color(self, color):
        self._viewer.programs["grid"].set_model_color(color)
        self._viewer.glDraw()

    def get_grid_coordinates_scaling(self):
        return self._viewer.programs["grid"].get_model_scaling()

    def set_grid_coordinates_scaling(self, scaling):
        self._viewer.programs["grid"].set_model_scaling(scaling)
        self._viewer.glDraw()

    def get_render_distance(self):
        return self._camera.get_render_distance()

    def set_render_distance(self, render_distance):
        self._camera.set_render_distance(render_distance)
        self._viewer.update_programs_projection_matrix()
        self._viewer.glDraw()

    def get_show_lines(self):
        return self._viewer.programs["grid"].show_lines

    def set_show_lines(self, show_lines: bool):
        self._viewer.programs["grid"].show_lines = show_lines
        self._viewer.glDraw()

    def get_show_border(self):
        return self._viewer.programs["grid"].show_border

    def set_show_border(self, show_border: bool):
        self._viewer.programs["grid"].show_border = show_border
        self._viewer.glDraw()

    def get_show_coordinates(self):
        return self._viewer.programs["grid"].show_coordinates

    def set_show_coordinates(self, show_coordinates: bool):
        self._viewer.programs["grid"].show_coordinates = show_coordinates
        self._viewer.glDraw()

    def get_show_center(self):
        return self._viewer.show_center

    def set_show_center(self, show_center: bool):
        self._viewer.show_center = show_center
        self._viewer.glDraw()

    def get_show_focus(self):
        return self._viewer.show_focus

    def set_show_focus(self, show_focus: bool):
        self._viewer.show_focus = show_focus
        self._viewer.glDraw()

    def take_screenshot(self, quick):
        self._viewer.take_screenshot(quick)

    def recalculate_grid(self, size):
        self.grid_size = size
        self._viewer.programs["grid"].update_offsets(self._world.grid.get_box(size))
        self._viewer.glDraw()

    def get_agent_scaling(self):
        return self._viewer.programs["agent"].get_model_scaling()

    def set_agent_scaling(self, scaling):
        self._viewer.programs["agent"].set_model_scaling(scaling)
        self._viewer.glDraw()

    def get_item_scaling(self):
        return self._viewer.programs["item"].get_model_scaling()

    def set_item_scaling(self, scaling):
        self._viewer.programs["item"].set_model_scaling(scaling)
        self._viewer.glDraw()

    def get_location_scaling(self):
        return self._viewer.programs["location"].get_model_scaling()

    def set_location_scaling(self, scaling):
        self._viewer.programs["location"].set_model_scaling(scaling)
        self._viewer.glDraw()

    def set_on_cursor_click_matter_type(self, matter_type):
        if matter_type == MatterType.ITEM or matter_type == MatterType.AGENT or matter_type == MatterType.LOCATION:
            self._viewer.cursor_type = matter_type
            self._viewer.update_cursor_data()

    def is_running(self):
        return self._running

    def get_added_matter_color(self):
        return self._viewer.added_matter_color

    def set_added_matter_color(self, color):
        self._viewer.added_matter_color = color

    def start_recording(self):
        self.recorder.record_round()
        self._splitter.setWindowTitle("Simulator, recorded: %d rounds" % len(self.recorder.records))
        self._recording = True

    def get_viewer_res(self):
        return self._viewer.width(), self._viewer.height()

    def stop_recording(self):
        self._recording = False

    def export_recording(self):
        if len(self.recorder.records) == 0:
            show_msg("No rounds recorded. Nothing to export.", Level.INFO, self._splitter)
            return
        if self._running:
            self.start_stop()
        self._viewer.set_show_info_frame(False)
        self._viewer.set_enable_cursor(False)
        if "set_disable_sim" in dir(self._gui_module):
            self._gui_module.set_disable_sim(True)
        else:
            show_msg("No 'set_disable_sim(disable_flag)' function in gui module found."
                     "\nRunning simulation within recording mode may result in undefined behavior!", Level.WARNING,
                     self._splitter)

        self.recorder.show(self.do_export)

        # loop
        while self.recorder.is_open():
            self._process_events()

        # go back to the main window
        if "set_disable_sim" in dir(self._gui_module):
            self._gui_module.set_disable_sim(False)

        self._viewer.agent_update_flag = True
        self._viewer.item_update_flag = True
        self._viewer.location_update_flag = True
        self._viewer.update_data()
        self._viewer.set_show_info_frame(True)
        self._viewer.set_enable_cursor(True)

    def do_export(self, rps, width, height, codec, first_frame_idx, last_frame_idx, animation):

        if not os.path.exists("outputs/videos") or not os.path.isdir("outputs/videos"):
            os.mkdir("outputs/videos")
        directory = "."
        if os.path.exists("outputs/videos") and os.path.isdir("outputs/videos"):
            directory = "outputs/videos"
        path = TopQFileDialog(self._splitter).getSaveFileName(options=(TopQFileDialog.Options()),
                                                              filter="*.mp4;;*.avi;;*.mkv",
                                                              directory=directory)
        if path[0] == '':
            return

        if path[0].endswith("mp4") or path[0].endswith(".avi") or path[0].endswith(".mkv"):
            fullpath = path[0]
        else:
            fullpath = path[0] + path[1].replace('*', '')

        if animation:
            animation_steps = int(30 / rps)
            if animation_steps < 1:
                animation_steps = 1
        else:
            animation_steps = 1

        writer = cv2.VideoWriter(fullpath, cv2.VideoWriter_fourcc(*codec), rps * animation_steps, (width, height))
        self._viewer.setDisabled(True)
        # creating and opening loading window
        lw = LoadingWindow("", "Exporting Video...")
        lw.show()
        out_of = (last_frame_idx - first_frame_idx + 1) * animation_steps
        for i in range(first_frame_idx - 1, last_frame_idx):
            # render and write frame
            self._viewer.inject_record_data(self.recorder.records[i])
            # animate
            for j in range(1, animation_steps + 1):
                # process events so the gui thread does respond to interactions..
                self._process_events()
                # update loading windows text and progress bar
                processing = (i - first_frame_idx + 1) * animation_steps + j
                lw.set_message("Please wait!\nExporting frame %d/%d..." % (processing, out_of))
                lw.set_progress(processing, out_of)
                self._viewer.set_animation_percentage(j / animation_steps)
                self._viewer.glDraw()
                img = self._viewer.get_frame_cv(width, height)
                writer.write(img)
        self._viewer.inject_record_data(self.recorder.records[last_frame_idx - 1])
        writer.release()
        lw.close()
        self._viewer.setDisabled(False)
        self._viewer.resizeGL(self._viewer.width(), self._viewer.height())
        self._viewer.update_scene()
        show_msg("Video exported successfully!", Level.INFO, self._splitter)

    def delete_recording(self):
        self.recorder = Recorder(self._world, self._viewer)
        self._splitter.setWindowTitle("Simulator")

    def set_antialiasing(self, value):
        if value <= 0:
            self._viewer.disable_aa()
        else:
            self._viewer.enable_aa(value)

    def take_vector_screenshot(self):
        if self._world.grid.__class__.__name__ == "TriangularGrid":
            if not os.path.exists("outputs/screenshots") or not os.path.isdir("outputs/screenshots"):
                os.mkdir("outputs/screenshots")
            directory = "."
            if os.path.exists("outputs/screenshots") and os.path.isdir("outputs/screenshots"):
                directory = "outputs/screenshots"

            path = TopQFileDialog(self._splitter).getSaveFileName(options=(TopQFileDialog.Options()),
                                                                  filter="*.svg",
                                                                  directory=directory)
            if path[0] == '':
                return

            if path[0].endswith(".svg"):
                create_svg(self._world, path[0])
            else:
                create_svg(self._world, path[0] + ".svg")
        else:
            show_msg("Not implemented yet.\nWorks only with Triangular Grid for now!\nSorry!", Level.WARNING,
                     self._splitter)

    def set_animation(self, animation):
        if not animation:
            self._viewer.set_animation_percentage(1)
        self._animation = animation

    def get_animation(self):
        return self._animation

    def set_auto_animation(self, auto_animation):
        self._auto_animation = auto_animation

    def get_auto_animation(self):
        return self._auto_animation

    def set_manual_animation_speed(self, manual_animation_speed):
        self._manual_animation_speed = manual_animation_speed

    def get_manual_animation_speed(self):
        return self._manual_animation_speed

    def get_main_window(self):
        return self._splitter

    def set_reset_flag(self):
        self._reset_flag = True
