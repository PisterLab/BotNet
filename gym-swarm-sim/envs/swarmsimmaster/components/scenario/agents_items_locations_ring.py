"""
A world is created that has agents formated in a ring structure that is up to 5 hops big
"""


def scenario(world):

    world.add_agent(world.grid.get_center())

    agent_ring = world.grid.get_n_sphere_border((0, 0, 0), 1)
    item_ring = world.grid.get_n_sphere_border((0, 0, 0), 3)
    location_ring = world.grid.get_n_sphere_border((0, 0, 0), 5)

    for agent in agent_ring:
        world.add_agent(agent)

    for item in item_ring:
        world.add_item(item)

    for location in location_ring:
        world.add_location(location)
