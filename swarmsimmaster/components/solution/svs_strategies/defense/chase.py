import numpy as np

from ..svs_strategy_template import SVSStrategy


class Chase(SVSStrategy):
    def run(self, observations):
        ret = []
        sorted_offense = sorted(observations.offense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(observations.defense_center)))
        for a in observations.defense_drones:
            closest_offense = sorted_offense[0]
            ret.append((a, closest_offense.coordinates))
        return ret
