import numpy as np

COMMS_MODEL = "disk"
DISK_RANGE_M = 3

def solution(world):

    if world.get_actual_round() % 1 == 0:
        R_COLLISION, R_CONNECTION = 1, DISK_RANGE_M / 2
        R1, R2 = R_COLLISION, R_CONNECTION
        k_col, k_conn = R1*R1 + R2, R2

        # set all agent control inputs
        control_inputs = {}
        for i, agent in enumerate(world.get_agent_list()):
            if i == 0:
                leader_agent_move(world, agent)
                continue
            vx, vy, vz = 0, 0, 0
            for neighbor in world.get_agent_list(): # TODO: agent neighbors
                if agent == neighbor:
                    continue

                x1, y1, _ = agent.coordinates
                x2, y2, _ = neighbor.coordinates

                dist, comm_range = communication_model(x1, y1, x2, y2)

                if not comm_range:
                    continue
                
                vx += 2*(x1-x2) * (k_conn*np.exp((dist)/(R2*R2)) / (R2*R2) - k_col*np.exp(-(dist)/(R1*R1)) / (R1*R1))
                vy += 2*(y1-y2) * (k_conn*np.exp((dist)/(R2*R2)) / (R2*R2) - k_col*np.exp(-(dist)/(R1*R1)) / (R1*R1))
                vz += 0
                
            print(f"{agent.neighbors} new vels {vx} {vy}")
            agent.set_velocities((-vx, -vy, -vz))
            # agent.neighbors = []

        for agent in world.get_agent_list():
            agent.move()

def communication_model(x1, y1, x2, y2):
    comms_model = COMMS_MODEL
    dist = np.sqrt((x2-x1)**2 + (y2-y1)**2)
    comms_range = True
    if comms_model == "full":
        comms_range = True
    elif comms_model == "disk":
        comms_range = dist <= DISK_RANGE_M
    elif comms_model == "los":
        comms_range = False # FIXME
    elif comms_model == "los_disk":
        comms_range = False # FIXME
    elif comms_model == "friis_upper":
        comms_range = False # FIXME
    elif comms_model == "friis_average":
        comms_range = False # FIXME
    elif comms_model == "friis_lower":
        comms_range = False # FIXME
    elif comms_model == "pister_hack":
        comms_range = False # FIXME
    return dist, comms_range

def leader_agent_move(world, agent):
    if world.get_actual_round() < 200:
        agent.set_velocities((1, 0, 0))
    elif world.get_actual_round() < 400:
        agent.set_velocities((1, 1, 0))
    elif world.get_actual_round() < 600:
        agent.set_velocities((0, 1, 0))
    else:
        agent.set_velocities((-1, -2, 0))