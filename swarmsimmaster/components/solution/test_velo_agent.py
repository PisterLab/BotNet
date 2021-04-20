import numpy as np
def solution(world):
    if world.get_actual_round() % 1 == 0:
        for agent in world.get_agent_list():
            agent.set_velocities([np.random.random() for _ in range( world.grid.get_dimension_count())])
            agent.move()
