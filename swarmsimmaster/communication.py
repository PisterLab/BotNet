import numpy as np
import math
from scipy.spatial import distance
import old_comms_test

def assign_agent_neighbors(agents, comms_model = "friis_upper"):
    #Credit to https://www.robots.ox.ac.uk/~albanie/notes/Euclidean_distance_trick.pdf for distance calculation optimization trick
    all_locations = [[a.coordinates[0], a.coordinates[1]] for a in agents]
    X = np.vstack(all_locations)
    distance_matrix = distance.cdist(X, X)
    neighbors_matrix = communication_model(distance_matrix, comms_model)
    for i, agent in enumerate(agents):
        #flush_neighbors
        agent.neighbors = {}
        neighbor_indices = neighbors_matrix[i].nonzero()[0]
        for j in neighbor_indices:
           agent.neighbors[agents[j].get_id()] = agents[j].coordinates



SPEED_OF_LIGHT = 3e8  # m / s
TWO_DOT_FOUR_GHZ = 2.4e9  # Hz
PISTER_HACK_LOWER_SHIFT = 40  # dB
def communication_model(distance_matrix, comms_model="friis_upper", DISK_RANGE_M=3):
    comms_range = True
    if comms_model == "full":
       return np.ones(distance_matrix.shape)
    elif comms_model == "disk":
        return np.where(distance_matrix <= DISK_RANGE_M, 1, 0)
    elif comms_model == "los":
        raise Exception("Line of sight comms model not yet implemented ")
    elif comms_model == "los_disk":
        raise Exception("Line of sight comms model not yet implemented ")
    elif comms_model == "friis_upper":
        comms_range = rssi_to_pdr_check(friis(distance_matrix))
    elif comms_model == "friis_average":
        comms_range = rssi_to_pdr_check(friis(distance_matrix) - PISTER_HACK_LOWER_SHIFT / 2.0)
    elif comms_model == "friis_lower":
        comms_range = rssi_to_pdr_check(friis(distance_matrix) - PISTER_HACK_LOWER_SHIFT)
    elif comms_model == "pister_hack":
        comms_range = rssi_to_pdr_check(friis(distance_matrix) - np.random.rand(distance_matrix.shape) * PISTER_HACK_LOWER_SHIFT)
    return comms_range

def inverse_friis(pdr=.5, txPower=0, gain=0, shift=0):
    rssi = -86 # 0.5 : -93.6 # NOTE: hardcoded
    distance = SPEED_OF_LIGHT / (4 * np.pi * np.power(10, (rssi - txPower - gain + shift) / 20) * TWO_DOT_FOUR_GHZ)
    return distance
def friis(distance, txPower=0, gain=0):
    # sqrt and inverse of the free space path loss (fspl)
    free_space_path_loss = SPEED_OF_LIGHT / (4 * np.pi * distance * TWO_DOT_FOUR_GHZ)
    # simple friis equation in Pr = Pt + Gt + Gr + 20log10(fspl)
    pr = (
        txPower + gain +
        (20 * np.log10(free_space_path_loss))
    )
    # NOTE: how does 6TiSCH model interferences? wouldn't really make sense here I guess
    return pr
# RSSI and PDR relationship obtained by experiment; dataset was available
# at the link shown below:
# http://wsn.eecs.berkeley.edu/connectivity/?dataset=dust
RSSI_PDR_TABLE = np.array([
    [-97,    0.0000],  # this value is not from experiment
    [-96,    0.1494],
    [-95,    0.2340],
    [-94,    0.4071],
    # <-- 50% PDR is here, at RSSI=-93.6
    [-93,    0.6359],
    [-92,    0.6866],
    [-91,    0.7476],
    [-90,    0.8603],
    [-89,    0.8702],
    [-88,    0.9324],
    [-87,    0.9427],
    [-86,    0.9562],
    [-85,    0.9611],
    [-84,    0.9739],
    [-83,    0.9745],
    [-82,    0.9844],
    [-81,    0.9854],
    [-80,    0.9903],
    [-79,    1.0000],  # this value is not from experiment
])

RSSI_PDR_DICT = {
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
def rssi_to_pdr_check(rssi):
    #replace the diagnol to 0 for self communications
    rssi[rssi == np.inf] = 0
    floor_rssi = np.floor(rssi).astype(np.int32)
    floor_rssi = np.clip(floor_rssi, -97, -79)
    u, inv = np.unique(floor_rssi, return_inverse=True)
    pdr_low = np.array([RSSI_PDR_DICT[x] for x in u])[inv].reshape(floor_rssi.shape)
    f1 = np.clip(floor_rssi + 1,  -97, -79 )
    u, inv = np.unique(f1, return_inverse=True)
    pdr_high = np.array([RSSI_PDR_DICT[x] for x in u])[inv].reshape(floor_rssi.shape)

    #  pdr_low    = RSSI_PDR_TABLE[maxRssi - ][1]
    #  pdr_high   = RSSI_PDR_TABLE[floor_rssi + 1]
    # linear interpolation
    pdr = (pdr_high - pdr_low) * (rssi - floor_rssi.astype(np.float32)) + pdr_low
    assert np.min(pdr_low) >= 0.0
    assert np.max(pdr) <= 1.0
    return np.random.rand(rssi.shape[0], rssi.shape[1]) < pdr