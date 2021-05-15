import numpy as np
from swarmsimmaster.components.scenario.formation_ctrl import connected_neighbors, move_toward, log_data
import time

r = 10
terminated = False

def solution(world):
    global terminated

    if world.get_actual_round() == 0:
        terminated = False

    if not terminated:
        comms_model = world.config_data.comms
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
            
def angle(v):
    u = np.array([1, 0])
    dot = np.dot(u, v[:2])
    det = u[0] * v[1] - u[1] * v[0]
    a = np.rad2deg(np.arctan2(det, dot)) % 360
    return a

def benchmark(world, diff, spokes):
    convergence_time = world.get_actual_round()
    data = np.array([convergence_time, np.var(diff), np.var(np.linalg.norm(spokes, axis=1))])
    log_data(data)


