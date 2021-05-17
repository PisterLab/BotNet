import numpy as np
def scenario(world, num_agents=1, spacing = 2.0):

     np.random.seed(world.config_data.seed_value)
     robotCoords.append((spacing * 1.1,
                                0.0))              
     for i in range(num_agents - 1):
        x, y = 2 * spacing * (np.random.rand(2) - .5)
        world.add_agent(x, y)

