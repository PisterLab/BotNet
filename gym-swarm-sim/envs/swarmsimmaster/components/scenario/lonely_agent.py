import numpy as np
from enum import Enum

def scenario(world, init_scenario="edge_line_flock"):
    seed, spacing, num_agents, follow = param_init(world.config_data)

    world.config_data.scenario_arg = init_scenario
    if init_scenario == "center_radius_flock":
        world.add_agent((0.0, 0.0))
        for i in range(num_agents):
            x, y = spacing * (np.random.rand(2) - 1)
            world.add_agent((x, y))
    elif init_scenario == "edge_radius_flock":
        for i in range(num_agents):
            # add agents along circumference
            theta = 2 * np.pi * float(i) / num_agents
            world.add_agent((spacing * np.cos(theta), spacing * np.sin(theta)))
    elif init_scenario == "center_line_flock":
        if follow:
            world.add_agent((0.0, 0.0))
        for i in range(1, num_agents // 2 + 1):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, spacing * float(i) + epsilon))

        for i in range(1, num_agents // 2 + 1):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, - spacing * float(i) + epsilon))
    elif init_scenario == "edge_line_flock":
        if follow:
            world.add_agent((0.0, spacing * float(num_agents // 2)))
        for i in range(num_agents // 2 + 1):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, spacing * float(i) + epsilon))

        for i in range(1, num_agents // 2 + 1):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, -spacing * float(i) + epsilon))

    # for agent in world.get_agent_list():
        # agent.set_velocities((2 * np.random.rand() - 2, 2 * np.random.rand() - 2, 0))

    # if radius: monte carlo! TODO

def param_init(config_data):
    try:
        seed = config_data.seed_value
    except:
        seed = 0

    np.random.rand(seed)

    try:
        spacing = config_data.spacing
    except:
        spacing = 1.0

    try:
        num_agents = config_data.num_agents
    except:
        num_agents = 10

    try:
        follow = config_data.follow
    except:
        follow = True

    return seed, spacing, num_agents, follow