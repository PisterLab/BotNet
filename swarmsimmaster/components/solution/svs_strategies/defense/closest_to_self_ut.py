import numpy as np

from ..svs_strategy_template import SVSStrategy


class ClosestToSelfUntargeted(SVSStrategy):
    # go to the closest guy from YOU that is non-targeted
    # if all targeted, go to the closest attacker from center
    def get_actions(self, obs):
        ret = []
        targeted = []

        for a in obs.defense_drones:
            self_sorted_offense = sorted(obs.offense_drones, key=lambda x: np.linalg.norm(
                np.array(x.coordinates) - np.array(a.coordinates)))

            flag = False
            for x in self_sorted_offense:
                if x.coordinates not in targeted:
                    flag = True
                    targeted.append(x.coordinates)
                    ret.append((a, x.coordinates))
                    break
            if not flag:
                sorted_offense = sorted(obs.offense_drones,
                                        key=lambda x: np.linalg.norm(
                                            np.array(x.coordinates) - np.array(self.defense_center)))
                closest_offense = sorted_offense[0]
                ret.append((a, closest_offense.coordinates))
        return ret