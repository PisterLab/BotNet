import numpy as np
from communication import communication_model
import time
import os
start_time = None
timesteps = 0
logged = False

def solution(world):
    global start_time, timesteps, logged

    if not world.network_formed:
        start_time = None
        return

    if not start_time:
        start_time = time.time()
        timesteps = 0
    elif timesteps == world.config_data.max_round:
        end_timer(world)
        timesteps += 1
    elif timesteps < world.config_data.max_round:
        timesteps += 1
        for a in world.get_agent_list():
            a.neighbors.values()
            jitter(a)
    else:
        timesteps += 1

def jitter(agent):
    target = (np.random.random(size=3) - 0.5) * 5
    target[2] = 0
    agent.move_to(target)

def end_timer(world):
    global start_time
    total_time = time.time() - start_time
    np.save(os.path.join(world.config_data.directory_csv, "data"), [total_time])
    print("=======", world.config_data.num_agents, total_time)