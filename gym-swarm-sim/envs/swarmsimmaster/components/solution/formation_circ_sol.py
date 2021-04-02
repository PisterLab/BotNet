import numpy as np
from communication import communication_model
import csv
import time

eps = 10e-8
max_speed = 0.1
comms_model = "full"
r = 10
terminated = False

def solution(world):
    global terminated

    if timestep(world) == 0:
        terminated = False

    if not terminated:
        comms_model = world.config_data.comms_model
        agents = world.get_agent_list()

        for i, agent in enumerate(agents):
            neighbors = connected_neighbors(world, agent, comms_model)
            if len(neighbors) >= 3:
                neighbors = sorted(neighbors, key=lambda x: np.linalg.norm(np.array(agent.coordinates) - np.array(x.coordinates)))
                closest, second_closest, furthest = neighbors[0], neighbors[1], neighbors[-1]
                centroid_data = np.vstack((np.array(closest.coordinates), np.array(second_closest.coordinates), np.array(furthest.coordinates)))
                centroid = np.mean(centroid_data, axis=0)

                d = np.linalg.norm(np.array(agent.coordinates) - centroid)
                radius_thres = 0.1

                agent_to_centroid = np.array(np.array(centroid) - np.array(agent.coordinates))
                agent_to_centroid = agent_to_centroid / np.linalg.norm(agent_to_centroid)

                if (d - r) > radius_thres:
                    target = np.array(agent.coordinates) + agent_to_centroid * (d - r)
                    move_toward(agent, target)
                elif (d - r) < -radius_thres:
                    target = -1 * (r - d) * agent_to_centroid + np.array(agent.coordinates)
                    move_toward(agent, target)
                else:
                    target = np.array(np.array(agent.coordinates) - np.array(closest.coordinates))
                    scale = 0.04
                    target_norm = np.linalg.norm(target)
                    target = target / target_norm * scale
                    target = np.array(agent.coordinates) + target
                    move_toward(agent, target)

        # find center
        coords = []
        for i, agent in enumerate(agents):
            coords.append(np.array(agent.coordinates))
        coords = np.array(coords)
        center = np.mean(coords, axis=0)

        # find angles of spokes
        angles = []
        spokes = []
        for agent in agents:
            spoke = center - np.array(agent.coordinates)
            angles.append(angle(spoke))
            spokes.append(spoke)

        angles = sorted(angles)
        diff = []
        for i in range(len(angles) - 1):
            diff.append(angles[i + 1] - angles[i])

        # variance check
        if np.var(diff) < 0.3 and np.var(np.linalg.norm(spokes, axis=1)) < 0.01:
            terminated = True
            benchmark(world, diff, spokes)

def benchmark(world, diff, spokes):
    convergence_time = timestep(world)
    data = np.array([convergence_time, np.var(diff), np.var(np.linalg.norm(spokes, axis=1))])
    np.save(world.config_data.data_dir + "/" + str(time.time()).replace(".", ""), data)

def angle(v):
    u = np.array([1, 0])
    dot = np.dot(u, v[:2])
    det = u[0] * v[1] - u[1] * v[0]
    a = np.rad2deg(np.arctan2(det, dot)) % 360

    return a

def connected_neighbors(world, agent, comms_model):
    x2, y2 = agent.coordinates[0], agent.coordinates[1]
    ns = []
    for n in world.get_agent_list():
        if n != agent:
            x1, y1 = n.coordinates[0], n.coordinates[1]
            dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M = 3.5)
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
