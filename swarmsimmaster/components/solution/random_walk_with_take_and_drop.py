import random


def solution(world):

    for agent in world.agents:
        items = agent.scan_for_matters_in(matter_type="item")
        agent.drop_item_in(random.choice(world.grid.get_directions_list()))
        if len(items) > 0:
            agent.take_item_with(items[0].get_id())
        agent.move_to(random.choice(world.grid.get_directions_list()))
