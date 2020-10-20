import gym
from gym import spaces
from core import world, config
import swarmsim
import logging
import numpy as np
import time

class SwarmSimEnvSingle(gym.Env):
  """Custom Environment that follows gym interface"""
  def __init__(self):
    super(SwarmSimEnvSingle, self).__init__()
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

    self.swarm_sim_world.init_scenario(swarmsim.get_scenario(config_data))
    #self.NUM_AGENTS = self.swarm_sim_world.get_amount_of_agents()
    #each agent can move one of 9 ways, with
    #self.action_space = spaces.MultiDiscrete(np.full_like(self.NUM_AGENTS, 9)) # xyz motion
    self.action_space = spaces.Discrete(len(self.swarm_sim_world.grid.get_directions_list()))

    #observation of the coordinates of each agent
    #TODO:: Redo observation space to not be hardcoded/box shaped
    self.observation_space = spaces.Box(np.array([-9999, -9999, -9999]), np.array([9999, 9999, 9999]))
    #self.observation_space = spaces.Box(np.array([1]), np.array([2]))
  # step returns
  def step(self, action):
    # Execute one time step within the environment
    #round_start_timestamp = time.perf_counter()
    action_counter = 0
    obs = []
    for agent in self.swarm_sim_world.agents:


      agent.move_to(self.swarm_sim_world.grid.get_directions_list()[action])
      action_counter += 1
      obs += agent.coordinates




    # return bare minimum
    print(obs)
    return obs, 1, False, {}



  def reset(self):
    # Reset the state of the environment to an initial state
    swarmsim.do_reset(self.swarm_sim_world)
    ...
  def render(self, mode='human', close=False):
    # Render the environment to the screen
    return
