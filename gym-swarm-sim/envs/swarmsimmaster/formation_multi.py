import subprocess
import os
import numpy as np


child_processes = []
process_cnt = 0

CIRCLE = False

scenario_file = "formation_line_sce"

if CIRCLE:
    solution_file = "formation_circ_sol"
else:
    solution_file = "formation_line_sol"

max_round = 500
seed_start = 122
seed_end = seed_start + os.cpu_count()

#ALL_MODELS = ["full", "disk", "friis_upper", "friis_average", "friis_lower", "pister_hack"]
ALL_MODELS = ["full", "disk", "friis_lower", "pister_hack"]
DISK_RANGES = [3, 10, 20]
AGENT_NUMS = [25, 50, 100, 150, 200, 250, 300]


# measuring convergence time and quality
for model in ALL_MODELS:
    if model == "disk":
        for q in DISK_RANGES:
            for num_agents in AGENT_NUMS:
                data_dir = "logs/line_" + model + "_" + str(q) + "_" + str(num_agents)
                os.mkdir(data_dir)
                for seed in range(seed_start, seed_end):
                    process = ("python", "swarmsim.py", "-r", str(seed),
                               "-v", str(0),
                               "-w", scenario_file,
                               "-s", solution_file,
                               "-n", str(max_round),
                               "-a", str(num_agents),  # num agents
                               "-x", model,  # comms model
                               "-z", data_dir,  # save_dir
                               "-q", str(q)) # comms range
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
    else:
        for num_agents in AGENT_NUMS:
            data_dir = "logs/line_" + model + "_" + str(num_agents)
            os.mkdir(data_dir)
            for seed in range(seed_start, seed_end):
                process = ("python", "swarmsim.py", "-r", str(seed),
                                                    "-v", str(0),
                                                    "-w", scenario_file,
                                                    "-s", solution_file,
                                                    "-n", str(max_round),
                                                    "-a", str(num_agents), # num agents
                                                    "-x", model, # comms model
                                                    "-z", data_dir) # save dir

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

for model in ALL_MODELS:
    for num_agents in AGENT_NUMS:
        data_dir = "logs/" + model + "_" + str(num_agents)
        data = []
        for f in os.listdir(data_dir):
            x = np.load(data_dir + "/" + f)
            data.append(x)
        data = np.array(data)
        print(np.mean(data, axis=0))
