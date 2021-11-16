from ..svs_strategy_template import SVSStrategy


class DirectCenter(SVSStrategy):
    # go to center directly
    def run(self, observations):
        for a in observations.offense_drones:
            self.move_toward(a, observations.defense_center)
