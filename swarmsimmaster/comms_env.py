"""This is the main module interfacing between SwarmSim and 6TiSCH"""
import importlib
import getopt
import logging
import os
import sys
import time
import random
import pandas as pd
import numpy as np
from core import world, config
from core.vis3d import ResetException

def read_cmd_args(config_data, argv=[]):
    try:
        opts, args = getopt.getopt(argv, "hs:w:r:n:m:d:v:",
                                   ["solution=", "scenario=",
                                    "init=", "comms=", "spacing=", "num_agents=",
                                    "flock_rad=", "flock_vel=",
                                    "run_id=", "follow="])

    except getopt.GetoptError:
        print('Error: comms_env.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('comms_env.py -r <seed> -w <scenario> -s <solution> -n <maxRounds>')
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
        elif opt in "--comms":
            config_data.comms_model = arg
        elif opt in "--init":
            config_data.scenario_arg = arg
        elif opt in "--spacing":
            config_data.spacing = float(arg)
        elif opt in "--num_agents":
            config_data.num_agents = int(arg)
        elif opt in "--flock_rad":
            config_data.flock_rad = float(arg)
        elif opt in "--flock_vel":
            config_data.flock_vel = float(arg)
        elif opt in "--run_id":
            config_data.id = arg
        elif opt in "--follow":
            config_data.follow = bool(int(arg))


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
    PANDAS_LOG = False

    def __init__(self, net_config, num_agents=1, timestep=0.010, seed=None, update_period=None):
        if update_period is None:
            update_period = len(goons)

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
        if seed is not None:
            self.config_data.seed_value = seed
        # random.seed(seed)
        # TODO : Move this to be different lol
        self.config_data.follow_the_leader = net_config.follow
        self.config_data.flock_rad = net_config.flock_rad
        self.config_data.flock_vel = net_config.flock_vel
        self.config_data.conn_class = net_config.conn_class
        self.config_data.num_agents = num_agents

        #set up world
        self.swarm_sim_world = world.World(self.config_data)
        self.swarm_sim_world.timestep = timestep
        self.swarm_sim_world.init_scenario(get_scenario(self.swarm_sim_world.config_data), num_agents=num_agents)
        self.swarm_sim_world.network_formed = False
        self._init_log(id="custom", scenario=self.config_data.scenario, num_agents=num_agents,
                       seed=self.config_data.seed_value, comms=net_config.conn_class,
                       flock_rad=net_config.flock_rad, flock_vel=net_config.flock_vel,
                       update_period=update_period
                       )

    def main_loop(self, iterations=1):
        round_start_timestamp = time.perf_counter()  # TODO: work with this
        # keep simulation going if set to infinite or there are still rounds left
        i = 0
        while i < iterations: # TODO: for i in range(iterations)
            i += 1
            try:
                # check to see if its necessary to run the vis
                self.swarm_sim_world.net_id_map = self.mote_key_map
                if self.config_data.visualization:
                    self.swarm_sim_world.vis.run(round_start_timestamp) # FIXME: seg fault when visualization enabled with 6TiSCH
                # run the solution for 1 step
                self.run_solution()

                self._log()
            except ResetException: # TODO: need to improve exception handling
                self.do_reset()
                return False



        return True

    def end(self):
        # TODO: Edit this because it is for end
        if self.config_data.visualization:
            try:
                self.swarm_sim_world.vis.run(round_start_timestamp)
                while not self.config_data.close_at_end:
                    self.swarm_sim_world.vis.run(round_start_timestamp)
            except ResetException:
                self.do_reset()
                return True

        logging.info('Finished')
        self.generate_data(self.config_data, self.swarm_sim_world)

    #make a solution that just calculates where they are based on the velos
    def run_solution(self):
        if self.swarm_sim_world.config_data.agent_random_order_always:
            random.shuffle(self.swarm_sim_world.agents)
        get_solution(self.swarm_sim_world.config_data).solution(self.swarm_sim_world)
        self.swarm_sim_world.csv_round.next_line(self.swarm_sim_world.get_actual_round(), self.swarm_sim_world.agents)
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

    def get_mote_key_map(self):
        return self.mote_key_map

    def get_mote_key_inv_map(self):
        return self.mote_key_inv_map

    def set_mote_key_map(self, mote_map, inv=False):
        self.mote_key_map = mote_map
        if inv:
            self.mote_key_inv_map = {v : k for (k, v) in mote_map.items()}

    def set_all_mote_neighbors(self, agent_neighbor_table):
        self.swarm_sim_world.network_formed = True
        id_map = self.swarm_sim_world.get_agent_map_id()
        for (net_id, neighbors) in agent_neighbor_table:
            agent_id = self.mote_key_map[net_id] # NOTE: this is set in the network simulator
            mote = id_map[agent_id]
            mote.id = agent_id #FIXME: THIS IS DUMB BUT IT WORKS
            mote.neighbors = neighbors

        self.swarm_sim_world.net_id_map = self.mote_key_map


    def get_all_mote_states(self):
        id_map = self.swarm_sim_world.get_agent_map_id()
        positions = {}
        for agent_id in id_map:
            mote = id_map[agent_id]
            positions[agent_id] = mote.coordinates

        return positions

    def _init_log(self, id = "custom", scenario = "basic", num_agents = 3, seed = 122, comms = "full", flock_rad = 20, flock_vel = 5, update_period = 12):
        if self.PANDAS_LOG:
            cols = []
            for agent in self.swarm_sim_world.get_agent_list():
                cols.append(agent.get_id())
            self.results_df = pd.DataFrame(columns=cols)
        else:
            csv_path = f'./outputs/csv/{id}/{scenario}/{num_agents}/{seed}/'
            # TODO: path difference for flocking

            if not os.path.exists(csv_path):
                os.makedirs(csv_path)

            self.csv_base = csv_path + f"{comms}-{float(flock_rad)}-{float(flock_vel)}-{float(update_period)}"

    def _log(self):
        if self.PANDAS_LOG:
            new_row = {}
            for agent in self.swarm_sim_world.get_agent_list():
                new_row[agent.get_id()] = agent.coordinates
            self.results_df = self.results_df.append(new_row, ignore_index=True)
        else:
            vels = []
            coords = []

            for agent in self.swarm_sim_world.get_agent_list():
                vels.append(np.array([np.array(v) for v in agent.velocities]))
                coords.append(np.array([np.array(c) for c in agent.coordinates]))

            csv_pos = f'{self.csv_base}-pos.dat'
            csv_vel = f'{self.csv_base}-vel.dat'
            with open(csv_pos, "ab") as fp, open(csv_vel, "ab") as fv:
                np.savetxt(fp, np.array(coords))
                np.savetxt(fv, np.array(vels))

if __name__ == "__main__": # TODO: mark as example
    test = SwarmSimCommsEnv()
    motes = test.get_all_mote_states().keys()
    velos = {}

    while True:
        test.main_loop(1)
        for agent in motes:
            velos[agent] = ((random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0)))
            test.assign_velos(velos)


    
