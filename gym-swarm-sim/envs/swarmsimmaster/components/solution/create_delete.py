"""
This solution is an example for creating and deleting, agents, items or locations
"""
from core.swarm_sim_header import *


def solution(world):

    dirs = world.grid.get_directions_list()
    center = world.grid.get_center()

    if world.get_actual_round() == 1:
        for agent in world.get_agent_list():
            print("World started")
            agent.create_item_in(dirs[0])
            agent.create_location_in(dirs[1])

    if world.get_actual_round() == 2:
        if len(world.get_agent_list()) > 0:
            world.get_agent_list()[0].create_agent_in(dirs[1])
            world.get_agent_list()[0].create_agent_in(dirs[1])

    if world.get_actual_round() == 3:
        if len(world.get_agent_list()) > 0:
            world.get_agent_list()[0].take_agent_in(dirs[1])
            world.get_agent_list()[0].delete_agent_in(dirs[1])
            world.get_agent_list()[0].delete_item_in(dirs[0])

    if world.get_actual_round() == 4:
        pos = get_coordinates_in_direction(center, dirs[2])
        world.get_agent_list()[0].create_item_on(pos)
        world.get_agent_list()[0].create_location_on(pos)

    if world.get_actual_round() == 5:
        pos = get_coordinates_in_direction(center, dirs[2])
        world.get_agent_list()[0].delete_item_on(pos)

    if world.get_actual_round() == 6:
        pos1 = get_coordinates_in_direction(center, dirs[2])
        pos2 = get_coordinates_in_direction(center, dirs[3])
        world.get_agent_list()[0].create_agent_on(pos2)
        world.get_agent_list()[0].delete_location_on(pos1)

    if world.get_actual_round() == 7:
        pos2 = get_coordinates_in_direction(center, dirs[3])
        world.get_agent_list()[0].delete_agent_on(pos2)

    if world.get_actual_round() == 8:
        world.get_agent_list()[0].create_item()
        world.get_agent_list()[0].create_location()

    if world.get_actual_round() == 9:
        world.get_agent_list()[0].delete_item()

    if world.get_actual_round() == 12:
        world.get_agent_list()[0].create_agent()

    if world.get_actual_round() == 15:
        world.get_agent_list()[0].delete_agent()
        world.get_agent_list()[0].delete_location()
