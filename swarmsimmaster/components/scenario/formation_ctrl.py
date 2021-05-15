import numpy as np
import random
import math
import os

eps = 10e-8
max_speed = 0.1
conv_thres = 0.001

# Agent spawns
def scenario(world):
    swarm_size = world.config_data.num_agents
    for s in range(swarm_size):
        spawn = list(circle_spawn(swarm_size))
        spawn.append(0)
        world.add_agent(tuple(spawn))

def circle_spawn(swarm_size):
    density = 0.22
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    radius =  pow(swarm_size / (density * np.pi), 0.5)
    return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])


def log_data(world, data):
    np.savetxt(os.path.join(world.config_data.directory_csv, "data.csv"), data, delimiter=",")

# move agent toward target
def move_toward(agent, target, thres=conv_thres):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec))
        return True
    return False

# enforce speed limit
def speed_limit(speed_vec):
    speed = np.linalg.norm(speed_vec)
    if speed > max_speed:
        return speed_vec / (speed + eps) * max_speed
    return speed_vec

# comms model
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

# Base communication code
SPEED_OF_LIGHT = 3e8  # m / s
TWO_DOT_FOUR_GHZ = 2.4e9  # Hz
PISTER_HACK_LOWER_SHIFT: int = 40  # dB

def communication_model(x1, y1, x2, y2, comms_model="friis_upper", DISK_RANGE_M="3"):
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

def inverse_friis(pdr=.5, txPower=0, gain=0, shift=0):
    rssi = -86 # 0.5 : -93.6 # NOTE: hardcoded
    distance = SPEED_OF_LIGHT / (4 * np.pi * np.power(10, (rssi - txPower - gain + shift) / 20) * TWO_DOT_FOUR_GHZ)
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

PDR_RSSI_TABLE = dict((v,k) for k,v in RSSI_PDR_TABLE.items()) # get ordered keys to make this work

def rssi_to_pdr_check(rssi, disk=False):
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
    return np.random.rand() < pdr if not disk else pdr == 1.0