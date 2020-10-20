import configparser
from datetime import datetime
from ast import literal_eval as make_tuple
import importlib
from enum import Enum


class ConfigData:
    class ConfigType(Enum):
        STRING = 0  # String is the default for all variables, which are not defined in the mapping dictionary
        BOOLEAN = 1
        INTEGER = 2
        FLOAT = 3
        TUPLE = 4

    # type definitions of config variables.
    # A definition of a variable is not required: missing variables will be interpreted and saved as strings
    mapping = {
        "Simulator": {
            "seed_value": ConfigType.INTEGER,
            "max_round": ConfigType.INTEGER,
            "agent_random_order": ConfigType.BOOLEAN,
            "agent_random_order_always": ConfigType.BOOLEAN,
            "window_size_x": ConfigType.INTEGER,
            "window_size_y": ConfigType.INTEGER,
            "close_at_end": ConfigType.BOOLEAN,
        },
        "Visualization": {
            "visualization": ConfigType.BOOLEAN,
            "agent_color": ConfigType.TUPLE,
            "agent_scaling": ConfigType.TUPLE,
            "item_color": ConfigType.TUPLE,
            "item_scaling": ConfigType.TUPLE,
            "location_color": ConfigType.TUPLE,
            "location_scaling": ConfigType.TUPLE,
            "grid_color": ConfigType.TUPLE,
            "cursor_color": ConfigType.TUPLE,
            "center_color": ConfigType.TUPLE,
            "background_color": ConfigType.TUPLE,
            "line_color": ConfigType.TUPLE,
            "line_scaling": ConfigType.TUPLE,
            "show_lines": ConfigType.BOOLEAN,
            "coordinates_color": ConfigType.TUPLE,
            "coordinates_scaling": ConfigType.TUPLE,
            "show_coordinates": ConfigType.BOOLEAN,
            "show_center": ConfigType.BOOLEAN,
            "focus_color": ConfigType.TUPLE,
            "show_focus": ConfigType.BOOLEAN,
            "look_at": ConfigType.TUPLE,
            "phi": ConfigType.INTEGER,
            "theta": ConfigType.INTEGER,
            "radius": ConfigType.INTEGER,
            "fov": ConfigType.INTEGER,
            "cursor_offset": ConfigType.INTEGER,
            "render_distance": ConfigType.INTEGER,
            "show_border": ConfigType.BOOLEAN,
            "border_color": ConfigType.TUPLE,
            "animation": ConfigType.BOOLEAN,
            "auto_animation": ConfigType.BOOLEAN,
            "manual_animation_speed": ConfigType.INTEGER,
        },
        "World": {
            "border": ConfigType.BOOLEAN,
            "type": ConfigType.INTEGER,
            "size_x": ConfigType.FLOAT,
            "size_y": ConfigType.FLOAT,
            "size_z": ConfigType.FLOAT,
            "max_agents": ConfigType.INTEGER
        },
        "Matter": {
            "memory_limitation": ConfigType.BOOLEAN,
            "location_mm_size": ConfigType.INTEGER,
            "agent_mm_size": ConfigType.INTEGER,
            "item_mm_size": ConfigType.INTEGER
        },
    }

    def __init__(self):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("config.ini")

        # load all variables
        for section in config.sections():
            for option in config.options(section):
                try:
                    config_type = self.mapping[section][option]
                    if config_type == self.ConfigType.BOOLEAN:
                        setattr(self, option, config.getboolean(section, option))
                    elif config_type == self.ConfigType.INTEGER:
                        setattr(self, option, config.getint(section, option))
                    elif config_type == self.ConfigType.FLOAT:
                        setattr(self, option, config.getfloat(section, option))
                    elif config_type == self.ConfigType.TUPLE:
                        setattr(self, option, make_tuple(config.get(section, option)))
                    elif config_type == self.ConfigType.STRING:
                        setattr(self, option, config.get(section, option))
                except KeyError:
                    # if not defined in mapping treat it as a string
                    setattr(self, option, config.get(section, option))

        # process variables if needed

        if self.gui is None:
            print("Warning: no gui option given. setting to default gui")
            self.gui = "default"

        if self.grid_class is None:
            self.grid_class = None
            raise RuntimeError("Error: no grid class defined in config.ini...")

        try:
            self.grid_size = config.getint("Visualization", "grid_size")
        except configparser.NoOptionError:
            print("Warning: grid size is not configured. setting to default of 5")
            self.grid_size = 5

        grid_module, grid_class = self.grid_class.rsplit(".", 1)
        test = getattr(importlib.import_module("components.grids.%s" % grid_module), grid_class)
        self.grid = test(self.grid_size)

        if self.scenario is None:
            self.scenario = "init_scenario.py"

        if self.solution is None:
            self.solution = "solution.py"

        self.local_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')[:-1]
        self.multiple_sim = 0
        self.directory_name = ""