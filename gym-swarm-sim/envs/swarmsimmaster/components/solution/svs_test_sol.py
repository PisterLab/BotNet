import numpy as np
import time

eps = 10e-8
max_speed = 0.1
r = 10
terminated = False

def solution(world):
    global terminated

    agents = world.get_agent_list()

    bot1 = agents[0]
    bot2 = agents[1]
    jitter(bot1)
    jitter(bot2)

    comms_line = world.get_agent_list()[2:]
    for c in comms_line:
        world.remove_agent_on(c.coordinates)

    new_c = (np.array(bot1.color) + np.array(bot2.color)) / 2
    new_c[3] = 0.4
    comms_x = np.arange(bot1.coordinates[0], bot2.coordinates[0])
    m = (bot1.coordinates[1] - bot2.coordinates[1]) / (bot1.coordinates[0] - bot2.coordinates[0])
    b = bot1.coordinates[1] - m * bot1.coordinates[0]
    # y = mx + b
    # b = y - mx
    comms_y = m * comms_x + b
    for x, y in zip(comms_x[1:-1], comms_y[1:-1]):
        world.add_agent((x, y, 0), color=new_c)


# random jittering
def jitter(agent):
    target = (np.random.random(size=3) - 0.5) * 10

    target[2] = 0
    target += agent.coordinates
    move_toward(agent, target)

####################################################
# move agent toward target
def move_toward(agent, target, thres=0.001):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec))
        return True
    return False

# move agent within [min_dist, max_dist] from target, where target = [x, y, z]
def move_threshold(agent, target, min_dist, max_dist):
    n_vec = np.array(agent.coordinates) - target
    n_dist = np.linalg.norm(n_vec)

    if n_dist > max_dist:
        nn_target = n_vec / (n_dist + eps) * max_dist + target
        return move_toward(agent, nn_target)

    if n_dist < min_dist:
        nn_target = n_vec / (n_dist + eps) * min_dist + target
        return move_toward(agent, nn_target)

    return False

# move agent within [min_dist, max_dist] from x, y
def move_threshold_xy(agent, x, y, min_dist, max_dist):
    target = np.array([x, y, 0])
    return move_threshold(agent, target, min_dist, max_dist)

# move agent to within [min_dist, max_dist] from agent2
def move_threshold_agent(agent, agent2, min_dist, max_dist):
    target = agent2.coordinates
    return move_threshold(agent, target, min_dist, max_dist)

# enforce speed limit
def speed_limit(speed_vec):
    speed = np.linalg.norm(speed_vec)
    if speed > max_speed:
        return speed_vec / (speed + eps) * max_speed
    return speed_vec

# helper for timestep
def timestep(world):
    return world.get_actual_round()
