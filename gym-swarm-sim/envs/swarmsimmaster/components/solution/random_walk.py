import random


def solution(world):

    if world.get_actual_round() % 1 == 0:
        for agent in world.get_agent_list():
            print(world.get_actual_round(), " Agent No.", agent.number)
            agent.move_to(random.choice(world.grid.get_directions_list()))
