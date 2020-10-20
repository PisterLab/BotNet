from core.swarm_sim_header import *
import random


def scenario(world):
    amount = 5
    direction = random.choice(world.grid.get_directions_list())
    create_matter_in_line(world, world.grid.get_center(), direction, amount, MatterType.AGENT)
