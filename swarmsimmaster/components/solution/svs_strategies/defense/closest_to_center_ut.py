import numpy as np

from ..svs_strategy_template import SVSStrategy

class ClosestToCenterUntargeted(SVSStrategy):
    # go to the closest non-targeted attacker from center
    # if all targeted, go to the closest attacker from center
    def run(self, obs):
        sorted_offense = sorted(obs.offense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(self.defense_center)))
        sorted_offense_cpy = sorted_offense.copy()

        for a in obs.defense_drones:
            if sorted_offense_cpy:
                closest_offense = sorted_offense_cpy.pop(0)
            else:
                closest_offense = sorted_offense[0]
            self.move_toward(a, closest_offense.coordinates)
