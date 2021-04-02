import numpy as np
from communication import communication_model
import csv
import time

eps = 10e-8
max_speed = 0.1
saved = False
comms_model = "full"

def solution(world):
    global saved

    if timestep(world) == 1:
        saved = False

    comms_model = world.config_data.comms_model

    min_dist = 0.001
    max_dist = 0.002
    agents = world.get_agent_list()

    moved = []
    for i, agent in enumerate(agents):
        neighbors = connected_neighbors(world, agent, comms_model)
        x, y, k = lstsq(world, agent, neighbors)
        m, c = k[0]
        x1, y1 = x[0], y[0]
        x_target = (x1 / m + y1 - c) / (m + 1/m)
        y_target = m * x_target + c
        moved.append(move_threshold_xy(agent, x_target, y_target, min_dist, max_dist))

    if not any(moved) and not saved:
        benchmark(world)
        saved = True

def lstsq(world, agent, neighbors):
    x = [agent.coordinates[0]]
    y = [agent.coordinates[1]]

    for n in neighbors:
        x.append(n.coordinates[0])
        y.append(n.coordinates[1])

    x, y = np.array(x), np.array(y)
    A = np.vstack([x, np.ones(len(x))]).T
    return x, y, np.linalg.lstsq(A, y, rcond=None)

def benchmark(world):
    convergence_time = timestep(world)
    residuals = lstsq(world, world.get_agent_list()[0], world.get_agent_list()[1:])[2][1][0]
    data = np.array([convergence_time, residuals])
    np.save(world.config_data.data_dir + "/" + str(time.time()).replace(".", ""), data)

# sorted by distance, close to far
def connected_neighbors(world, agent, comms_model):
    x2, y2 = agent.coordinates[0], agent.coordinates[1]
    ns = []
    for n in world.get_agent_list():
        if n != agent:
            x1, y1 = n.coordinates[0], n.coordinates[1]
            if comms_model == "disk":
                dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M = world.config_data.disk_range)
            else:
                dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model)
            if comm_range:
                ns.append(n)
    return ns

# random jittering
def jitter(agent):
    target = (np.random.random(size=3) - 0.5) * 5
    target[2] = 0
    move_toward(agent, target)

# 2D rotation vector
def rot_vec(vec, rad=0):
    R = np.array([[np.cos(rad), -np.sin(rad)], [np.sin(rad), np.cos(rad)]])
    return R @ vec

# mod wrapper for agents
def get_agent_mod(agents, i):
    return agents[i % len(agents)]

# return list of n nearest neighbors of agent
def n_nearest(world, agent, n=2):
    n = min(n, len(world.get_agent_list()))
    max_dists = [(float("inf"), None) for _ in range(n)]
    for neighbor in world.get_agent_list():
        if neighbor != agent:
            n_dist = np.linalg.norm(np.array(agent.coordinates) - np.array(neighbor.coordinates))
            max_dist =  max(max_dists, key=lambda x: x[0])

            if n_dist < max_dist[0]:
                max_dists[max_dists.index(max_dist)] = (n_dist, neighbor)

    return [y for x, y in max_dists]

# move agent toward target
def move_toward(agent, target, thres=0.001):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec))
        return True
    return False

# move agent within [min_dist, max_dist] from target
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
