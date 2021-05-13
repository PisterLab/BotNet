"""This is the main module of the Opportunistic Robotics Network Simulator"""
import importlib
import getopt
import logging
import os
import sys
import time
import random
import traceback
from core import world, config
from core.vis3d import ResetException


def swarm_sim(argv=[]):
    """In the main function first the config is getting parsed and than
    the swarm_sim_world and the swarm_sim_world item is created. Afterwards the run method of the swarm_sim_world
    is called in which the simulator is going to start to run"""
    config_data = config.ConfigData()

    unique_descriptor = "%s_%s_%s" % (config_data.local_time,
                                      config_data.scenario.rsplit('.', 1)[0],
                                      config_data.solution.rsplit('.', 1)[0])

    logging.basicConfig(filename="outputs/logs/system_%s.log" % unique_descriptor, filemode='w',
                        level=logging.INFO, format='%(message)s')
    logging.info('Started')

    read_cmd_args(config_data, argv)
    create_directory_for_data(config_data, unique_descriptor)
    random.seed(config_data.seed_value)
    swarm_sim_world = world.World(config_data)
    try:
        swarm_sim_world.init_scenario(get_scenario(swarm_sim_world.config_data),
                                      id=config_data.id, scenario=config_data.scenario_arg,
                                      num_agents=config_data.num_agents, seed=config_data.seed_value,
                                      comms=config_data.comms, flock_rad=config_data.flock_rad,
                                      flock_vel=config_data.flock_vel)
    except:
        traceback.print_exc()
        swarm_sim_world.init_scenario(get_scenario(swarm_sim_world.config_data))

    reset = True
    while reset:
        reset = main_loop(config_data, swarm_sim_world)

    logging.info('Finished')
    generate_data(config_data, swarm_sim_world)


def main_loop(config_data, swarm_sim_world):
    round_start_timestamp = time.perf_counter()
    #keep simulation going if set to infinite or there are still rounds left
    while (config_data.max_round == 0 or swarm_sim_world.get_actual_round() <= config_data.max_round) \
            and swarm_sim_world.get_end() is False:
        try:
            #check to see if its neccessary to run the vis
            if config_data.visualization:
                swarm_sim_world.vis.run(round_start_timestamp)
                round_start_timestamp = time.perf_counter()
            #run the solution for 1 step
            run_solution(swarm_sim_world)
        except ResetException:
            do_reset(swarm_sim_world)

    if config_data.visualization:
        try:
            swarm_sim_world.vis.run(round_start_timestamp)
            while not config_data.close_at_end:
                swarm_sim_world.vis.run(round_start_timestamp)
        except ResetException:
            do_reset(swarm_sim_world)
            return True
    return False


def do_reset(swarm_sim_world):
    swarm_sim_world.reset()
    solution = get_solution(swarm_sim_world.config_data)
    scenario = get_scenario(swarm_sim_world.config_data)
    importlib.reload(solution)
    importlib.reload(scenario)
    swarm_sim_world.init_scenario(scenario)


def read_cmd_args(config_data, argv=[]):
    try:
        opts, args = getopt.getopt(argv, "hs:w:r:n:m:d:v:",
                                   ["solution=", "scenario=",
                                    "init=", "comms=", "spacing=", "num_agents=",
                                    "flock_rad=", "flock_vel=",
                                    "run_id=", "follow=", "id="
                                    ])
    except getopt.GetoptError:
        print('Error: swarm-swarm_sim_world.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('swarm-swarm_sim_world.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
            sys.exit()
        if opt in ("-s", "--solution"):
            config_data.solution = arg
        if opt in ("-w", "--scenario"):
            config_data.scenario = arg
        if opt in ("-r", "--seed"):
            config_data.seed_value = int(arg)
        if opt in ("-n", "--maxrounds"):
            config_data.max_round = int(arg)
        if opt == "-m":
            config_data.multiple_sim = int(arg)
        if opt == "-v":
            config_data.visualization = int(arg)
        if opt == "-d":
            config_data.local_time = str(arg)
        if opt == "--comms":
            config_data.comms = arg
        if opt == "--init":
            config_data.scenario_arg = arg
        if opt == "--spacing":
            config_data.spacing = float(arg)
        if opt == "--num_agents":
            config_data.num_agents = int(arg)
        if opt == "--flock_rad":
            config_data.flock_rad = float(arg)
        if opt == "--flock_vel":
            config_data.flock_vel = float(arg)
        if opt == "--run_id":
            config_data.id = arg
        if opt == "--follow":
            config_data.follow = bool(int(arg))
        if opt == "--id":
            config_data.id = arg


def create_directory_for_data(config_data, unique_descriptor):
    if config_data.multiple_sim == 1:
        config_data.directory_name = "%s/%s" % (unique_descriptor, str(config_data.seed_value))

        config_data.directory_name = "./outputs/csv/mulitple/" + config_data.directory_name
        config_data.directory_plot = "./outputs/plot/mulitple/" + config_data.directory_name


    else:
        config_data.directory_name = "%s_%s" % (unique_descriptor, str(config_data.seed_value))

        config_data.directory_csv = "./outputs/csv/" + config_data.directory_name
        config_data.directory_plot = "./outputs/plot/" + config_data.directory_name
    if not os.path.exists(config_data.directory_csv):
        os.makedirs(config_data.directory_csv)
    if not os.path.exists(config_data.directory_plot):
        os.makedirs(config_data.directory_plot)

def run_solution(swarm_sim_world):
    if swarm_sim_world.config_data.agent_random_order_always:
        random.shuffle(swarm_sim_world.agents)
    get_solution(swarm_sim_world.config_data).solution(swarm_sim_world)
    swarm_sim_world.csv_round.next_line(swarm_sim_world.get_actual_round())
    swarm_sim_world.inc_round_counter_by(number=1)


def get_solution(config_data):
    return importlib.import_module('components.solution.' + config_data.solution)




def get_scenario(config_data):
    return importlib.import_module('components.scenario.' + config_data.scenario)


def generate_data(config_data, swarm_sim_world):
    swarm_sim_world.csv_aggregator()
    plt_gnrtr = importlib.import_module('components.generators.plot.%s' % config_data.plot_generator)
    plt_gnrtr.plot_generator(config_data.directory_csv, config_data.directory_plot )


if __name__ == "__main__":
    swarm_sim(sys.argv[1:])
