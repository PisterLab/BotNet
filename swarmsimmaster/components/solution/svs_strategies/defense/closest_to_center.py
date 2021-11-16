import numpy as np

from ..svs_strategy_template import SVSStrategy

class ClosestToCenter(SVSStrategy):
    # def policy 1: go to closest attacker to center
    def run(self, obs):
        sorted_offense = sorted(obs.offense_drones,
                                key=lambda x: np.linalg.norm(np.array(x.coordinates) - np.array(self.defense_center)))
        for a in obs.defense_drones:
            closest_offense = sorted_offense[0]
            self.move_toward(a, closest_offense.coordinates)