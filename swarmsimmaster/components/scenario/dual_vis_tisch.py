import rpyc
import importlib

def scenario(world):
    print('A.2')
    #setup world information passed from 6tisch
    world.interface_server = rpyc.connect("localhost", 18861, config={'allow_public_attrs': True, 'allow_all_attrs': True, 'allow_pickle': True}).root
    while not world.interface_server.simulation_ready():
        continue
    print('simulation ready')
    args, kwargs = world.interface_server.get_initialization_args()
    print(args, kwargs)
    net_config = args[0]

    world.config_data.follow_the_leader = net_config['follow']
    world.config_data.flock_rad = net_config['flock_rad']
    world.config_data.flock_vel = net_config['flock_vel']
    world.config_data.seed_value = kwargs['seed']
    world.timestep = kwargs['timestep']

    #run scenario
    scenario_mod = importlib.import_module('components.scenario.' + world.config_data.scenario)
    if 'num_agents' in kwargs:
        scenario_mod.scenario(world, num_agents=kwargs['num_agents'])
    else:
        scenario_mod.scenario(world)

    #update server on world information
    id_map = world.get_agent_map_id()
    positions = {}
    for agent_id in id_map:
        mote = id_map[agent_id]
        positions[agent_id] = mote.coordinates

    world.interface_server.update_mote_states(positions)

    world.network_formed = False
    # wait for 6tisch to have set the sync as false
    while world.interface_server.synced():
        continue
    world.interface_server.set_sync(True)
    print('passed init sync')




