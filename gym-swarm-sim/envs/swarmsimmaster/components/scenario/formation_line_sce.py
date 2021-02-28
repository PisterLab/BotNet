import numpy as np
import random

def scenario(world):
    swarm_size = world.config_data.num_agents
    center = world.grid.get_center()


    for s in range(swarm_size):
        # spawn = (np.random.random(size=(3)) * 2 - 1) + center
        # spawn[2] = 0
        spawn = list(circle_spawn(swarm_size))
        spawn.append(0)
        world.add_agent(tuple(spawn))

    # swarm_size = 10
    # center = world.grid.get_center()
    # dirs = world.grid.get_directions_list()
    # world.add_agent((0.75, 1, 0))
    # m, c = -1, 5
    #
    # for x in range(swarm_size - 1):
    #     x = (x - 5)
    #     y = m * x + c + (np.random.random() - 0.5)
    #     world.add_agent(tuple([x, y, 0]))
    #     print(x, y)

def circle_spawn(swarm_size):
    density = 0.22
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    radius =  pow(swarm_size / (density * np.pi), 0.5)
    return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])