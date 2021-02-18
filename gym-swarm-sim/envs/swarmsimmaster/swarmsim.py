"""This is the main module of the Opportunistic Robotics Network Simulator"""
import importlib
import getopt
import logging
import os
import sys
import time
import random
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
        swarm_sim_world.init_scenario(get_scenario(swarm_sim_world.config_data), config_data.scenario_arg)
    except:
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
        opts, args = getopt.getopt(argv, "hs:w:r:n:m:d:v:x:y:z:", ["solution=", "scenario="])
    except getopt.GetoptError:
        print('Error: swarm-swarm_sim_world.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('swarm-swarm_sim_world.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
            sys.exit()
        elif opt in ("-s", "--solution"):
            config_data.solution = arg
        elif opt in ("-w", "--scenario"):
            config_data.scenario = arg
        elif opt in ("-r", "--seed"):
            config_data.seed_value = int(arg)
        elif opt in ("-n", "--maxrounds"):
            config_data.max_round = int(arg)
        elif opt in "-m":
            config_data.multiple_sim = int(arg)
        elif opt in "-v":
            config_data.visualization = int(arg)
        elif opt in "-d":
            config_data.local_time = str(arg)
        elif opt in "-x":
            config_data.solution_arg = arg
        elif opt in "-y":
            config_data.scenario_arg = arg
        elif opt in "-z":
            config_data.spacing = float(arg)


def create_directory_for_data(config_data, unique_descriptor):
    if config_data.multiple_sim == 1:
        config_data.directory_name = "%s/%s" % (unique_descriptor, str(config_data.seed_value))

        config_data.directory_csv = "./outputs/csv/mulitple/" + config_data.directory_name
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
    try:
        get_solution(swarm_sim_world.config_data).solution(swarm_sim_world, swarm_sim_world.config_data.solution_arg)
    except:
        get_solution(swarm_sim_world.config_data).solution(swarm_sim_world)
    swarm_sim_world.csv_round.next_line(swarm_sim_world.get_actual_round(), swarm_sim_world.get_agent_list())
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
