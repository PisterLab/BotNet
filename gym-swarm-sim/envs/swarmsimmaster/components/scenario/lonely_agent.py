import numpy as np
from enum import Enum


NUM_AGENTS = 20
SPACING = 3.0

def scenario(world, init_scenario="edge_line_flock"):
    # np.random.rand(world.seed) # TODO: get this from config somehow? configdata param or something

    if init_scenario == "center_radius_flock":
        world.add_agent((0.0, 0.0))
        for i in range(NUM_AGENTS):
            x, y = SPACING * NUM_AGENTS * (np.random.rand(2) - 1)
            world.add_agent((x, y))
    elif init_scenario == "center_line_flock":
        world.add_agent((0.0, 0.0))
        for i in range(1,12,2):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, SPACING * float(i) + epsilon))

        for i in range(1,12,2):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, - SPACING * float(i) + epsilon))
    elif init_scenario == "edge_line_flock":
        world.add_agent((0.0, SPACING * float(NUM_AGENTS // 2)))
        for i in range(0, NUM_AGENTS // 2 - 1,2):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, SPACING * float(i) + epsilon))

        for i in range(1, NUM_AGENTS // 2,2):
            epsilon = (np.random.rand() - .5) / 2
            world.add_agent((0.0, -SPACING * float(i) + epsilon))

    # if radius: monte carlo! TODO