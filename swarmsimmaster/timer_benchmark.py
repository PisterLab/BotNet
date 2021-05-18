import subprocess
import os
import numpy as np

child_processes = []
process_cnt = 0

scenario_file = "timer_sce"
solution_file = "timer_sol"
max_round = 500
seed_start = 122
trials_per_config = os.cpu_count()
rounds_per_trial = 101

model = "pister_hack"
AGENT_NUMS = [1, 5, 10, 25, 50, 100, 250, 500]

for num_agents in AGENT_NUMS:
    for seed in range(seed_start, seed_start + trials_per_config):
        process = ("python", "swarmsim.py", "--scenario", scenario_file,
                                            "--solution", solution_file,
                                            "--comms", model,
                                            "--num_agents", str(num_agents),
                                            "-n", str(rounds_per_trial),
                                            "-r", str(seed))
        print(process)
        p = subprocess.Popen(process)
        child_processes.append(p)
        process_cnt += 1
        print(f"Process #{process_cnt} started - {process}")
        if len(child_processes) == os.cpu_count():
            for cp in child_processes:
                cp.wait()
            child_processes.clear()
    for cp in child_processes:
        cp.wait()









