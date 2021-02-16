
def scenario(world):
    world.add_agent((0.0 - 5,0.0))
    for i in range(10):
        world.add_agent((5.5 - i - 5, 5.5 - i))
