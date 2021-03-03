import pandas as pd
import numpy as np

DEFAULT_NUM_AGENTS = 10

def scenario(world, goons=None, id="custom", scenario="basic", num_agents=DEFAULT_NUM_AGENTS, seed=122, comms="full", flock_rad=20, flock_vel=5):
    replication_file = f"./outputs/csv/{id}/{scenario}/{num_agents}/{seed}/{comms}-{flock_rad}-{flock_vel}-pos.dat"

    # add all the agents with a mapping
    dfp = pd.read_csv(replication_file, sep=',', header=None)

    fp = np.array([np.fromstring(p[0], dtype=float, sep=" ") for p in dfp.values])

    positions = np.reshape(fp, (-1, num_agents, 3)) # [:, :, :2] # for 2D coords

    # TODO: assert that position data is > 0 in length (see positions.shape[0])

    world.replication_data = positions
    for i in range(num_agents):
        world.add_agent(tuple(positions[0][i]))