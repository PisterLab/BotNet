import numpy as np
import torch
import omegaconf
import mbrl.util.common as common_util
import mbrl.models as models
import mbrl.planning as planning
import svs_env

from communication import communication_model

terminated = False

# Game conditions
eps = 10e-8
defense_max_speed = 0.1
offense_max_speed = 0.1
# offense_max_speed = 0.09
comms_model = "disk"
DISK_RANGE = 3

# Goal positions
defense_clr = [0, 0, 255, 1]
offense_clr = [255, 0, 0, 1]
defense_center = [-10, 0, 0]
offense_center = [10, 0, 0]

def load_model():
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    # Configure dynamics model
    ensemble_size = 5
    cfg_dict = {
        # dynamics model configuration
        "dynamics_model": {
            "model": {
                "_target_": "mbrl.models.GaussianMLP",
                "device": device,
                "num_layers": 3,
                "ensemble_size": ensemble_size,
                "hid_size": 200,
                "in_size": "???",
                "out_size": "???",
                "deterministic": False,
                "propagation_method": "fixed_model"
            }
        },
        # options for training the dynamics model
        "algorithm": {
            "learned_rewards": False,
            "target_is_delta": True,
            "normalize": True,
        },
        # these are experiment specific options
        "overrides": {}
    }
    cfg = omegaconf.OmegaConf.create(cfg_dict)

    # Create a 1-D dynamics model for this environment
    dynamics_model = common_util.create_one_dim_tr_model(cfg, (7,), (1,), model_dir="/home/jennomai/code/BotNet/swarmsimmaster/outputs/models/model 2021-11-30 12:40:53.848900")

    # Create a gym-like environment to encapsulate the model
    env = svs_env.SwarmEnv()
    env.seed(0)
    model_env = models.ModelEnv(env, dynamics_model, svs_env.termination_fn, svs_env.reward_fn)

    # Create agent
    agent_cfg = omegaconf.OmegaConf.create({
        # this class evaluates many trajectories and picks the best one
        "_target_": "mbrl.planning.TrajectoryOptimizerAgent",
        "planning_horizon": 15,
        "replan_freq": 1,
        "verbose": False,
        "action_lb": 0,
        "action_ub": 3,
        # this is the optimizer to generate and choose a trajectory
        "optimizer_cfg": {
            "_target_": "mbrl.planning.CEMOptimizer",
            "num_iterations": 5,
            "elite_ratio": 0.1,
            "population_size": 500,
            "alpha": 0.1,
            "device": device,
            "lower_bound": "???",
            "upper_bound": "???",
            "return_mean_elites": True,
        }
    })
    agent = planning.create_trajectory_optim_agent_for_model(
        model_env,
        agent_cfg,
        num_particles=20
    )
    return agent

model = load_model()

def solution(world, stats=None):
    global terminated
    if not terminated:
        offense_drones = get_drones(world, clr=offense_clr)
        defense_drones = get_drones(world, clr=defense_clr)

        # check if defenders win
        if not offense_drones:
            terminated = True
        # check if attackers win
        elif not defense_drones:
            terminated = True
        else:
            # defense policy applied
            # def_p1(world, defense_drones, offense_drones)

            # check deaths in offense after defense moves
            off_death_check1(world, defense_drones, offense_drones)

            # refresh offense_drones
            offense_drones = get_drones(world, clr=offense_clr)

            # offense policy applied
            off_rl(world, defense_drones, offense_drones, model, timestep(world))

            # defender death check
            # def_death_check1(world, defense_drones, offense_drones)
            oob_check(world, defense_drones, offense_drones)
    else:
        world.set_successful_end()

# kills agents that move too far away
def oob_check(world, defense_drones, offense_drones):
    sorted_offense = sorted(offense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)), reverse=True)
    sorted_defense = sorted(defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)), reverse=True)
    for o in sorted_offense:
        if (o.alive):
            dist = np.linalg.norm(np.array(o.coordinates) - np.array(defense_center))
            if (dist > 40):
                death_routine(o)
            else:
                break
    
    for d in sorted_defense:
        if d.alive:
            dist = np.linalg.norm(np.array(d.coordinates) - np.array(defense_center))
            if (dist > 40):
                death_routine(d)
            else:
                break

# offense death check
def off_death_check1(world, defense_drones, offense_drones, stats=None):
    global terminated

    # death check for offense
    for a in offense_drones:
        sorted_defense = sorted(defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(a.coordinates)))
        closest_defense = sorted_defense[0]
        # check if dead
        if np.linalg.norm(np.array(closest_defense.coordinates) - np.array(a.coordinates)) < 0.1:
            death_routine(a)

            ### hopefully temporary?
            # closest_defense.kills += 1
            ###

        # check if attackers win:
        if np.linalg.norm(np.array(a.coordinates) - np.array(defense_center)) < 0.1:
            terminated = True

def proximity_death_check(world, defense_drones, offense_drones, chance_func):
    global terminated

    # death check for offense
    for a in offense_drones:
        _, near_defense = get_local_agents(world, a, offense_drones, defense_drones)
        
        # check if dead
        for d in near_defense:
            distance = np.linalg.norm(np.array(d.coordinates) - np.array(a.coordinates))
            if np.random.rand() < chance_func(distance):
                death_routine(a)
                ### hopefully temporary?
                d.kills += 1
                ###
                break

    # check if attackers win:
        if np.linalg.norm(np.array(a.coordinates) - np.array(defense_center)) < 0.1:
            terminated = True
    return

# defense death check 1: defenders die after eliminating `n` attackers
def def_death_check1(world, defense_drones, offense_drones):
    for a in defense_drones:
        if (a.kills) >= 3:
            death_routine(a)

#######
def dodge_vec(agent, sorted_agents, angle=90):
        """Returns a vector to dodge towards.
        :param agent: the agent to move
        :param sorted_agents: the sorted list of agents to dodge
        :param angle: the angle at which to dodge
        :return: a numpy vector in 3D
        """
        u = np.array(sorted_agents[0].coordinates) - np.array(agent.coordinates)
        u = u / np.linalg.norm(u)
        v = np.array(defense_center)
        w = v - (v @ u) * u
        w = w / np.linalg.norm(w)
        return 10 * (np.sin(angle*np.pi/180) * w + np.cos(angle*np.pi/180) * u)


def num_in_range(agent, agent_list, range):
        """Returns the number of agents within a range (inclusive) of a given agent.
        :param agent: the agent to check around
        :param agent_list: the agents to check for
        :return: (int)
        """
        num = 0
        for a in agent_list:
            if np.linalg.norm(np.array(agent.coordinates) - np.array(a.coordinates)) <= range:
                num += 1
        return num
#######

# def policy 1: go to closest attacker to center
def def_p1(world, defense_drones, offense_drones):
    sorted_offense = sorted(offense_drones,
                            key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)))
    for a in defense_drones:
        closest_offense = sorted_offense[0]
        move_toward(a, closest_offense.coordinates)

# def policy 2: go to the closest non-targeted attacker from center
# if all targeted, go to the closest attacker from center
def def_p2(world, defense_drones, offense_drones):
    sorted_offense = sorted(offense_drones,
                            key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)))
    sorted_offense_cpy = sorted_offense.copy()

    for a in defense_drones:
        if sorted_offense_cpy:
            closest_offense = sorted_offense_cpy.pop(0)
        else:
            closest_offense = sorted_offense[0]
        move_toward(a, closest_offense.coordinates)

# def policy 3: go to the closest guy from YOU that is non-targeted
# if all targeted, go to the closest attacker from center
def def_p3(world, defense_drones, offense_drones):
    targetted = []

    for a in defense_drones:
        self_sorted_offense = sorted(offense_drones, key=lambda x: np.linalg.norm(
            np.array(x.coordinates) - np.array(a.coordinates)))

        flag = False
        for x in self_sorted_offense:
            if x.coordinates not in targetted:
                flag = True
                targetted.append(x.coordinates)
                move_toward(a, x.coordinates)
                break
        if not flag:
            sorted_offense = sorted(offense_drones,
                                    key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)))
            closest_offense = sorted_offense[0]
            move_toward(a, closest_offense.coordinates)

def get_drones(world, clr):
    lst = []
    for a in world.get_agent_list():
        if a.color == clr and a.alive:
            lst.append(a)
    return lst

def death_routine(a):
    a.alive = False
    a.update_agent_coordinates(a, (100, 100, 0))

####################################################
# move agent toward target
def move_toward(agent, target, thres=0.001):
    vec = np.array(target) - np.array(agent.coordinates)
    if np.linalg.norm(vec) > thres:
        agent.move_to(speed_limit(vec, agent))
        return True
    return False

# enforce speed limit
def speed_limit(speed_vec, agent):
    speed = np.linalg.norm(speed_vec)

    if agent.color == defense_clr:
        max_speed = defense_max_speed
    else:
        max_speed = offense_max_speed

    if speed > max_speed:
        return speed_vec / (speed + eps) * max_speed
    return speed_vec


# helper for timestep
def timestep(world):
    return world.get_actual_round()

##############################################
# random jittering
def jitter(agent):
    target = (np.random.random(size=3) - 0.5) * 10
    target[2] = 0
    target += agent.coordinates
    move_toward(agent, target)


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

# returns lists of offense and defense drones "visible" to the agent
def get_local_agents(world, agent, offense_drones, defense_drones, disk_range=DISK_RANGE):
    local_offense = []
    local_defense = []

    x2, y2 = agent.coordinates[0], agent.coordinates[1]
    for o in offense_drones:
        x1, y1 = o.coordinates[0], o.coordinates[1]
        dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M = disk_range)
        if (comm_range):
            local_offense.append(o)
    for d in defense_drones:
        x1, y1 = d.coordinates[0], d.coordinates[1]
        dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M = disk_range)
        if (comm_range):
            local_defense.append(d)
    
    return local_offense, local_defense

def off_rl(world, defense_drones, offense_drones, agent, ts):
    for a in offense_drones:
        obs = np.zeros(7)
        obs[0:3] = a.coordinates
        obs[3:6] = defense_drones[0].coordinates
        obs[6] = ts
        action = agent.act(torch.tensor(obs))
        move = world.grid.get_directions_list()[int(np.rint(action.squeeze()))]
        a.move_to(speed_limit(move, a))
