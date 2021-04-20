
def scenario(world):

    item_ring = world.grid.get_n_sphere_border((0, 0, 0), 2)
    for agent in item_ring:
        world.add_item(agent)

    agent_ring = world.grid.get_n_sphere_border((0, 0, 0), 4)
    for agent in agent_ring:
        world.add_agent(agent)
