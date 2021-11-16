import numpy as np

from components.solution.svs_strategies.defense.split_closest_ring import SplitClosestRing
from components.solution.svs_strategies.offense.orth_dodge import OrthDodge
from old_comms_test import communication_model

eps = 10e-8
comms_model = "disk"
DISK_RANGE = 3

terminated = False

defense_clr = [0, 0, 255, 1]
offense_clr = [255, 0, 0, 1]
defense_center = [-10, 0, 0]
offense_center = [10, 0, 0]

off_strat = OrthDodge(off_clr=offense_clr, def_clr=defense_clr, off_center=offense_center, def_center=defense_center)
def_strat = SplitClosestRing(off_clr=offense_clr, def_clr=defense_clr, off_center=offense_center, def_center=defense_center)


def solution(world, stats=None):
    global terminated

    if not terminated:

        agents = world.get_agent_list()

        # add alive and kills markers
        if timestep(world) == 1:
            for a in agents:
                a.alive = True
                a.kills = 0

        # get alive attackers and defenders
        offense_drones = get_drones(world, clr=offense_clr)
        defense_drones = get_drones(world, clr=defense_clr)

        # check if defenders win
        if not offense_drones:
            terminated = True
            if (stats):
                stats.increment_wins()
        # check if attackers win
        elif not defense_drones:
            terminated = True
            if (stats):
                stats.increment_losses()
        else:
            # defense policy applied
            def_strat.solution(world)

            # offense policy applied
            off_strat.solution(world)

            # check deaths in offense after defense moves
            proximity_death_check(world, defense_drones, offense_drones, lambda d: 1 - 3 * d)

            # defender death check
            def_death_check1(world, defense_drones, offense_drones)

            oob_check(world, defense_drones, offense_drones)
    else:
        world.set_successful_end()


def get_drones(world, clr):
    lst = []
    for a in world.get_agent_list():
        if a.color == clr and a.alive:
            lst.append(a)
    return lst


# kills agents that move too far away
def oob_check(world, defense_drones, offense_drones):
    sorted_offense = sorted(offense_drones,
                            key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)),
                            reverse=True)
    sorted_defense = sorted(defense_drones,
                            key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(defense_center)),
                            reverse=True)
    for o in sorted_offense:
        dist = np.linalg.norm(np.array(o.coordinates) - np.array(defense_center))
        if (dist > 40):
            death_routine(o)
        else:
            break

    for d in sorted_defense:
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
            closest_defense.kills += 1
            ###

        # check if attackers win:
        if np.linalg.norm(np.array(a.coordinates) - np.array(defense_center)) < 0.1:
            terminated = True


# offense death check with % chance of death
def off_death_check2(world, defense_drones, offense_drones):
    global terminated

    # death check for offense
    for a in offense_drones:
        sorted_defense = sorted(defense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(a.coordinates)))
        closest_defense = sorted_defense[0]
        # check if dead
        if np.linalg.norm(
                np.array(closest_defense.coordinates) - np.array(a.coordinates)) < 0.1 and np.random.rand() > 0.8:
            death_routine(a)

            ### hopefully temporary?
            closest_defense.kills += 1
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


def death_routine(a):
    a.alive = False
    a.update_agent_coordinates(a, (100, 100, 0))

# helper for timestep
def timestep(world):
    return world.get_actual_round()


# returns lists of offense and defense drones "visible" to the agent
def get_local_agents(world, agent, offense_drones, defense_drones, disk_range=DISK_RANGE):
    local_offense = []
    local_defense = []

    x2, y2 = agent.coordinates[0], agent.coordinates[1]
    for o in offense_drones:
        x1, y1 = o.coordinates[0], o.coordinates[1]
        dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M=disk_range)
        if (comm_range):
            local_offense.append(o)
    for d in defense_drones:
        x1, y1 = d.coordinates[0], d.coordinates[1]
        dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=comms_model, DISK_RANGE_M=disk_range)
        if (comm_range):
            local_defense.append(d)

    return local_offense, local_defense