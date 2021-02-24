import numpy as np
import random

def scenario(world):
    swarm_size = 10
    center = world.grid.get_center()
    dirs = world.grid.get_directions_list()

    for s in range(swarm_size):
        spawn = (np.random.random(size=(3)) * 2 - 1) + center
        spawn[2] = 0
        world.add_agent(tuple(spawn.tolist()))


