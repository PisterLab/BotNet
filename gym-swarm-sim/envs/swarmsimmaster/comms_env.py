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



def read_cmd_args(config_data, argv=[]):
    try:
        opts, args = getopt.getopt(argv, "hs:w:r:n:m:d:v:", ["solution=", "scenario="])
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



def generate_data(config_data, swarm_sim_world):
    swarm_sim_world.csv_aggregator()
    plt_gnrtr = importlib.import_module('components.generators.plot.%s' % config_data.plot_generator)
    plt_gnrtr.plot_generator(config_data.directory_csv, config_data.directory_plot )


def get_solution(config_data):
    return importlib.import_module('components.solution.' + config_data.solution)


def get_scenario(config_data):
    return importlib.import_module('components.scenario.' + config_data.scenario)

##threading with the passing of initial conditions
class SwarmSimCommsEnv():
    def __init__(self, goons=[(0,0,0)]):

        #get config data
        self.config_data = config.ConfigData()

        #set up logging
        unique_descriptor = "%s_%s_%s" % (self.config_data.local_time,
                                          self.config_data.scenario.rsplit('.', 1)[0],
                                          self.config_data.solution.rsplit('.', 1)[0])

        logging.basicConfig(filename="outputs/logs/system_%s.log" % unique_descriptor, filemode='w',
                            level=logging.INFO, format='%(message)s')
        logging.info('Started')

        read_cmd_args(self.config_data)

        create_directory_for_data(self.config_data, unique_descriptor)
        random.seed(self.config_data.seed_value)

        #set up world
        self.swarm_sim_world = world.World(self.config_data)
        self.swarm_sim_world.init_scenario(get_scenario(self.swarm_sim_world.config_data))

    def main_loop(self, iterations=1):
        round_start_timestamp = time.perf_counter()  # TODO: work with this
        # keep simulation going if set to infinite or there are still rounds left
        i = 0
        while i < iterations:
            try:
                # check to see if its neccessary to run the vis
                if self.config_data.visualization:
                    self.swarm_sim_world.vis.run(round_start_timestamp)
                # run the solution for 1 step
                self.run_solution()
            except ResetException: #need to improve exception handlng
                self.do_reset(self.swarm_sim_world)

            i += 1

    def end(self):
        ##TODO: Edit this because it is for end
        if self.config_data.visualization:
            try:
                self.swarm_sim_world.vis.run(round_start_timestamp)
                while not self.config_data.close_at_end:
                    self.swarm_sim_world.vis.run(round_start_timestamp)
            except ResetException:
                self.do_reset(self.swarm_sim_world)
                return True

        logging.info('Finished')
        self.generate_data(self.config_data, self.swarm_sim_world)

    #make a solution that just calculates where they are based on the velos
    def run_solution(self):
        if self.swarm_sim_world.config_data.agent_random_order_always:
            random.shuffle(self.swarm_sim_world.agents)
        get_solution(self.swarm_sim_world.config_data).solution(self.swarm_sim_world)
        self.swarm_sim_world.csv_round.next_line(self.swarm_sim_world.get_actual_round())
        self.swarm_sim_world.inc_round_counter_by(number=1)

    def do_reset(self):
        self.swarm_sim_world.reset()
        solution = get_solution(self.swarm_sim_world.config_data)
        scenario = get_scenario(self.swarm_sim_world.config_data)
        importlib.reload(solution)
        importlib.reload(scenario)
        self.swarm_sim_world.init_scenario(scenario)

    #will have to add functionality to make sure the velos are gud
    def assign_velos(self, new_velos):
        id_map = self.swarm_sim_world.get_agent_map_id()
        for mote in new_velos:
            id_map[mote].set_velocities(new_velos[mote])

    def get_all_mote_states(self):
        id_map = self.swarm_sim_world.get_agent_map_id()
        positions = {}
        for agent_id in id_map:
            mote = id_map[agent_id]
            positions[agent_id] = mote.coordinates #mb an access function in the agent class rather than this

        return positions



if __name__ == "__main__":
    test = SwarmSimCommsEnv()
    motes = test.get_all_mote_states().keys()
    velos = {}

    print(test.get_all_mote_states())
    while True:
        test.main_loop(100)
        for agent in motes:
            velos[agent] = ((random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0)))
            test.assign_velos(velos)


    