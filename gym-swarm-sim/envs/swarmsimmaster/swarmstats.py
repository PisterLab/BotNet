"""This wrapper repeatedly runs simulations and aggregates statistics for the winrate."""
import sys
import swarmsim as ss
import matplotlib as plt

class StatTracker:
    def __init__(self):
        self.wins = 0
        self.losses = 0

    def swarm_stats(self, trials):
        for _ in range(trials):
            ss.do_reset(ss.swarm_sim(stats=self))
            print("Wins = " + str(self.wins), "Losses = " + str(self.losses))
        
        print("Total winrate = " + str(self.wins / trials * 100) + "%")

    def increment_wins(self):
        self.wins += 1
    def increment_losses(self):
        self.losses += 1

if __name__ == "__main__":
    stats = StatTracker()
    stats.swarm_stats(int(sys.argv[1]))