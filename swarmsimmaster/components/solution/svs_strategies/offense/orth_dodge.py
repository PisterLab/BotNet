from ..svs_strategy_template import SVSStrategy
import numpy as np


class OrthDodge(SVSStrategy):
    def run(self, obs):
        """Dodges defense drones by moving orthogonally when within a certain range of said drone type."""
        # Tunable Parameters
        dodge_dist = 4
        dive_dist = 4
        crit_dist = 1
        crit_locked_on = 1
        dodge_angle = lambda x: min(90, max(80, 3 * 90 / x))
        # dodge_angle = lambda x: 90

        # Other variables
        obj_vec = np.array(self.DEFENSE_CENTER)

        for a in obs.offense_drones:
            a_vec = np.array(a.coordinates)
            obj_dist = np.linalg.norm(obj_vec - a_vec)
            sorted_defense = sorted(obs.defense_drones, key=lambda a: np.linalg.norm(np.array(a.coordinates) - a_vec))
            closest_def_vec = np.array(sorted_defense[0].coordinates)

            # if close enough to objective or at least closer to objective than closest defense drone, move toward objective
            if obj_dist < dive_dist or obj_dist < np.linalg.norm(obj_vec - closest_def_vec):
                self.move_toward(a, self.DEFENSE_CENTER)
            # if there are more than CRIT_LOCKED_ON defense drones within a CRIT_DIST distance, start moving away
            elif self.num_in_range(a, sorted_defense, crit_dist) >= crit_locked_on:
                self.move_toward(a, 2 * a_vec - closest_def_vec)
            # if the closest defending drone is within the DODGE_DIST distance, move orthogonally
            elif np.linalg.norm(closest_def_vec - a_vec) <= dodge_dist:
                self.move_toward(a, a_vec + self.dodge_vec(a, sorted_defense, dodge_angle(obj_dist)))
            # by default, move towards objective
            else:
                self.move_toward(a, self.DEFENSE_CENTER)

    def dodge_vec(self, agent, sorted_agents, angle=90):
        """Returns a vector to dodge towards.

        @param agent: the agent to move
        @param sorted_agents: the sorted list of agents to dodge
        @param angle: the angle at which to dodge
        @return: a numpy vector in 3D
        """
        u = np.array(sorted_agents[0].coordinates) - np.array(agent.coordinates)
        u = u / np.linalg.norm(u)
        v = np.array(self.DEFENSE_CENTER)
        w = v - (v @ u) * u
        w = w / np.linalg.norm(w)
        return 10 * (np.sin(angle * np.pi / 180) * w + np.cos(angle * np.pi / 180) * u)

    def num_in_range(self, agent, agent_list, range):
        """Returns the number of agents within a range (inclusive) of a given agent.

        @param agent: the agent to check around
        @param agent_list: the agents to check for
        @return: (int)
        """
        num = 0
        for a in agent_list:
            if np.linalg.norm(np.array(agent.coordinates) - np.array(a.coordinates)) <= range:
                num += 1
        return num
