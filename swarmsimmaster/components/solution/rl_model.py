from stable_baselines3 import PPO
from stable_baselines3.ppo import MlpPolicy
import numpy as np

def solution(world):
    model = PPO.load("models/ppo_search")
    for agent in world.get_agent_list():
        #construct the observation
        obs = list(agent.coordinates)

        for direction in world.grid.get_directions_list():
            adjacent_location_coords = world.grid.get_coordinates_in_direction(agent.coordinates,
                                                                                              direction)
            if adjacent_location_coords in world.item_map_coordinates:
                obs += [1]

            else:
                obs += [0]


        agent.move_to(world.grid.get_directions_list()[model.predict(np.array(obs))[0]])



