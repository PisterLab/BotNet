import sys, getopt, subprocess
from datetime import datetime
import os
import configparser
from itertools import product, chain

OLD_LOGGING = False

def main(argv):
    max_round = 1000
    seed_start = 122
    seed_end = seed_start + os.cpu_count()
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("config.ini")

    try:
        scenario_file = config.get ("File", "scenario")
    except (configparser.NoOptionError) as noe:
        scenario_file = "init_scenario.py"

    try:
        solution_file = config.get("File", "solution")
    except (configparser.NoOptionError) as noe:
        solution_file = "solution.py"

    n_time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')[:-1]
    try:
        opts, args = getopt.getopt(argv, "hs:w:r:n:v:", ["scenaro=", "solution="])
    except getopt.GetoptError:
        print('Error: multiple.py -r <randomeSeed> -w <scenario> -s <solution> -n <maxRounds>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('multiple.py -ss <seed_start> -se <seed_end> -w <scenario> -s <solution>  -n <maxRounds>')
            sys.exit()
        elif opt in ("-s", "--solution"):
            solution_file = arg
        elif opt in ("-w", "--scenario"):
            scenario_file = arg
        elif opt in ("-ss", "--seed_start"):
            seed_start = int(arg)
        elif opt in ("-se", "--seed_end"):
            seed_end = int(arg)
        elif opt in ("-n", "--maxrounds"):
            max_round = int(arg)

    # TODO: random seeds, monte carlo, etc.

    run_id = str(n_time).strip(":") + "_" + scenario_file.rsplit('.', 1)[0] + "_" + solution_file.rsplit('.', 1)[0]
    direction = "./outputs/csv/multiple/" + run_id
    if not os.path.exists(direction):
        os.makedirs(direction)
    out = open(direction + "/multiprocess.txt", "w")

    child_processes = []
    process_cnt = 0

    # NOTE: THIS IS WHERE YOU ITERATE THROUGH ARGUMENTS
    scenario_arguments = ["edge_line_flock"]
    comms_arguments = ["full", "friis_upper", "friis_average", "friis_lower", "pister_hack"]
    spacing = [2.0]
    FLOCK_START, FLOCK_END = 5, 100
    flock_rads = [5, 10, 20, 40, 80] # list(np.linspace(FLOCK_START, FLOCK_END, FLOCK_END - FLOCK_START + 1))
    flock_vels = [5.0] # [1, 5, 10, 20, 50]
    follow_bools = [1] # [0, 1]
    num_agents = [10]
    enumerated_params = (scenario_arguments, comms_arguments, spacing, flock_rads, flock_vels, follow_bools, num_agents)

    input(f"Press any key to run the following enumerations:\n\n{list(product(*enumerated_params))}.")

    for (init, comms, spacing, flock_rad, flock_vel, follow, num_agents) in product(*enumerated_params):
        for seed in range(seed_start, seed_end):
            process = ("python", "swarmsim.py",
                                    "-r", str(seed),
                                    "-v", str(0),
                                    "-w", scenario_file,
                                    "-s", solution_file,
                                    "-n", str(max_round),
                                    "-m", "1",
                                    "-d", str(n_time),
                                    "--init", init,
                                    "--comms", comms,
                                    "--spacing", str(spacing),
                                    "--num_agents", str(num_agents),
                                    "--flock_rad", str(flock_rad),
                                    "--flock_vel", str(flock_vel),
                                    "--follow", str(follow),
                                    "--run_id", str(run_id))
            # TODO: other args? env
            # TODO: follow the leader boolean
            p = subprocess.Popen(process, stdout=out, stderr=out)
            child_processes.append(p)
            process_cnt += 1
            print(f"Process #{process_cnt} started - {process}")
            if len(child_processes) == os.cpu_count():
                for cp in child_processes:
                    cp.wait()
                child_processes.clear()

    for cp in child_processes:
        cp.wait()


if __name__ == "__main__":
    main(sys.argv[1:])
