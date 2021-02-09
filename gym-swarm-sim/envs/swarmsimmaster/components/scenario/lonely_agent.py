
def scenario(world):
    world.add_agent((0.0,)*world.grid.get_dimension_count())
    for i in range(10):
        world.add_agent((5.5 - i,)*world.grid.get_dimension_count())
