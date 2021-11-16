import numpy as np

from ..svs_strategy_template import SVSStrategy


class NClosestToSelfUntargeted(SVSStrategy):
    # Tweakable parameters
    n = 1
    TARGET_RAD = 0.25

    # slight modification of 'closest_to_self_ut'
    # go to the closest guy from YOU that is *reachable*,
    # with at most `n` other defenders targeting
    # if all targeted, go to the closest attacker from center
    def run(self, obs):
        targeted = {}

        for a in obs.defense_drones:
            self_dist = np.linalg.norm(np.array(a.coordinates) - np.array(obs.defense_center))
            self_sorted_offense = sorted(obs.offense_drones, key=lambda x: np.linalg.norm(
                np.array(x.coordinates) - np.array(a.coordinates)))

            flag = False
            for x in self_sorted_offense:
                off_dist = np.linalg.norm(np.array(x.coordinates) - np.array(obs.defense_center))
                if (targeted.setdefault(x.coordinates, 0) <= self.n) and off_dist >= self_dist - self.TARGET_RAD:
                    flag = True
                    targeted[x.coordinates] += 1
                    self.move_toward(a, x.coordinates)
                    break
            if not flag:
                sorted_offense = sorted(obs.offense_drones,
                                        key=lambda x: np.linalg.norm(
                                            np.array(x.coordinates) - np.array(self.defense_center)))
                closest_offense = sorted_offense[0]
                self.move_toward(a, closest_offense.coordinates)
