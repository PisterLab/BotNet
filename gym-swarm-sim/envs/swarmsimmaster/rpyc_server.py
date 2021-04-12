from comms_env import SwarmSimCommsEnv
import rpyc
from rpyc.utils.server import ThreadedServer
import multiprocessing
class MyService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        print("success fully connected to RPC")
        pass

    def exposed_set_mote_key_map(self, mote_map, inv=False):
        self.exposed_simulation.mote_key_map = mote_map
        if inv:
            self.exposed_simulation.mote_key_inv_map = {v : k for (k, v) in mote_map.items()}

    def exposed_get_mote_key_map(self):
        return self.exposed_simulation.mote_key_map

    def exposed_get_mote_key_inv_map(self):
        return self.exposed_simulation.mote_key_inv_map

    def exposed_initialize_simulation(self, *args, **kwargs):
        print(args, kwargs)
        self.exposed_simulation = SwarmSimCommsEnv(*args, **kwargs)
        print("Successfully initialized simulation")

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def exposed_main_loop(self, iterations=1):
        return self.exposed_simulation.main_loop(iterations)

    def exposed_end(self):
        return self.exposed_simulation.end()

    def exposed_do_reset(self):
        self.exposed_simulation.do_reset()

    def exposed_assign_velos(self, new_velos):
        self.exposed_simulation.assign_velos(new_velos)

    def exposed_set_all_mote_neighbors(self, agent_neighbor_dict):
        self.exposed_simulation.set_all_mote_neighbors(agent_neighbor_dict)

    def exposed_get_all_mote_states(self):
        print("Fetching mote states")
        states = self.exposed_simulation.get_all_mote_states()
        return self.exposed_simulation.get_all_mote_states()

if __name__ == "__main__":

    t = ThreadedServer(MyService, port=18861, protocol_config={'allow_public_attrs': True, 'allow_all_attrs': True})
    t.start()
