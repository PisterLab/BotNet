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
        Type: Dict{Attackers: Box(N, 3), Defenders: Box(N, 3)}
        
        For each box space:
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
  DEFENSE_CENTER = [-10, 0, 0]
  action_space = None
  observation_space = None

  def __init__(self):
    super(SwarmEnv, self).__init__()
    # Define action and observation space
    # They must be gym.spaces objects
    # Example when using discrete actions:
    ##may need to alter configdata to be closer to fit our needs.
    config_data = config.ConfigData()
    config_data.visualization = False
    unique_descriptor = "%s_%s_%s" % (config_data.local_time,
                                      config_data.scenario.rsplit('.', 1)[0],
                                      config_data.solution.rsplit('.', 1)[0])

    logging.basicConfig(filename="outputs/logs/system_%s.log" % unique_descriptor, filemode='w',
                        level=logging.INFO, format='%(message)s')
    logging.info('Started')
    swarmsim.read_cmd_args(config_data)
    swarmsim.create_directory_for_data(config_data, unique_descriptor)
    swarmsim.random.seed(config_data.seed_value)
    self.WORLD = world.World(config_data)
    self.SCENARIO = swarmsim.get_scenario(config_data)

    self.ts = 0 # timestep
    self.WORLD.init_scenario(self.SCENARIO)
    self.offense_drones = self.get_drones(self.WORLD, clr=self.offense_clr)
    self.defense_drones = self.get_drones(self.WORLD, clr=self.defense_clr)
    self.NUM_AGENTS = self.WORLD.get_amount_of_agents()

    # each agent may move UP, DOWN, LEFT, RIGHT
    # self.action_space = spaces.MultiDiscrete(np.full_like(self.NUM_AGENTS, 4)) # xy motion
    self.action_space = spaces.Discrete(4)
    
    # The coordinates of each agent
    self.observation_space = spaces.Box(low=-40, high=40, shape=(7,))

  def step(self, action):
    # Execute one time step within the environment
    obs = np.zeros(7)
    reward = 0
    done = False

    if (not isinstance(action, int)):
      action = int(np.rint(action.squeeze()))

    # Attackers move
    agent = self.offense_drones[0]
    move = self.WORLD.grid.get_directions_list()[action]
    agent.move_to(self.speed_limit(move, agent))
    print(agent.coordinates)
    dist_from_goal = np.linalg.norm(np.array(agent.coordinates) - np.array(self.DEFENSE_CENTER))
    if dist_from_goal < 0.5:
      reward += 100
      done = True
    elif dist_from_goal > 40:
      reward = 0
      done = True
      return obs, reward, done, {}
    else:
      reward += (1 - dist_from_goal) / 100
    # obs["offense"].append(agent.coordinates)
    obs[0:3] = agent.coordinates

    # if not done:
    #   sorted_offense = sorted(self.offense_drones, key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(self.DEFENSE_CENTER)))
    #   closest_offense = sorted_offense[0]
    #   for agent in self.defense_drones:
    #     if (agent.alive):
    #       self.move_toward(agent, closest_offense.coordinates)
    agent = self.defense_drones[0]
    obs[3:6] = agent.coordinates

    # Offense death check
    if not done:
      # death check for offense
      for agent in self.offense_drones:
        sorted_defense = sorted(self.defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(agent.coordinates)))
        closest_defense = sorted_defense[0]
        # check if dead
        if np.linalg.norm(np.array(closest_defense.coordinates) - np.array(agent.coordinates)) < 0.1:
          done = True
          reward -= 100
    
    self.ts += 1
    obs[6] = self.ts
    if (self.ts > 500):
      done = True
    return obs, reward, done, {}

  def reset(self):
    # Reset the state of the environment to an initial state
    self.WORLD.reset()
    self.WORLD.init_scenario(self.SCENARIO)
    self.ts = 0
    obs = np.zeros(7)
    # for agent in self.WORLD.agents:
    #   obs += agent.coordinates
    self.offense_drones = self.get_drones(self.WORLD, clr=self.offense_clr)
    self.defense_drones = self.get_drones(self.WORLD, clr=self.defense_clr)
    obs[0:3] = self.offense_drones[0].coordinates
    obs[3:6] = self.defense_drones[0].coordinates
    return obs
  
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
  # print(next_obs)
  offense = next_obs[:, 0:3]
  distance = torch.linalg.norm(offense - torch.tensor([-10, 0, 0], device='cuda:0'), dim=1)
  done = torch.logical_or(torch.linalg.norm(offense, dim=1) > 40, distance < 0.1)
  return done.view(-1, 1)

def reward_fn(act: torch.Tensor, next_obs: torch.Tensor) -> torch.Tensor:
  # print(next_obs)
  offense = next_obs[:, 0:3]
  # print(offense)
  distance = torch.linalg.norm(offense - torch.tensor([-10, 0, 0], device='cuda:0'), dim=1)
  return (1 - distance.view(-1, 1)) / 100 + (distance.view(-1, 1) < 0.1).float()
  # if (distance < 0.1):
  #   return 1
  # else:
  #   return (1 - distance)/10