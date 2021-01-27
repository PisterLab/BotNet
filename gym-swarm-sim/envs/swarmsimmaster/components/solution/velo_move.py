import random

def solution(world):

    if world.get_actual_round() % 1 == 0:
        for agent in world.get_agent_list():
            agent.move()