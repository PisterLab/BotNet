import rpyc


def scenario(world):
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
    goons = kwargs['goons']
    world.timestep = kwargs['timestep']
# These are for logging which we will get to
  # seed = kwargs['seed']
  # update_period = self.kwargs['update_period']
    if goons:
        for agent in goons:
            world.add_agent(agent)
    else:
        world.add_agent(world.grid.get_center())



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




