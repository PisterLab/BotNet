import gym
from gym import spaces
from core import world, config
import swarmsim
import logging
import numpy as np
import time

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
    #self.NUM_AGENTS = self.swarm_sim_world.get_amount_of_agents()
    #each agent can move one of 9 ways, with
    #self.action_space = spaces.MultiDiscrete(np.full_like(self.NUM_AGENTS, 9)) # xyz motion
    self.action_space = spaces.Discrete(len(self.swarm_sim_world.grid.get_directions_list()))
    #observation of the coordinates of each agent and the 6 neighboring locations
    #space should be the current position, plus the hops
    self.observation_space = spaces.Box(np.array([-9999, -9999, -9999] + [0] * len(self.swarm_sim_world.grid.get_directions_list()) ), np.array([9999, 9999, 9999] + [1] * len(self.swarm_sim_world.grid.get_directions_list())))
    #self.observation_space = spaces.Box(np.array([1]), np.array([2]))

  # step returns
  def step(self, action):
    # Execute one time step within the environment
    #round_start_timestamp = time.perf_counter()
    action_counter = 0
    obs = []
    reward = -.001
    done = False
    for agent in self.swarm_sim_world.agents:
      move = self.swarm_sim_world.grid.get_directions_list()[action]

      if move in self.get_valid_directions(agent):
        agent.move_to(move)


      action_counter += 1
      obs += agent.coordinates

      if agent.coordinates not in self.explored_points:
        self.explored_points.add(agent.coordinates)
        reward == 0.1


      #for each of the adjacent locations if there is an undiscovered item there add 1 to the reward and obs
      for direction in self.swarm_sim_world.grid.get_directions_list():
        adjacent_location_coords = self.swarm_sim_world.grid.get_coordinates_in_direction(agent.coordinates, direction)
        if adjacent_location_coords in self.swarm_sim_world.item_map_coordinates:

          obs += [1]

          if adjacent_location_coords not in self.discovered_items:
            self.discovered_items.add(adjacent_location_coords)
            reward += 1.0

            if len(self.discovered_items) >= len(self.swarm_sim_world.get_items_list()) or self.ts > 100:
              done = True

        else:
          obs += [0]



    self.ts += 1
    return np.array(obs), reward, done, {}


  #Currently returns all directions which point to coordinates on the map
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
        adjacent_location_coords = self.swarm_sim_world.grid.get_coordinates_in_direction(agent.coordinates, direction)
        if adjacent_location_coords in self.swarm_sim_world.item_map_coordinates:
          obs += [1]
          self.discovered_items.add(adjacent_location_coords)
        else:
          obs += [0]
      self.explored_points.add(agent.coordinates)

    return  np.array(obs)
  def render(self, mode='human', close=False):
    # Render the environment to the screen
    return
