import numpy as np
import random

def scenario(world):
    swarm_size = world.config_data.num_agents
    #world.add_location((0, 0, 0), [0, 0, 255, 1])

    swarm_a_center = (-10, 0, 0)
    swarm_b_center = (10, 0, 0)

    world.add_agent(swarm_a_center)
    world.add_agent(swarm_b_center)
    agents = world.get_agent_list()
    [k.set_color([0, 0, 255, 1]) for k in agents[:len(agents) // 2]]


    # swarm_a_center = [-10, 0]
    # swarm_b_center = [10, 0]
    # #center = world.grid.get_center()
    #
    # for s in range(swarm_size // 2):
    #     spawn = list(circle_spawn(swarm_size) + swarm_a_center)
    #     spawn.append(0)
    #     world.add_agent(tuple(spawn))
    #
    # for s in range(swarm_size // 2):
    #     spawn = list(circle_spawn(swarm_size) + swarm_b_center)
    #     spawn.append(0)
    #     world.add_agent(tuple(spawn))
    #
    # agents = world.get_agent_list()
    # #[k.set_color([0, 0, 255, 1]) for k in agents[:len(agents) // 2]]
    #
    # world.add_location((1, 1, 0), [0, 0, 255, 1])
    # world.add_item((1, 0, 0), [0, 255, 0, 1])

def circle_spawn(swarm_size):
    density = 0.22
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    radius =  pow(swarm_size / (density * np.pi), 0.5)
    return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])