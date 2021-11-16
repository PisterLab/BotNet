import gym
from gym import spaces
from core import world, config
import swarmsim
import logging
import numpy as np
import torch

class SwarmEnv(gym.Env):
  """
    Description:
        Swarm

    Observation:
        Type: Box(N, 2)
        Num     Observation         Min X   Max X   Min Y   Max Y
        0       Agent 0 Position    -40     40      -40     40   
        1       Agent 1 Position    -40     40      -40     40   
        ...     ...                 ...     ...     ...     ...  
        N       Agent N Position    -40     40      -40     40   

    Actions:
        Type: Discrete(N, 2)
        Num   Action
        0     Push cart to the left
        1     Push cart to the right

        Note: The amount the velocity that is reduced or increased is not
        fixed; it depends on the angle the pole is pointing. This is because
        the center of gravity of the pole increases the amount of energy needed
        to move the cart underneath it

    Reward:
        Reward is 1 for every step taken, including the termination step

    Starting State:
        All agents spawn in random positions.

    Episode Termination:
        Pole Angle is more than 12 degrees.
        Cart Position is more than 2.4 (center of the cart reaches the edge of
        the display).
        Episode length is greater than 200.
        Solved Requirements:
        Considered solved when the average return is greater than or equal to
        195.0 over 100 consecutive trials.
    """
  defense_clr = [0, 0, 255, 1]
  offense_clr = [255, 0, 0, 1]
  action_space = None
  observation_space = None

  def __init__(self):
    super(SwarmEnv, self).__init__()
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
    self.SCENARIO = swarmsim.get_scenario(config_data)

    self.t = 0 # timestep
    self.swarm_sim_world.init_scenario(self.SCENARIO)
    self.offense_drones = self.get_drones(self.swarm_sim_world, clr=self.offense_clr)
    self.defense_drones = self.get_drones(self.swarm_sim_world, clr=self.defense_clr)
    self.NUM_AGENTS = self.swarm_sim_world.get_amount_of_agents()
    self.DEFENSE_CENTER = [-10, 0, 0]

    # each agent may move UP, DOWN, LEFT, RIGHT
    self.action_space = spaces.MultiDiscrete(np.full_like(self.NUM_AGENTS, 4)) # xy motion

    obs_spaces = {
      "offense": spaces.Box(low=-40, high=40, shape=(len(self.offense_drones), 3)), # xyz coords
      "defense": spaces.Box(low=-40, high=40, shape=(len(self.defense_drones), 3)), # xyz coords
    }
    #observation of the coordinates of each agent
    self.observation_space = spaces.Dict(obs_spaces)

  def step(self, action):
    # Execute one time step within the environment
    action_counter = 0
    obs = {
      "offense": [],
      "defense": []
    }
    reward = 0
    done = False

    # Attackers move
    for i in range(len(action)):
      agent = self.offense_drones[i]
      if (not agent.alive):
        continue

      move = self.swarm_sim_world.grid.get_directions_list()[action[i]]
      if move in self.get_valid_directions(agent):
        agent.move_to(self.speed_limit(move))
      
      action_counter += 1
      obs["offense"].append(agent.coordinates)
      dist_from_goal = np.linalg.norm(np.array(agent.coordinates) - np.array(self.DEFENSE_CENTER))
      if dist_from_goal < 0.1:
        reward += 1
        done = True
        break
      else:
        reward += 2 - dist_from_goal

    if not done:
      sorted_offense = sorted(self.offense_drones, key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(self.DEFENSE_CENTER)))
      closest_offense = sorted_offense[0]
      for agent in self.defense_drones:
        if (agent.alive):
          self.move_toward(agent, closest_offense.coordinates)
      obs["defense"].append(agent.coordinates)

    # Offense death check
    if not done:
      # death check for offense
      for agent in self.offense_drones:
        sorted_defense = sorted(self.defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(agent.coordinates)))
        if (agent.alive):
          closest_defense = sorted_defense[0]
          # check if dead
          if np.linalg.norm(np.array(closest_defense.coordinates) - np.array(agent.coordinates)) < 0.1:
              agent.alive = False
              agent.update_agent_coordinates(agent, (100, 100, 0))
    
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
    self.swarm_sim_world.reset()
    self.swarm_sim_world.init_scenario(self.SCENARIO)
    self.ts = 0
    obs = []
    for agent in self.swarm_sim_world.agents:
      obs += agent.coordinates
    return np.array(obs)
  
  def render(self, mode='human', close=False):
    # Render the environment to the screen
    pass

  # HELPER FUNCTIONS
  def get_drones(self, world, clr):
    lst = []
    for a in world.get_agent_list():
        if a.color == clr and a.alive:
            lst.append(a)
    return lst

  # move agent toward target
  def move_toward(self, agent, target, thres=0.001):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(self.speed_limit(vec, agent))
        return True
    return False

  # enforce speed limit
  def speed_limit(self, speed_vec, agent):
    speed = np.linalg.norm(speed_vec)
    if agent.color == self.defense_clr:
        max_speed = 0.1
    else:
        max_speed = 0.1

    if speed > max_speed:
        return speed_vec / (speed + 10e-8) * max_speed
    return speed_vec

def termination_fn(act: torch.Tensor, next_obs: torch.Tensor) -> torch.Tensor:
  return 