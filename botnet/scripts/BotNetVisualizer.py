if __name__ == "__main__":
    from multiprocessing import Manager
    import copy
    import rpyc
    from rpyc.utils.server import ThreadedServer

    shared_dictionary = Manager().dict()
    shared_dictionary.update({
            'loop_counter' : 0,
            'simulation_end' : False,
            'do_reset' : False,
            'simulation_initialized' : False,
            'synced' : False
            })


    class MyService(rpyc.Service):
        # SET SWARM SIM ATTRIBUTES

        def exposed_initialize_simulation(self, *args, **kwargs):
            shared_dictionary.update({
                'scenario_args' : args,
                'scenario_kwargs' : kwargs,
                'simulation_initialized' : True
            })

        def exposed_simulation_ready(self):
            return shared_dictionary.get( 'simulation_initialized')

        def exposed_get_initialization_args(self):
            return shared_dictionary.get('scenario_args'), shared_dictionary.get('scenario_kwargs')

        def exposed_set_mote_key_map(self, mote_map, inv=False):
            shared_dictionary.update({'mote_key_map' : mote_map})
            if inv:
                shared_dictionary.update({'mote_key_in_map' : {v : k for (k, v) in mote_map.items()}})

        def exposed_main_loop(self, iterations=1):
            shared_dictionary.update({'loop_counter' : iterations})

        def exposed_should_loop(self):
            return (shared_dictionary.get('loop_counter') > 0)

        def exposed_decrement_loop(self):
            loops = shared_dictionary.get('loop_counter')
            if loops > 0:
                loops -= 1
                shared_dictionary.update({'loop_counter': loops})

        def exposed_assign_velos(self, new_velos):
            shared_dictionary.update({
                'assign_velos' : True,
                'new_velos' : copy.deepcopy(new_velos)
            })

        def exposed_should_assign_velos(self):
            return shared_dictionary.get('assign_velos')

        def exposed_get_new_velocities(self):
            shared_dictionary.update({'assign_velos': False})
            return shared_dictionary.get('new_velos')

        def exposed_set_all_mote_neighbors(self, agent_neighbor_dict):
            shared_dictionary.update({
                'set_mote_neighbors': True,
                'agent_neighbor_dict': copy.deepcopy(agent_neighbor_dict)
            })

        def exposed_should_set_neighbors(self):
            return shared_dictionary.get('set_mote_neighbors')

        def exposed_get_neighbors_table(self):
            shared_dictionary.update({'set_mote_neighbors': False})
            return shared_dictionary.get('agent_neighbor_dict')

        def exposed_get_mote_key_map(self):
            return shared_dictionary.get('mote_key_map')

        def exposed_get_mote_key_inv_map(self):
            return shared_dictionary.get('mote_key_inv_map')

        # def exposed_initialize_simulation(self, *args, **kwargs):
        #     print(args, kwargs)
        #     self.exposed_simulation = SwarmSimCommsEnv(*args, **kwargs)
        #     print("Successfully initialized simulation")


        def exposed_get_all_mote_states(self):
            return shared_dictionary.get('mote_states')

        def exposed_update_mote_states(self, mote_states):
            shared_dictionary.update({'mote_states': copy.deepcopy(mote_states) })

        def on_disconnect(self, conn):
            # code that runs after the connection has already closed
            # (to finalize the service, if needed)
            pass

        def exposed_set_sync(self, status):
            '''
            Lets both sides of the service comminicate when the other side is done.
            '''
            shared_dictionary.update({'synced': status})

        def exposed_synced(self):
            return shared_dictionary.get('synced')



    t = ThreadedServer(MyService, port=18861,
                           protocol_config={'allow_public_attrs': True, 'allow_all_attrs': True, 'allow_pickle': True})
    t.start()
