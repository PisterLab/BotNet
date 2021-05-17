import numpy as np
import math
def scenario(world, num_agents=1, spacing = 2.0):
	world.add_agent(0,0)
	np.random.seed(world.config_data.seed_value)
	for i in range(0, num_agents - 1):
		epsilon = (np.random.rand() - .5) / 2
		world.add_agent((0.0, ((spacing * float((i//2 + 1)) + epsilon) * math.pow(-1, i)) ))