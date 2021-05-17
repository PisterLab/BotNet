import numpy as np
def scenario(world, num_agents=1, spacing = 2.0):

    np.random.seed(world.config_data.seed_value)
    for i in range(num_agents):
        # add agents along circumference
        theta = 2 * np.pi * float(i) / num_agents
        world.add_agent((spacing * np.cos(theta), spacing * np.sin(theta)))