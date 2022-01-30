import gym
from gym import spaces
from core import world, config
import swarmsim
import logging
import numpy as np
import torch

class SwarmEnv(gym.Env):
  defense_clr = [0, 0, 255, 1]
  offense_clr = [255, 0, 0, 1]
  DEFENSE_CENTER = [-10, 0, 0]
  action_space = None
  observation_space = None

  def __init__(self):
    super(SwarmEnv, self).__init__()
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
    self.action_space = spaces.MultiDiscrete([4] * len(self.offense_drones))
    # self.action_space = spaces.Box(low=0, high=3.99, shape=(len(self.offense_drones),))
    
    # XY of defenders, XY of attackers, XY of defense goal, timestep
    self.obs_size = self.NUM_AGENTS * 2 + 3
    self.observation_space = spaces.Box(low=-40, high=40, shape=(self.obs_size,))

  def step(self, action):
    obs = np.zeros(self.obs_size)
    obs_i = 0
    reward = 0
    done = False
    print(action)
    # if (not isinstance(action, int)):
    #   action = int(np.rint(action.squeeze()))

    # Defenders move
    sorted_offense = sorted(self.offense_drones,
                            key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(self.DEFENSE_CENTER)))
    for a in self.defense_drones:
        closest_offense = sorted_offense[0]
        self.move_toward(a, closest_offense.coordinates)
        obs[obs_i:obs_i + 2] = a.coordinates[0:2]
        obs_i += 2

    # death check for offense
    for a in self.offense_drones:
        sorted_defense = sorted(self.defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(a.coordinates)))
        closest_defense = sorted_defense[0]
        # check if dead
        if np.linalg.norm(np.array(closest_defense.coordinates) - np.array(a.coordinates)) < 0.1:
            a.alive = False
            a.update_agent_coordinates(a, (100, 100, 0))
            reward -= 5

    if not list(filter(lambda e: e.alive, self.offense_drones)):
      reward -= 100
      done = True

    # Attackers move
    for i in range(len(self.offense_drones)):
      agent = self.offense_drones[i]
      move = self.WORLD.grid.get_directions_list()[action[i]]
      if not agent.alive:
        obs[obs_i:obs_i + 2] = agent.coordinates[0:2]
        obs_i += 2
        continue
      agent.move_to(self.speed_limit(move, agent))
      obs[obs_i:obs_i + 2] = agent.coordinates[0:2]
      obs_i += 2
      dist_from_goal = np.linalg.norm(np.array(agent.coordinates) - np.array(self.DEFENSE_CENTER))
      if dist_from_goal < 0.1:
        reward += 100
        done = True
      else:
        # def_dist = np.linalg.norm(np.array(agent.coordinates) - np.array(defender.coordinates))
        # if (def_dist < 1):
        #   reward -= def_dist
        reward += (1 - dist_from_goal) / 100

    # agent = self.offense_drones[0]
    # defender = self.defense_drones[0]
    # move = self.WORLD.grid.get_directions_list()[action]
    # agent.move_to(self.speed_limit(move, agent))
    # print(agent.coordinates)
    # dist_from_goal = np.linalg.norm(np.array(agent.coordinates) - np.array(self.DEFENSE_CENTER))
    # if dist_from_goal < 0.1:
    #   reward += 100
    #   done = True
    # elif dist_from_goal > 40:
    #   reward = 0
    #   done = True
    #   return obs, reward, done, {}
    # else:
    #   def_dist = np.linalg.norm(np.array(agent.coordinates) - np.array(defender.coordinates))
    #   if (def_dist < 1):
    #     reward -= def_dist
    #   reward += (1 - dist_from_goal) / 100
    
    # obs[0:3] = agent.coordinates
    # obs[3:6] = defender.coordinates
    # obs[6:9] = self.DEFENSE_CENTER

    obs[obs_i:obs_i + 2] = self.DEFENSE_CENTER[0:2]
    self.ts += 1
    obs[-1] = self.ts
    print(obs)
    if (self.ts > 750):
      done = True
    return obs, reward, done, {}

  def reset(self):
    # Reset the state of the environment to an initial state
    self.WORLD.reset()
    self.WORLD.init_scenario(self.SCENARIO)
    self.ts = 0
    obs = []
    self.offense_drones = self.get_drones(self.WORLD, clr=self.offense_clr)
    self.defense_drones = self.get_drones(self.WORLD, clr=self.defense_clr)
    for agent in self.defense_drones:
      obs.extend(agent.coordinates[0:2])
    for agent in self.offense_drones:
      obs.extend(agent.coordinates[0:2])
  
    obs.extend(self.DEFENSE_CENTER[0:2])
    obs.append(self.ts)
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
  print(next_obs)
  offense = next_obs[:, 0:2]
  distance = torch.linalg.norm(offense - torch.tensor([-10, 0], device='cuda:0'), dim=1)
  done = torch.logical_or(torch.linalg.norm(offense, dim=1) > 40, distance < 0.1)
  return done.view(-1, 1)

def reward_fn(act: torch.Tensor, next_obs: torch.Tensor) -> torch.Tensor:
  print(next_obs)
  offense = next_obs[:, 0:2]
  # print(offense)
  distance = torch.linalg.norm(offense - torch.tensor([-10, 0], device='cuda:0'), dim=1)
  return (1 - distance.view(-1, 1)) / 100 + (distance.view(-1, 1) < 0.1).float()
  # if (distance < 0.1):
  #   return 1
  # else:
  #   return (1 - distance)/10