import numpy as np
from swarmsimmaster.components.scenario.formation_ctrl import connected_neighbors, move_toward, log_data


terminated = False

def solution(world):
    global terminated

    if world.get_actual_round() == 1:
        terminated = False

    comms_model = world.config_data.comms
    agents = world.get_agent_list()

    moved = []
    for i, agent in enumerate(agents):
        neighbors = connected_neighbors(world, agent, comms_model)
        x, y, k = lstsq(agent, neighbors)
        m, c = k[0]
        x1, y1 = x[0], y[0]
        x_target = (x1 / m + y1 - c) / (m + 1/m)
        y_target = m * x_target + c
        target = np.array([x_target, y_target, 0])
        moved.append(move_toward(agent, target))

    if not any(moved) and not terminated:
        benchmark(world)
        terminated = True

def lstsq(agent, neighbors):
    x = [agent.coordinates[0]]
    y = [agent.coordinates[1]]

    for n in neighbors:
        x.append(n.coordinates[0])
        y.append(n.coordinates[1])

    x, y = np.array(x), np.array(y)
    A = np.vstack([x, np.ones(len(x))]).T
    return x, y, np.linalg.lstsq(A, y, rcond=None)

def benchmark(world):
    convergence_time = world.get_actual_round()
    residuals = lstsq(world.get_agent_list()[0], world.get_agent_list()[1:])[2][1][0]
    data = np.array([convergence_time, residuals])
    log_data(data)

