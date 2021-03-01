def scenario(world, goons=None):
    if goons:
        for agent in goons:
            world.add_agent(agent)
    else:
        world.add_agent(world.grid.get_center())