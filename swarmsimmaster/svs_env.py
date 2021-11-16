import gym
from gym import spaces
from core import world, config
import swarmsim
import logging
import numpy as np

from swarmsimmaster.old_comms_test import communication_model


class SingleExplorer(gym.Env):
    """Custom Environment that follows gym interface"""

    def __init__(self):
        super(SingleExplorer, self).__init__()
        # Define action and observation space
        # They must be gym.spaces objects
        # Example when using discrete actions:
        ##may need to alter configdata to be closer to fit our needs.
        config_data = config.ConfigData()
        unique_descriptor = "%s_%s_%s" % (config_data.local_time,
                                          config_data.scenario.rsplit('.', 1)[0],
                                          config_data.solution.rsplit('.', 1)[0])

        logging.basicConfig(filename="outputs/logs/system_%s.log" % unique_descriptor, filemode='w',
                            level=logging.INFO, format='%(message)s')
        logging.info('Started')

        swarmsim.read_cmd_args(config_data)
        swarmsim.create_directory_for_data(config_data, unique_descriptor)
        swarmsim.random.seed(config_data.seed_value)
        self.swarm_sim_world = world.World(config_data)
        self.ts = 0
        self.discovered_items = set()
        self.explored_points = set()

        self.swarm_sim_world.init_scenario(swarmsim.get_scenario(config_data))
        self.off_clr = config_data.off_agent_color
        self.def_clr = config_data.def_agent_color
        self.goal_center = config_data.goal_center
        # self.NUM_AGENTS = self.swarm_sim_world.get_amount_of_agents()
        # each agent can move one of 9 ways, with
        # self.action_space = spaces.MultiDiscrete(np.full_like(self.NUM_AGENTS, 9)) # xyz motion
        self.action_space = spaces.Discrete(len(self.swarm_sim_world.grid.get_directions_list()))
        # observation of the coordinates of each agent and the 6 neighboring locations
        # space should be the current position, plus the hops
        self.observation_space = spaces.Box(
            np.array([-9999, -9999, -9999] + [0] * len(self.swarm_sim_world.grid.get_directions_list())),
            np.array([9999, 9999, 9999] + [1] * len(self.swarm_sim_world.grid.get_directions_list())))
        # self.observation_space = spaces.Box(np.array([1]), np.array([2]))

    # step returns
    def step(self, action):
        print("stepping...")
        # Execute one time step within the environment
        # round_start_timestamp = time.perf_counter()
        action_counter = 0
        obs = []
        reward = 0
        done = False
        for agent in self.swarm_sim_world.agents:
            move = self.swarm_sim_world.grid.get_directions_list()[action]

            if move in self.get_valid_directions(agent):
                agent.move_to(move)

            action_counter += 1

        # kill agents
        off_drones = self.get_drones(self.swarm_sim_world, self.off_clr)
        def_drones = self.get_drones(self.swarm_sim_world, self.def_clr)

        self.proximity_death_check(def_drones, off_drones, lambda d: 1 - 3*d)

        # check if done
        for agent in off_drones:
            if np.linalg.norm(np.array(agent.coordinates) - np.array(self.goal_center)) < 0.1:
                done = True

        self.ts += 1
        return np.array(obs), reward, done, {}  # TODO config observations, reward

    # Currently returns all directions which point to coordinates on the map
    def get_valid_directions(self, agent):
        valid_directions = []
        for direction in self.swarm_sim_world.grid.get_directions_list():
            direction_coordinates = self.swarm_sim_world.grid.get_coordinates_in_direction(agent.coordinates, direction)
            if self.swarm_sim_world.grid.are_valid_coordinates(direction_coordinates):
                valid_directions.append(direction)
        return valid_directions

    def reset(self):
        # Reset the state of the environment to an initial state
        swarmsim.do_reset(self.swarm_sim_world)
        self.explored_points = set()
        self.ts = 0
        self.discovered_items = set()
        obs = []
        for agent in self.swarm_sim_world.agents:
            obs += agent.coordinates
            for direction in self.swarm_sim_world.grid.get_directions_list():
                adjacent_location_coords = self.swarm_sim_world.grid.get_coordinates_in_direction(agent.coordinates,
                                                                                                  direction)
                if adjacent_location_coords in self.swarm_sim_world.item_map_coordinates:
                    obs += [1]
                    self.discovered_items.add(adjacent_location_coords)
                else:
                    obs += [0]
            self.explored_points.add(agent.coordinates)

        return np.array(obs)

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        return

    # death checks TODO refactor into some sort of util lib
    def death_routine(self, a):
        a.alive = False
        a.update_agent_coordinates(a, (100, 100, 0))

    def proximity_death_check(self, defense_drones, offense_drones, chance_func):
        global terminated

        # death check for offense
        for a in offense_drones:
            _, near_defense = self.get_local_agents(a, offense_drones, defense_drones)

            # check if dead
            for d in near_defense:
                distance = np.linalg.norm(np.array(d.coordinates) - np.array(a.coordinates))
                if np.random.rand() < chance_func(distance):
                    self.death_routine(a)
                    ### hopefully temporary?
                    d.kills += 1
                    ###
                    break
        return

    # defenders die after eliminating `n` attackers
    def kill_death_check(self, world, defense_drones, offense_drones):
        for a in defense_drones:
            if (a.kills) >= 3:
                self.death_routine(a)

    def get_drones(self, world, clr):
        lst = []
        for a in world.get_agent_list():
            if a.color == clr and a.alive:
                lst.append(a)
        return lst

    # returns lists of offense and defense drones "visible" to the agent
    def get_local_agents(self, agent, offense_drones, defense_drones, des_comms_model="disk", disk_range=3):
        local_offense = []
        local_defense = []

        x2, y2 = agent.coordinates[0], agent.coordinates[1]
        for o in offense_drones:
            x1, y1 = o.coordinates[0], o.coordinates[1]
            dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=des_comms_model, DISK_RANGE_M=disk_range)
            if (comm_range):
                local_offense.append(o)
        for d in defense_drones:
            x1, y1 = d.coordinates[0], d.coordinates[1]
            dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=des_comms_model, DISK_RANGE_M=disk_range)
            if (comm_range):
                local_defense.append(d)

        return local_offense, local_defense

    # offense death check with % chance of death
    def off_death_check2(world, defense_drones, offense_drones):
        global terminated

        # death check for offense
        for a in offense_drones:
            sorted_defense = sorted(defense_drones,
                                    key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(a.coordinates)))
            closest_defense = sorted_defense[0]
            # check if dead
            if np.linalg.norm(
                    np.array(closest_defense.coordinates) - np.array(a.coordinates)) < 0.1 and np.random.rand() > 0.8:
                death_routine(a)

                ### hopefully temporary?
                closest_defense.kills += 1
                ###

            # check if attackers win:
            if np.linalg.norm(np.array(a.coordinates) - np.array(defense_center)) < 0.1:
                terminated = True
