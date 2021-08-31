import numpy as np
import random
def scenario(world):
    swarm_size = int(world.config_data.num_agents)
    for s in range(swarm_size):
        spawn = list(np.random.random(size=2) * 10)
        spawn.append(0)
        world.add_agent(tuple(spawn))