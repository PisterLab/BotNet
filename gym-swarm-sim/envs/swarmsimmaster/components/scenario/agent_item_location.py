"""
A world is created that has two particles, two markers, and two tiles.
"""
from lib.swarm_sim_header import get_multiple_steps_in_direction, get_coordinates_in_direction


def scenario(world):
    world.add_agent((0.0,0.0,0.0))
    world.add_item((1.0,0.0,0.0))
    world.add_location((2.0,0.0,0.0))
