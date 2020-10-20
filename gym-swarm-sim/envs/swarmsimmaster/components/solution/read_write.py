"""
The agents are moving infront each other but in the different direction but whenever they meet each other
the start either to write to each other and then they give out the what it they received from each other.
"""


def solution(world):
    """
    All the magic starts from here

    :param world: The item instance of the world.py
    :param world: The item instance of the created world
    """
    # two_agent_inverse_walk(world)
    read_write(world)


def read_write(world):
    world.get_agent_list()[0].write_to_with(world.locations[0], "location", "test1")
    world.get_agent_list()[0].wrTFite_to_with(world.items[0], "item", "test2")
    world.get_agent_list()[0].write_to_with(world.get_agent_list()[1], "agent1", "test3")
    world.get_agent_list()[0].write_to_with(world.get_agent_list()[1], "agent2", "test4")
    world.get_agent_list()[0].write_to_with(world.get_agent_list()[1], "agent3", "test5")
    world.get_agent_list()[0].write_to_with(world.get_agent_list()[1], "agent4", "test6")
    loc_data = world.get_agent_list()[0].read_from_with(world.locations[0], "location")
    item_data = world.get_agent_list()[0].read_from_with(world.items[0], "item")
    if loc_data != 0:
        print(loc_data)
    if item_data != 0:
        print(item_data)
    for part_key in world.get_agent_list()[1].read_whole_memory():
        print(world.get_agent_list()[1].read_whole_memory()[part_key])


