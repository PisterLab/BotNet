import random
import numpy as np
import queue

INF = 10000
radius = 5
eps = 0.0001
max_speed = 0.1

def solution(world):
    global radius

    nn_min_radius = 2
    nn_max_radius = 1

    # if timestep(world) > 200:
    #     center = (7, 7, 0)
    # elif timestep(world) == 200:
    #     #print("updated")
    #     #radius = 3
    #     #center = (7, 7, 0)
    # else:
    center = world.grid.get_center()

    num_agents =  len(world.get_agent_list())

    # # satisfy radius
    # radius_moved = []
    # for agent in world.get_agent_list():
    #     center_vec = np.array(agent.coordinates) - np.array(center)
    #     center_dist = np.linalg.norm(center_vec)
    #
    #     radius_target = center_vec / (eps + center_dist) * radius + center
    #     radius_moved.append(move_toward(agent, radius_target, thres=1))
    #

    # neighbors requirement
    for i, agent in enumerate(world.get_agent_list()):
        nns = n_nearest(world, agent, n=1)
        want = [world.get_agent_list()[(i-1) % num_agents]]

        n_vec = np.array(agent.coordinates) - np.array(nns[0].coordinates)
        n_dist = np.linalg.norm(n_vec)
        w_vec = np.array(agent.coordinates) - np.array(want[0].coordinates)
        w_dist = np.linalg.norm(w_vec)

        if w_dist > nn_max_radius:
            nn_target = w_vec / (eps + w_dist) * nn_max_radius + np.array(want[0].coordinates)
            move_toward(agent, nn_target)

        if n_dist < nn_min_radius and nns[0] not in want:
            nn_target =  n_vec / (eps + n_dist) * nn_min_radius + np.array(nns[0].coordinates)
            move_toward(agent, nn_target)



    #radius = max([np.linalg.norm(np.array(agent.coordinates)  - np.array(center)) for agent in world.get_agent_list()])

def n_nearest(world, agent, n=2):
    max_dists = [(INF, None) for _ in range(n)]
    for neighbor in world.get_agent_list():
        if neighbor != agent:
            n_dist = np.linalg.norm(np.array(agent.coordinates) - np.array(neighbor.coordinates))
            max_dist =  max(max_dists, key=lambda x: x[0])

            if n_dist < max_dist[0]:
                max_dists[max_dists.index(max_dist)] = (n_dist, neighbor)

    return [y for x, y in max_dists]

def move_toward(agent, target, thres=0.4):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec))
        return True
    return False

def speed_limit(speed_vec):
    speed = np.linalg.norm(speed_vec)
    if speed > max_speed:
        return speed_vec / (speed + eps) * max_speed
    return speed_vec

def timestep(world):
    return world.get_actual_round()