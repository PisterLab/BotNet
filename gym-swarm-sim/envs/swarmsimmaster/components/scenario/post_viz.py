import pandas as pd
import numpy as np

DEFAULT_FILE = "./outputs/csv/custom/basic/3/122/full-20-5-pos.dat"
DEFAULT_NUM_AGENTS = 3

def scenario(world, replication_file=DEFAULT_FILE, num_agents=DEFAULT_NUM_AGENTS):
    # add all the agents with a mapping
    dfp = pd.read_csv(replication_file, sep=',', header=None)

    fp = np.array([np.fromstring(p[0], dtype=float, sep=" ") for p in dfp.values])

    positions = np.reshape(fp, (-1, num_agents, 3)) # [:, :, :2] # for 2D coords

    world.replication_data = positions
    for i in range(num_agents):
        world.add_agent(tuple(positions[0][i])) # TODO: seems like just a dummy init I guess?? should probably look at timestep 0 positions