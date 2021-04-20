"""The world module provides the interface of the simulation world. In the simulation world
all the data of the agents, items, and locations are stored.
It also have the the coordination system and stated the maximum of the x and y coordinate.

 .. todo:: What happens if the maximum y or x axis is passed? Either the start from the other side or turns back.
"""
import importlib
import logging
import random
import threading
import os
import datetime
import traceback

from core import agent, item, location, vis3d, velo_controlled_agent
from core.visualization.utils import show_msg, TopQFileDialog, VisualizationError, Level

def load_scenario(mod, world, goons=None, **kwargs):
    """
    Function to load the scenario into the world.
    Parameters:
    -----------
        goons = a place to pass optional arguments into the scenario functions. Must be used in conjuction with a scenario which accepts args.
    """
    try:
        mod.scenario(world, goons, **kwargs)
    except:
        traceback.print_exc()
        try:
            mod.scenario(world)
        except VisualizationError as ve:
            world._scenario_load_error = ve


class World:
    def __init__(self, config_data):
        """
        Initializing the world constructor
        :param config_data: configuration data from config.ini file
        """
        self.__round_counter = 1
        self.__end = False

        self.init_agents = []
        self.agent_id_counter = 0
        self.agents = []
        self.agent_map_coordinates = {}
        self.agent_map_id = {}
        self.agents_created = []
        self.agent_rm = []
        self.__agent_deleted = False
        self.new_agent = None

        self.items = []
        self.item_map_coordinates = {}
        self.item_map_id = {}
        self.items_created = []
        self.item_rm = []

        self.__item_deleted = False
        self.new_item = None

        self.locations = []
        self.location_map_coordinates = {}
        self.location_map_id = {}
        self.locations_created = []
        self.locations_rm = []
        self.__location_deleted = False
        self.new_location = None

        self.config_data = config_data
        self.grid = config_data.grid

        self.csv_generator_module = importlib.import_module('components.generators.csv.%s' % config_data.csv_generator)
        self.csv_round = self.csv_generator_module.CsvRoundData(scenario=config_data.scenario,
                                                                solution=config_data.solution,
                                                                seed=config_data.seed_value,
                                                                directory=config_data.directory_csv)

        if config_data.visualization:
            self.vis = vis3d.Visualization(self)
        else:
            self.vis = None

        self._scenario_load_error = None

    def reset(self):
        """
        resets everything (agents, items, locations) except for the logging in system.log and in the csv file...
        reloads the scenario.
        :return:
        """
        self.__round_counter = 1
        self.__end = False

        self.init_agents = []
        self.agent_id_counter = 0
        self.agents = []
        self.agents_created = []
        self.agent_rm = []
        self.agent_map_coordinates = {}
        self.agent_map_id = {}
        self.__agent_deleted = False
        self.new_agent = None

        self.items = []
        self.items_created = []
        self.item_rm = []
        self.item_map_coordinates = {}
        self.item_map_id = {}
        self.__item_deleted = False
        self.new_item = None

        self.locations = []
        self.locations_created = []
        self.location_map_coordinates = {}
        self.location_map_id = {}
        self.locations_rm = []
        self.__location_deleted = False
        self.new_location = None
        self._scenario_load_error = None

        if self.vis is not None:
            self.vis.reset()

    def init_scenario(self, scenario_module, goons=None, **kwargs):
        if self.config_data.visualization:
            # if visualization is on, run the scenario in a separate thread and show that the program runs..
            x = threading.Thread(target=load_scenario, args=(scenario_module, self, goons), kwargs=kwargs)
            self.vis.wait_for_thread(x, "loading scenario... please wait.", "Loading Scenario")
        else:
            # if no vis, just run the scenario on the main thread
            load_scenario(scenario_module, self, goons)

        if self._scenario_load_error is not None:
            show_msg("Error while loading Scenario:\n%s" % self._scenario_load_error.msg, Level.CRITICAL,
                     self.vis.get_main_window())
            exit(1)

        if self.vis is not None:
            self.vis.update_visualization_data()

        if self.config_data.agent_random_order:
            random.shuffle(self.agents)

    def save_scenario(self, quick):

        def save_scenario(fn):
            try:
                f = open(fn, "w+")
                f.write("def scenario(world):\n")
                for prtc in self.agent_map_coordinates.values():
                    f.write("\tworld.add_agent(%s, color=%s)\n" % (str(prtc.coordinates), str(prtc.get_color())))
                for tl in self.item_map_coordinates.values():
                    f.write("\tworld.add_item(%s, color=%s)\n" % (str(tl.coordinates), str(tl.get_color())))
                for lctn in self.location_map_coordinates.values():
                    f.write("\tworld.add_location(%s, color=%s)\n" % (str(lctn.coordinates), str(lctn.get_color())))
                f.flush()
                f.close()
            except IOError as e:
                show_msg("Couldn't save scenario.\n%s" % e, Level.WARNING, self.vis.get_main_window())

        # create scenario folder, if it doesn't already exist.
        if not os.path.exists("components/scenario") or not os.path.isdir("components/scenario"):
            os.mkdir("components/scenario")

        if quick:
            # if the scenario folder exists, try to create and save the new scenario file, if it fails print the error.
            if os.path.exists("components/scenario") and os.path.isdir("components/scenario"):
                now = datetime.datetime.now()
                filename = str("components/scenario/%d-%d-%d_%d-%d-%d_scenario.py"
                               % (now.year, now.month, now.day, now.hour, now.minute, now.second))
                save_scenario(filename)
                # checks if the file exists. If not, some unknown error occured while saving.
                if not os.path.exists(filename) or not os.path.isfile(filename):
                    show_msg("Error: scenario couldn't be saved due to an unknown reason.", Level.WARNING,
                             self.vis.get_main_window())
            else:
                show_msg("\"scenario\" folder couldn't be created.", Level.WARNING, self.vis.get_main_window())
        else:
            directory = "."
            if os.path.exists("components/scenario") and os.path.isdir("components/scenario"):
                directory = "components/scenario"
            path = TopQFileDialog(self.vis.get_main_window()).getSaveFileName(options=TopQFileDialog.Options(),
                                                                              filter="*.py",
                                                                              directory=directory)

            if path[0] == '':
                return

            if path[0].endswith(".py"):
                save_scenario(path[0])
            else:
                save_scenario(path[0] + ".py")

    def csv_aggregator(self):
        self.csv_round.aggregate_metrics()
        agent_csv = self.csv_generator_module.CsvAgentFile(self.config_data.directory_csv)
        for a in self.agents:
            agent_csv.write_agent(a)
        agent_csv.csv_file.close()

    def set_successful_end(self):
        self.csv_round.success()
        self.__end = True
        # self.set_end()

    def set_successful_round(self):
        self.csv_round.success()

    def get_max_round(self):
        """
        The max round number

        :return: maximum round number
        """
        return self.config_data.max_round

    def get_actual_round(self):
        """
        The actual round number

        :return: actual round number
        """
        return self.__round_counter

    def set_unsuccessful_end(self):
        """
        Allows to terminate before the max round is reached
        """
        self.__end = True

    def get_end(self):
        """
            Returns the end parameter values either True or False
        """
        return self.__end

    def inc_round_counter_by(self, number=1):
        """
        Increases the the round counter by

        :return:
        """
        self.__round_counter += number

    def get_solution(self):
        """
        actual solution name

        :return: actual solution name
        """
        return self.config_data.solution

    def get_amount_of_agents(self):
        """
        Returns the actual number of agents in the world

        :return: The actual number of agents
        """
        return len(self.agents)

    def get_agent_list(self):
        """
        Returns the actual number of agents in the world

        :return: The actual number of agents
        """
        return self.agents

    def get_agent_map_coordinates(self):
        """
        Get a dictionary with all agents mapped with their actual coordinates

        :return: a dictionary with agents and their coordinates
        """
        return self.agent_map_coordinates

    def get_agent_map_id(self):
        """
        Get a dictionary with all agents mapped with their own ids

        :return: a dictionary with agents and their own ids
        """
        return self.agent_map_id

    def get_amount_of_items(self):
        """
        Returns the actual number of agents in the world

        :return: The actual number of items
        """
        return len(self.items)

    def get_items_list(self):
        """
        Returns the actual number of items in the world

        :return: a list of all the items in the world
        """
        return self.items

    def get_item_map_coordinates(self):
        """
        Get a dictionary with all items mapped with their actual coordinates

        :return: a dictionary with agents and their coordinates
        """
        return self.item_map_coordinates

    def get_item_map_id(self):
        """
        Get a dictionary with all agents mapped with their own ids

        :return: a dictionary with agents and their own ids
        """
        return self.item_map_id

    def get_amount_of_locations(self):
        """
        Returns the actual number of locations in the world

        :return: The actual number of locations
        """
        return len(self.locations)

    def get_location_list(self):
        """
        Returns the actual number of locations in the world

        :return: The actual number of locations
        """
        return self.locations

    def get_location_map_coordinates(self):
        """
        Get a dictionary with all locations mapped with their actual coordinates

        :return: a dictionary with locations and their coordinates
        """
        return self.location_map_coordinates

    def get_location_map_id(self):
        """
        Get a dictionary with all locations mapped with their own ids

        :return: a dictionary with locations and their own ids
        """
        return self.location_map_id

    def get_x_size(self):
        """

        :return: Returns the maximal x size of the world
        """
        return self.config_data.size_x

    def get_y_size(self):
        """
        :return: Returns the maximal y size of the world
        """
        return self.config_data.size_y

    def get_z_size(self):
        """

        :return: Returns the maximal z size of the world
        """
        return self.config_data.size_z

    def get_size(self):
        """
        :return: Returns the maximal (x,y) size of the world as a tupel
        """
        return self.config_data.size_x, self.config_data.size_y

    def get_item_deleted(self):
        return self.__item_deleted

    def get_agent_deleted(self):
        return self.__agent_deleted

    def get_location_deleted(self):
        return self.__location_deleted

    def set_item_deleted(self):
        self.__item_deleted = False

    def set_agent_deleted(self):
        self.__agent_deleted = False

    def set_location_deleted(self):
        self.__location_deleted = False

    ##TODO: add ability to set initial velocities.
    def add_agent(self, coordinates, color=None, new_class=agent.Agent, velocities=None):
        """
        Add an agent to the world database

        :param coordinates: The coordinatex of the agent
        :param color: The color of the agent
        :param new_class: the Agent class to be created (default: agent.Agent)
        :return: Added Matter; False: Unsuccessful
        """
        if self.config_data.agent_type == 1:
            new_class = velo_controlled_agent.VeloAgent

        if isinstance(coordinates, int) or isinstance(coordinates, float):
            coordinates = (coordinates, color, 0.0)
            color = None

        elif len(coordinates) == 2:
            coordinates = (coordinates[0], coordinates[1], 0.0)

        if len(self.agents) < self.config_data.max_agents:
            if self.grid.are_valid_coordinates(coordinates):
                if coordinates not in self.get_agent_map_coordinates():
                    if color is None:
                        color = self.config_data.agent_color
                    self.agent_id_counter += 1
                    if self.config_data.agent_type == 1:
                        self.new_agent = new_class(self, coordinates, color, self.agent_id_counter, velocities)
                    else:
                        self.new_agent = new_class(self, coordinates, color, self.agent_id_counter)
                    if self.vis is not None:
                        self.vis.agent_changed(self.new_agent)
                    self.agents_created.append(self.new_agent)
                    self.agent_map_coordinates[self.new_agent.coordinates] = self.new_agent
                    self.agent_map_id[self.new_agent.get_id()] = self.new_agent
                    self.agents.append(self.new_agent)
                    self.csv_round.update_agent_num(len(self.agents))
                    self.init_agents.append(self.new_agent)
                    self.new_agent.created = True
                    logging.info("Created agent at %s", self.new_agent.coordinates)
                    return self.new_agent

                else:
                    logging.info("there is already an agent on %s" % str(coordinates))
                    return False
            else:
                logging.info("%s is not a valid location!" % str(coordinates))
                return False
        else:
            logging.info("Max of agents reached and no more agents can be created")
            return False

    def remove_agent(self, agent_id):
        """ Removes an agent with a given agent id from the world database


        :param agent_id: agent id
        :return: True: Successful removed; False: Unsuccessful
        """
        rm_agent = self.agent_map_id[agent_id]
        if rm_agent:
            self.agents.remove(rm_agent)
            del self.agent_map_coordinates[rm_agent.coordinates]
            del self.agent_map_id[agent_id]
            self.agent_rm.append(rm_agent)
            if self.vis is not None:
                self.vis.remove_agent(rm_agent)
            self.csv_round.update_agent_num(len(self.agents))
            self.csv_round.update_metrics(agents_deleted=1)
            self.__agent_deleted = True
            return True
        else:
            return False

    def remove_agent_on(self, coordinates):
        """
        Removes an agent on a give coordinate from to the world database

        :param coordinates: A tuple that includes the x and y coordinates
        :return: True: Successful removed; False: Unsuccessful
        """
        if coordinates in self.agent_map_coordinates:
            return self.remove_agent(self.agent_map_coordinates[coordinates].get_id())
        else:
            return False

    def add_item(self, coordinates, color=None):
        """
        Adds an item to the world database
        :param color: color of the item (None for config default)
        :param coordinates: the coordinates on which the item should be added
        :return: Successful added matter; False: Unsuccessful
        """
        if isinstance(coordinates, int) or isinstance(coordinates, float):
            coordinates = (coordinates, color, 0.0)
            color = None

        elif len(coordinates) == 2:
            coordinates = (coordinates[0], coordinates[1], 0.0)

        if self.grid.are_valid_coordinates(coordinates):
            if coordinates not in self.item_map_coordinates:
                if color is None:
                    color = self.config_data.item_color
                self.new_item = item.Item(self, coordinates, color)
                self.items.append(self.new_item)
                if self.vis is not None:
                    self.vis.item_changed(self.new_item)
                self.csv_round.update_items_num(len(self.items))
                self.item_map_coordinates[self.new_item.coordinates] = self.new_item
                self.item_map_id[self.new_item.get_id()] = self.new_item
                logging.info("Created item with id %s on coordinates %s",
                             str(self.new_item.get_id()), str(coordinates))
                return self.new_item

            else:
                logging.info("there is already an item on %s " % str(coordinates))
                return False
        else:
            logging.info("%s is not a valid location!" % str(coordinates))
            return False

    def remove_item(self, item_id):
        """
        Removes an item with a given item_id from to the world database

        :param item_id: The items id that should be removed
        :return:  True: Successful removed; False: Unsuccessful
        """
        if item_id in self.item_map_id:
            rm_item = self.item_map_id[item_id]
            self.items.remove(rm_item)
            self.item_rm.append(rm_item)
            if self.vis is not None:
                self.vis.remove_item(rm_item)
            logging.info("Deleted item with id %s on %s", str(rm_item.get_id()), str(rm_item.coordinates))
            try:  # cher: added so the program does not crashed if it does not find any entries in the map
                del self.item_map_id[rm_item.get_id()]
            except KeyError:
                pass
            try:  # cher: added so the program does not crashed if it does not find any entries in the map
                del self.item_map_coordinates[rm_item.coordinates]
            except KeyError:
                pass
            self.csv_round.update_items_num(len(self.items))
            self.csv_round.update_metrics(items_deleted=1)
            self.__item_deleted = True
            return True
        else:
            return False

    def remove_item_on(self, coordinates):
        """
        Removes an item on a give coordinates from to the world database

        :param coordinates: A tuple that includes the x and y coordinates
        :return: True: Successful removed; False: Unsuccessful
        """
        if coordinates in self.item_map_coordinates:
            return self.remove_item(self.item_map_coordinates[coordinates].get_id())

        else:
            return False

    def add_location(self, coordinates, color=None):
        """
        Add a location to the world database

        :param color:
        :param coordinates: the coordinates on which the location should be added
        :return: True: Successful added; False: Unsuccessful
        """

        if isinstance(coordinates, int) or isinstance(coordinates, float):
            coordinates = (coordinates, color, 0.0)
            color = None

        elif len(coordinates) == 2:
            coordinates = (coordinates[0], coordinates[1], 0.0)

        if self.grid.are_valid_coordinates(coordinates):
            if coordinates not in self.location_map_coordinates:
                if color is None:
                    color = self.config_data.location_color
                self.new_location = location.Location(self, coordinates, color)
                self.locations.append(self.new_location)
                if self.vis is not None:
                    self.vis.location_changed(self.new_location)
                self.location_map_coordinates[self.new_location.coordinates] = self.new_location
                self.location_map_id[self.new_location.get_id()] = self.new_location
                self.csv_round.update_locations_num(len(self.locations))
                logging.info("Created location with id %s on coordinates %s",
                             str(self.new_location.get_id()), str(self.new_location.coordinates))
                self.new_location.created = True
                return self.new_location
            else:
                logging.info("there is already a location on %s" % str(coordinates))
                return False
        else:
            logging.info("%s is not a valid location!" % str(coordinates))
            return False

    def remove_location(self, location_id):
        """
        Removes a location with a given location_id from to the world database

        :param location_id: The locations id that should be removed
        :return:  True: Successful removed; False: Unsuccessful
        """
        if location_id in self.location_map_id:
            rm_location = self.location_map_id[location_id]
            if rm_location in self.locations:
                self.locations.remove(rm_location)
            if self.vis is not None:
                self.vis.remove_location(rm_location)
            self.locations_rm.append(rm_location)
            logging.info("Deleted location with location id %s on %s", str(location_id), str(rm_location.coordinates))
            try:
                del self.location_map_coordinates[rm_location.coordinates]
            except KeyError:
                pass
            try:
                del self.location_map_id[location_id]
            except KeyError:
                pass
            self.csv_round.update_locations_num(len(self.locations))
            self.csv_round.update_metrics(location_deleted=1)
            self.__location_deleted = True
            return True
        else:
            return False

    def remove_location_on(self, coordinates):
        """
        Removes a location on a give coordinates from to the world database

        :param coordinates: A tuple that includes the x and y coordinates
        :return: True: Successful removed; False: Unsuccessful
        """
        if coordinates in self.location_map_coordinates:
            return self.remove_location(self.location_map_coordinates[coordinates].get_id())
        else:
            return False

