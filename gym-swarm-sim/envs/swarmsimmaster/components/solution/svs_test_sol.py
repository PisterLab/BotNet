import numpy as np
import time

eps = 10e-8
defense_max_speed = 0.1
offense_max_speed = 0.09
# offense_max_speed = 0.09

terminated = False

defense_clr = [0, 0, 255, 1]
offense_clr = [255, 0, 0, 1]
defense_center = [-10, 0, 0]
offense_center = [10, 0, 0]

def solution(world):
    global terminated

    if not terminated:

        agents = world.get_agent_list()

        # add alive marker
        if timestep(world) == 1:
            for a in agents:
                a.alive = True

        # get alive attackers and defenders
        offense_drones = get_drones(world, clr=offense_clr)
        defense_drones = get_drones(world, clr=defense_clr)

        # check if defenders win
        if not offense_drones:
            terminated = True
        else:
            # defense policy applied
            def_p3(world, defense_drones, offense_drones)

            # check deaths in offense after defense moves
            off_death_check(world, defense_drones, offense_drones)

            # refresh offense_drones
            offense_drones = get_drones(world, clr=offense_clr)

            # offense policy applied
            off_p2(world, defense_drones, offense_drones)

            # defender death check

# offense death check
def off_death_check(world, defense_drones, offense_drones):
    global terminated

    # death check for offense
    for a in offense_drones:
        sorted_defense = sorted(defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(a.coordinates)))
        closest_defense = sorted_defense[0]
        # check if dead
        if np.linalg.norm(np.array(closest_defense.coordinates) - np.array(a.coordinates)) < 0.1:
            death_routine(a)

        # check if attackers win:
        if np.linalg.norm(np.array(a.coordinates) - np.array(defense_center)) < 0.1:
            terminated = True

# off policy 1: go to center directly
def off_p1(world, defense_drones, offense_drones):
    for a in offense_drones:
        move_toward(a, defense_center)

# off policy 2: hand craft
def off_p2(world, defense_drones, offense_drones):
    leaders = []
    total_leaders = min(len(offense_drones), 20)

    for a in offense_drones:
        if hasattr(a, "leader"):
            leaders.append(a)

    for i in range(total_leaders - len(leaders)):
        for a in offense_drones:
            if not hasattr(a, "leader") and not hasattr(a, "sneaker"):
                leaders.append(a)
                a.leader = True
                break

    for leader in leaders:
        move_toward(leader, (0, -100, 0))

    for i, a in enumerate(offense_drones):
        if not hasattr(a, "leader"):
            move_toward(a, defense_center)

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
