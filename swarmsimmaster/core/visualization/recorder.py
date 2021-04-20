import copy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QSlider, QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMainWindow, \
    QComboBox, QCheckBox

from core.visualization.utils import show_msg, Level


class Recorder:
    def __init__(self, world, viewer):
        self.records = []
        self._world = world
        self._viewer = viewer
        self._width_edit = None
        self._height_edit = None
        self._fps_edit = None
        self._gui = None

    def show(self, export_callback):
        self._gui = self._create_recorder_gui(export_callback)
        self._gui.show()
        if len(self.records) > 0:
            self._viewer.inject_record_data(self.records[0])

    def is_open(self):
        return self._gui.isVisible()

    def record_round(self):
        r = [[[], [], [], []], [[], [], [], []], [[], []]]
        for agent in self._world.agents:
            r[0][0].append(copy.deepcopy(agent.coordinates))
            r[0][1].append(copy.deepcopy(agent.color))
            if len(self.records) > 0:
                r[0][2].append(copy.deepcopy(self.records[-1][0][0]))
            else:
                r[0][2].append(copy.deepcopy(agent.coordinates))
            r[0][3].append(copy.deepcopy(agent.is_carried()))

        for item in self._world.items:
            r[1][0].append(copy.deepcopy(item.coordinates))
            r[1][1].append(copy.deepcopy(item.color))
            if len(self.records) > 0:
                r[1][2].append(copy.deepcopy(self.records[-1][1][0]))
            else:
                r[1][2].append(copy.deepcopy(item.coordinates))
            r[1][3].append(copy.deepcopy(item.is_carried()))

        for location in self._world.locations:
            r[2][0].append(copy.deepcopy(location.coordinates))
            r[2][1].append(copy.deepcopy(location.color))

        self.records.append(r)

    @staticmethod
    def copy_agent(agent):
        coords = copy.copy(agent.coordinates)
        color = copy.copy(agent.color)
        status = copy.copy(agent.is_carried())
        return coords, color, status

    @staticmethod
    def copy_item(item):
        coords = copy.copy(item.coordinates)
        color = copy.copy(item.color)
        status = copy.copy(item.is_carried())
        return coords, color, status

    @staticmethod
    def copy_location(location):
        coords = copy.copy(location.coordinates)
        color = copy.copy(location.color)
        return coords, color

    def _create_recorder_gui(self, export_callback):
        window = QMainWindow()
        window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        window.setWindowTitle("Video Export Tool")
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        round_slider_box = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setTickInterval(1)
        slider.setTickPosition(1)
        slider.setMaximum(len(self.records) - 1)
        slider.setMinimum(0)
        slider.setSliderPosition(0)
        text = QLabel("rounds: 1/%d" % len(self.records))

        def onchange(value):
            self._viewer.inject_record_data(self.records[value])
            self._viewer.glDraw()
            text.setText("rounds: %d/%d" % (value + 1, len(self.records)))

        # noinspection PyUnresolvedReferences
        slider.valueChanged.connect(onchange)
        round_slider_box.addWidget(text)
        round_slider_box.addWidget(slider)

        fps_edit = QLineEdit()
        fps_edit.setText(str(self._world.vis.get_rounds_per_second()))
        fpsbox = QHBoxLayout()
        fpsbox.addWidget(QLabel("rounds per second:"))
        fpsbox.addWidget(fps_edit)

        width, height = self._world.vis.get_viewer_res()
        width_edit = QLineEdit()
        width_edit.setText(str(width))
        height_edit = QLineEdit()
        height_edit.setText(str(height))
        resbox = QHBoxLayout()
        resbox.addWidget(QLabel("resolution:"))
        resbox.addWidget(width_edit)
        resbox.addWidget(QLabel("x"))
        resbox.addWidget(height_edit)

        start_frame = QLineEdit("1")
        end_frame = QLineEdit(str(len(self.records)))
        frames_box = QHBoxLayout()
        frames_box.addWidget(QLabel("first frame:"))
        frames_box.addWidget(start_frame)
        frames_box.addWidget(QLabel("last frame:"))
        frames_box.addWidget(end_frame)

        codec_combo = QComboBox()
        codec_combo.addItem("mp4v", 'mp4v')
        codec_combo.addItem("X264", 'X264')
        codec_combo.addItem("MJPG", 'MJPG')
        codec_combo.addItem("DIVX", 'DIVX')
        codec_combo.addItem("XVID", 'XVID')
        codec_box = QHBoxLayout()
        codec_box.addWidget(QLabel("codec:"))
        codec_box.addWidget(codec_combo)

        anim_checkbox = QCheckBox("export with animation")
        anim_checkbox.setChecked(self._world.vis.get_animation())

        export_button = QPushButton("export video")

        def export_call():
            try:
                input_rps = float(fps_edit.text())
                if input_rps <= 0:
                    show_msg("Rounds per second has to be greater than 0!", Level.WARNING, window)
                    return
            except ValueError:
                show_msg("Rounds per second has to be a number!", Level.WARNING, window)
                return

            try:
                input_width = int(width_edit.text())
                if input_width <= 0:
                    show_msg("Width has to be greater than 0!", Level.WARNING, window)
                    return
            except ValueError:
                show_msg("Width has to be an integer!", Level.WARNING, window)
                return

            try:
                input_height = int(height_edit.text())
                if input_height <= 0:
                    show_msg("Height has to be greater than 0!", Level.WARNING, window)
                    return
            except ValueError:
                show_msg("Height has to be an integer!", Level.WARNING, window)
                return

            try:
                ff = int(start_frame.text())
                ef = int(end_frame.text())
                if ff < 1 or ef < 1:
                    show_msg("frame index cannot be lower than 1", Level.WARNING, window)
                    return
                if ff > len(self.records) or ef > len(self.records):
                    show_msg("frame index cannot be higher than the index of last frame (%d)" % len(self.records),
                             Level.WARNING, window)
                    return
                if ff > ef:
                    show_msg("index of first frame cannot be higher than index of last frame", Level.WARNING, window)
                    return
            except ValueError:
                show_msg("frame index has to be an integer!", Level.WARNING, window)
                return

            window.setDisabled(True)
            export_callback(input_rps, input_width, input_height,
                            codec_combo.itemData(codec_combo.currentIndex()), ff, ef, anim_checkbox.isChecked())
            window.setDisabled(False)

        # noinspection PyUnresolvedReferences
        export_button.clicked.connect(export_call)

        main_layout.addLayout(round_slider_box)
        main_layout.addLayout(frames_box)
        main_layout.addLayout(fpsbox)
        main_layout.addLayout(resbox)
        main_layout.addLayout(codec_box)
        main_layout.addWidget(anim_checkbox)
        main_layout.addWidget(export_button)
        window.setCentralWidget(main_widget)
        return window
