import numpy as np
import random

def scenario(world):
    swarm_size = 100
    center = world.grid.get_center()


    for s in range(swarm_size):
        # spawn = (np.random.random(size=(3)) * 2 - 1) + center
        # spawn[2] = 0
        spawn = list(circle_spawn())
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

def circle_spawn():
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    return np.array([r * np.cos(t) * 12, r * np.sin(t) * 12])