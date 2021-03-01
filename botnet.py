"""This is the main module interfacing between SwarmSim and 6TiSCH"""
import importlib
import getopt
import logging
import os
import sys

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

# TODO: take RPC vs. no-viz option (Monte Carlo is always no-viz, but can do post-viz)
# TODO: this should take command line arguments and pass as a config_data object to 6tisch and swarmsim