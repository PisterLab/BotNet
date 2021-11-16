import numpy as np

from old_comms_test import communication_model


class SVSStrategy:
    """1 SVSSol determines strategies for one group of drones"""
    def __init__(self, off_clr, def_clr, off_center, def_center, disk_range=3):
        # TODO reconfig with environment parameters file
        self.DEFENSE_CLR = def_clr
        self.OFFENSE_CLR = off_clr
        self.DEFENSE_CENTER = def_center
        self.OFFENSE_CENTER = off_center
        self.DEFENSE_MAX_SPEED = 1
        self.OFFENSE_MAX_SPEED = 1
        self.DISK_RANGE = disk_range
        self.EPS = 10e-8

    # abstract method
    def run(self, observations):
        """Move all drones in group according to policy"""
        pass

    def solution(self, world):
        offense_drones = self.get_drones(world, clr=self.OFFENSE_CLR)
        defense_drones = self.get_drones(world, clr=self.DEFENSE_CLR)

        observations = Observations(offense_drones, defense_drones)
        self.run(observations)

    def get_drones(self, world, clr):
        lst = []
        for a in world.get_agent_list():
            if a.color == clr and a.alive:
                lst.append(a)
        return lst

    def circle_spawn(swarm_size):
        density = 0.22
        t = 2 * np.pi * np.random.random()
        u = np.random.random() + np.random.random()
        r = 2 - u if u > 1 else u
        radius = pow(swarm_size / (density * np.pi), 0.5)
        return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])

    def get_drones(self, world, clr):
        lst = []
        for a in world.get_agent_list():
            if a.color == clr and a.alive:
                lst.append(a)
        return lst

    def death_routine(self, a):
        a.alive = False
        a.update_agent_coordinates(a, (100, 100, 0))

    # move agent toward target
    def move_toward(self, agent, target, thres=0.001):
        vec = np.array(target) - np.array(agent.coordinates)
        if np.linalg.norm(vec) > thres:
            agent.move_to(self.speed_limit(vec, agent))
            return True
        return False

    # enforce speed limit
    def speed_limit(self, speed_vec, agent):
        speed = np.linalg.norm(speed_vec)

        if agent.color == self.DEFENSE_CLR:
            max_speed = self.DEFENSE_MAX_SPEED
        else:
            max_speed = self.OFFENSE_MAX_SPEED

        if speed > max_speed:
            return speed_vec / (speed + self.EPS) * max_speed
        return speed_vec

    # helper for timestep
    def timestep(self, world):
        return world.get_actual_round()

    # random jittering
    def jitter(self, agent):
        target = (np.random.random(size=3) - 0.5) * 10
        target[2] = 0
        target += agent.coordinates
        self.move_toward(agent, target)

    # move agent within [min_dist, max_dist] from target, where target = [x, y, z]
    def move_threshold(self, agent, target, min_dist, max_dist):
        n_vec = np.array(agent.coordinates) - target
        n_dist = np.linalg.norm(n_vec)

        if n_dist > max_dist:
            nn_target = n_vec / (n_dist + self.EPS) * max_dist + target
            return self.move_toward(agent, nn_target)

        if n_dist < min_dist:
            nn_target = n_vec / (n_dist + self.EPS) * min_dist + target
            return self.move_toward(agent, nn_target)

        return False

    # move agent within [min_dist, max_dist] from x, y
    def move_threshold_xy(self, agent, x, y, min_dist, max_dist):
        target = np.array([x, y, 0])
        return self.move_threshold(agent, target, min_dist, max_dist)

    # move agent to within [min_dist, max_dist] from agent2
    def move_threshold_agent(self, agent, agent2, min_dist, max_dist):
        target = agent2.coordinates
        return self.move_threshold(agent, target, min_dist, max_dist)

    # returns lists of offense and defense drones "visible" to the agent TODO should be provided as datapoint
    def get_local_agents(self, world, agent, offense_drones, defense_drones):
        local_offense = []
        local_defense = []

        x2, y2 = agent.coordinates[0], agent.coordinates[1]
        for o in offense_drones:
            x1, y1 = o.coordinates[0], o.coordinates[1]
            dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=self.COMMS_MODEL,
                                                   DISK_RANGE_M=self.DISK_RANGE)  # TODO fix
            if (comm_range):
                local_offense.append(o)
        for d in defense_drones:
            x1, y1 = d.coordinates[0], d.coordinates[1]
            dist, comm_range = communication_model(x1, y1, x2, y2, comms_model=self.COMMS_MODEL,
                                                   DISK_RANGE_M=self.DISK_RANGE)
            if (comm_range):
                local_defense.append(d)

        return local_offense, local_defense


class Observations:
    def __init__(self, offense, defense):
        self.offense_drones = offense
        self.defense_drones = defense

