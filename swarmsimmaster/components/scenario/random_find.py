#from lib.swarm_sim_header import get_multiple_steps_in_direction, get_coordinates_in_direction
import random
def scenario(world):
    world.add_agent((0.0, 0.0, 0.0))
    world.add_item((random.randrange(-5,5), random.randrange(-5,5), random.randrange(-5,5)))
    world.add_item((random.randrange(-5,5), random.randrange(-5,5), random.randrange(-5,5)))
    world.add_item((random.randrange(-5,5), random.randrange(-5,5), random.randrange(-5,5)))

    world.add_item((random.randrange(-5, 5), random.randrange(-5, 5), random.randrange(-5, 5)))
    world.add_item((random.randrange(-5, 5), random.randrange(-5, 5), random.randrange(-5, 5)))
    world.add_item((random.randrange(-5, 5), random.randrange(-5, 5), random.randrange(-5, 5)))
