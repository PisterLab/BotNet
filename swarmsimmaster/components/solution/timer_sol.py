import numpy as np
import time
import os
start_time = None
end_time = None

def solution(world):
    global start_time, end_time
    comms = world.config_data.comms_model
    if timestep(world) == 1:
        start_time = None
        start_timer(world)
    elif timestep(world) >= world.config_data.max_round:
        end_timer(world)

    for a in world.get_agent_list():
        assert isinstance(a.neighbors, list)
        jitter(a)
    # else:
    #     for a in world.get_agent_list():
    #         x1, y1 = a.coordinates[0], a.coordinates[1]
    #         for b in world.get_agent_list():
    #             if a != b:
    #                 x2, y2 = b.coordinates[0], b.coordinates[1]
    #                 communication_model(x1, y1, x2, y2, comms_model=comms)
    #         jitter(a)

def timestep(world):
    return world.get_actual_round()

def jitter(agent):
    target = (np.random.random(size=3) - 0.5) * 5
    target[2] = 0
    agent.move_to(target)

def start_timer(world):
    global start_time
    start_time = time.time()

def end_timer(world):
    global start_time
    total_time = time.time() - start_time
    np.save(os.path.join(world.config_data.directory_csv, "data"), [total_time])
    print(world.config_data.num_agents, total_time)