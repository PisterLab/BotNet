import pandas as pd

def scenario(world, replication_file=None):
    # add all the agents with a mapping
    world.replication_data = pd.read_csv(replication_file)
    for agent_id in world.replication_data.columns:
        world.add_agent(world.grid.get_center()) # TODO: seems like just a dummy init I guess?? should probably look at timestep 0 positions