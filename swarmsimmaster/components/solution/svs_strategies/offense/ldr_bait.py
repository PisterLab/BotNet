from ..svs_strategy_template import SVSStrategy


class LeaderBait(SVSStrategy):
    # off policy 2: hand craft
    def run(self, obs):
        leaders = []
        total_leaders = min(len(obs.offense_drones), 20)

        for a in obs.offense_drones:
            if hasattr(a, "leader"):
                leaders.append(a)

        for i in range(total_leaders - len(leaders)):
            for a in obs.offense_drones:
                if not hasattr(a, "leader") and not hasattr(a, "sneaker"):
                    leaders.append(a)
                    a.leader = True
                    break

        for leader in leaders:
            self.move_toward(leader, (0, -100, 0))

        for i, a in enumerate(obs.offense_drones):
            if not hasattr(a, "leader"):
                self.move_toward(a, obs.defense_center)