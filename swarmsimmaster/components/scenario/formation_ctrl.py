import numpy as np
import random
import math
import os

eps = 10e-8
max_speed = 0.1
conv_thres = 0.001

# Agent spawns
def scenario(world):
    swarm_size = world.config_data.num_agents
    for s in range(swarm_size):
        spawn = list(circle_spawn(swarm_size))
        spawn.append(0)
        world.add_agent(tuple(spawn))

def circle_spawn(swarm_size):
    density = 0.22
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    radius =  pow(swarm_size / (density * np.pi), 0.5)
    return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])


def log_data(world, data):
    np.save(os.path.join(world.config_data.directory_csv, "data"), data)

# move agent toward target
def move_toward(agent, target, thres=conv_thres):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec))
        return True
    return False

# enforce speed limit
def speed_limit(speed_vec):
    speed = np.linalg.norm(speed_vec)
    if speed > max_speed:
        return speed_vec / (speed + eps) * max_speed
    return speed_vec