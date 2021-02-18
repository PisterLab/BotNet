import numpy as np
import math

COMMS_MODEL = "friis_upper"
DISK_RANGE_M = 3

SPEED_OF_LIGHT = 3e8 # m / s
TWO_DOT_FOUR_GHZ = 2.4e9 # Hz
PISTER_HACK_LOWER_SHIFT = 40 # dB

def solution(world):

    if world.get_actual_round() % 1 == 0:
        R_COLLISION, R_CONNECTION = .8, inverse_friis(pdr=1, shift=PISTER_HACK_LOWER_SHIFT / 2)
        print(R_CONNECTION)
        R1, R2 = R_COLLISION, R_CONNECTION
        k_col, k_conn = R1*R1 + R2, R2

        # set all agent control inputs
        control_inputs = {}
        for i, agent in enumerate(world.get_agent_list()):
            if i == 0 and leader_agent_move(world, agent):
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
                
            # print(f"{agent.neighbors} new vels {vx} {vy}")
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
        comms_range = False # TODO: implement line of sight
    elif comms_model == "los_disk":
        comms_range = False # FIXME: implement line of sight and ^ with disk
    elif comms_model == "friis_upper":
        comms_range = rssi_to_pdr_check(friis(dist))
    elif comms_model == "friis_average":
        comms_range = rssi_to_pdr_check(friis(dist) - PISTER_HACK_LOWER_SHIFT / 2.0)
    elif comms_model == "friis_lower":
        comms_range = rssi_to_pdr_check(friis(dist) - PISTER_HACK_LOWER_SHIFT)
    elif comms_model == "pister_hack":
        comms_range = rssi_to_pdr_check(friis(dist) - np.random.rand() * PISTER_HACK_LOWER_SHIFT)
    return dist, comms_range

VELOCITY_SCALE = 5
def leader_agent_move(world, agent):
    if world.get_actual_round() < 200:
        agent.set_velocities((VELOCITY_SCALE, 0, 0))
    elif world.get_actual_round() < 300:
        agent.set_velocities((VELOCITY_SCALE, VELOCITY_SCALE, 0))
    elif world.get_actual_round() < 400:
        agent.set_velocities((0, VELOCITY_SCALE, 0))
    elif world.get_actual_round() < 650:
        agent.set_velocities((-VELOCITY_SCALE, -VELOCITY_SCALE, 0))
    else:
        return False
    return True

def inverse_friis(pdr=.5, txPower=0, gain=0, shift=0):
    rssi = -79 # 0.5 : -93.6 # NOTE: hardcoded
    distance = SPEED_OF_LIGHT / (4 * math.pi * np.power(10, (rssi - txPower - gain + shift) / 20) * TWO_DOT_FOUR_GHZ)
    return distance

def friis(distance, txPower=0, gain=0):
    # sqrt and inverse of the free space path loss (fspl)
    free_space_path_loss = SPEED_OF_LIGHT / (4 * math.pi * distance * TWO_DOT_FOUR_GHZ)

    # simple friis equation in Pr = Pt + Gt + Gr + 20log10(fspl)
    pr = (
        txPower + gain +
        (20 * math.log10(free_space_path_loss))
    )

    # NOTE: how does 6TiSCH model interferences? wouldn't really make sense here I guess

    return pr

# RSSI and PDR relationship obtained by experiment; dataset was available
# at the link shown below:
# http://wsn.eecs.berkeley.edu/connectivity/?dataset=dust
RSSI_PDR_TABLE = {
    -97:    0.0000,  # this value is not from experiment
    -96:    0.1494,
    -95:    0.2340,
    -94:    0.4071,
    # <-- 50% PDR is here, at RSSI=-93.6
    -93:    0.6359,
    -92:    0.6866,
    -91:    0.7476,
    -90:    0.8603,
    -89:    0.8702,
    -88:    0.9324,
    -87:    0.9427,
    -86:    0.9562,
    -85:    0.9611,
    -84:    0.9739,
    -83:    0.9745,
    -82:    0.9844,
    -81:    0.9854,
    -80:    0.9903,
    -79:    1.0000,  # this value is not from experiment
}

PDR_RSSI_TABLE = dict((v,k) for k,v in RSSI_PDR_TABLE.items())

def rssi_to_pdr_check(rssi):
    minRssi = min(RSSI_PDR_TABLE.keys())
    maxRssi = max(RSSI_PDR_TABLE.keys())

    if rssi < minRssi:
        pdr = 0.0
    elif rssi > maxRssi:
        pdr = 1.0
    else:
        floor_rssi = int(math.floor(rssi))
        pdr_low    = RSSI_PDR_TABLE[floor_rssi]
        pdr_high   = RSSI_PDR_TABLE[floor_rssi + 1]
        # linear interpolation
        pdr = (pdr_high - pdr_low) * (rssi - float(floor_rssi)) + pdr_low

    assert pdr >= 0.0
    assert pdr <= 1.0
    return np.random.rand() < pdr