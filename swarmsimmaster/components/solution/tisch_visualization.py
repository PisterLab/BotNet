import random
import time
import importlib
def solution(world):
    #wait for command to run the main loop
    neighbors_set = False


    while not world.interface_server.should_loop():
        continue

    #decreases the loop queue by one
    world.interface_server.decrement_loop()

    #set neighbors
    if world.interface_server.should_set_neighbors():
        neighbors_set = True
        id_map = world.get_agent_map_id()
        agent_neighbor_table = world.interface_server.get_neighbors_table()
        mote_key_map = world.interface_server.get_mote_key_map()
        for (net_id, neighbors) in agent_neighbor_table:
            agent_id = mote_key_map[net_id]  # NOTE: this is set in the network simulator
            mote = id_map[agent_id]
            mote.id = agent_id  # FIXME: THIS IS DUMB BUT IT WORKS
            mote.neighbors = neighbors




    #assign velocities
    if world.interface_server.should_assign_velos():
        id_map = world.get_agent_map_id()
        new_velos = world.interface_server.get_new_velocities()
        for mote in new_velos:
            id_map[mote].set_velocities(new_velos[mote])

        # call second solution
    if neighbors_set:
        run_2nd_solution(world.config_data, world=world, net_id_map=mote_key_map)






    # if this was the last neccessary loop return control to 6tisch
    if not world.interface_server.should_loop():
        # update RPC on mote states
        id_map = world.get_agent_map_id()
        positions = {}
        for agent_id in id_map:
            mote = id_map[agent_id]
            positions[agent_id] = mote.coordinates

        world.interface_server.update_mote_states(positions)

        # wait for 6tisch to have set the sync as false
        while world.interface_server.synced():
            continue
        world.interface_server.set_sync(True)


def run_2nd_solution(config_data, **kwargs):
    importlib.import_module('components.solution.' + config_data.solution2).solution(**kwargs)
