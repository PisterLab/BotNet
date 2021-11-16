from .closest_to_self_ut import ClosestToSelfUntargeted
from ..svs_strategy_template import SVSStrategy
import numpy as np


class SplitClosestRing(SVSStrategy):
    # Tweakable parameters
    DEF_RADIUS = 3
    n = 2
    TARGET_RAD = 0.25

    # half the drones follow def policy 3.5 as usual
    # other half only attack drones within `radius` of the center (following def policy n_closest_to_self)
    def run(self, obs):
        patrollers = []
        targetted = {}

        for i in range(len(obs.defense_drones) // 2):
            patrollers.append(obs.defense_drones[i])

        near_offense = list(
            filter(
                lambda x: (np.linalg.norm(np.array(x.coordinates) - np.array(self.DEFENSE_CENTER))) < self.DEF_RADIUS,
                obs.offense_drones))
        far_offense = list(
            filter(
                lambda x: (np.linalg.norm(np.array(x.coordinates) - np.array(self.DEFENSE_CENTER))) >= self.DEF_RADIUS,
                obs.offense_drones))

        for a in patrollers:
            sorted_near_offense = sorted(near_offense, key=lambda x: np.linalg.norm(
                np.array(x.coordinates) - np.array(a.coordinates)))

            flag = False
            for x in sorted_near_offense:
                if (targetted.setdefault(x.coordinates, 0) <= self.n) and np.linalg.norm(
                        np.array(x.coordinates) - np.array(self.DEFENSE_CENTER)) >= np.linalg.norm(
                        np.array(a.coordinates) - np.array(self.DEFENSE_CENTER)) - self.TARGET_RAD:
                    flag = True
                    targetted[x.coordinates] += 1
                    self.move_toward(a, x.coordinates)
                    break
            if not flag:
                if a.coordinates[0] <= self.DEFENSE_CENTER[0]:
                    self.move_toward(a, [self.DEFENSE_CENTER[0] + 1, a.coordinates[1], a.coordinates[2]])
                else:
                    self.move_threshold(a, self.DEFENSE_CENTER, 0, 1)

        if far_offense:
            ClosestToSelfUntargeted.run(obs.defense_drones[len(patrollers):],
                                        far_offense)
        else:
            ClosestToSelfUntargeted.run(obs.defense_drones[len(patrollers):], near_offense)
