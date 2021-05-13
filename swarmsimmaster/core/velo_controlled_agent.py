
import importlib
import logging
from core import matter
from core.swarm_sim_header import *
from core import agent
import numpy as np

DEFAULTS = {"flock_rad" : 20, "flock_vel" : 5, "collision_rad" : 0.8, "csv_mid" : "custom"}
VELOCITY_CAP = 30
CAPPED_VELS = True
TIMESTEP= 0.1 #Approximation of a slotframe

class VeloAgent(agent.Agent):
    def __init__(self, world, coordinates, color, agent_counter=0, velocities = None):
        super().__init__(world, coordinates, color)
        self.velocities = (0.0,) * 3 # self.world.grid.get_dimension_count()
        self.neighbors = []

        try:
            self.timestep = self.world.timestep
        except:
            self.timestep = TIMESTEP

    # change in time is one round
    # function adds the velo to the position

    # TODO: Refactor with the parent class to remove the code written twice.
    def move(self):
        '''
        moves agent according to current velocity,
        '''
        #check to make sure that this doesnt throw an error and conforms to grid types.
        direction_coord = tuple(np.add(np.array(self.velocities) * self.timestep, self.coordinates))
        direction_coord = self.check_within_border(self.velocities, direction_coord)
        if self.world.grid.are_valid_coordinates(direction_coord) \
                and direction_coord not in self.world.agent_map_coordinates \
                and not self._Agent__isCarried: # this is a little jank IK
            if self.coordinates in self.world.agent_map_coordinates:
                del self.world.agent_map_coordinates[self.coordinates]
            self.coordinates = direction_coord
            self.world.agent_map_coordinates[self.coordinates] = self
            if self.world.vis is not None:
                self.world.vis.agent_changed(self)
            logging.info("Agent %s successfully moved to %s", str(self.get_id()), self.coordinates)
            self.world.csv_round.update_metrics(steps=1)
            self.csv_agent_writer.write_agent(steps=1)
            self.check_for_carried_matter()
            return True

        return False

    def move_coord(self, coordinates):
        '''
        moves agent to provided coordinates
        '''
        if self.world.grid.are_valid_coordinates(coordinates) \
                and not self._Agent__isCarried: # this is a little jank IK
            if self.coordinates in self.world.agent_map_coordinates:
                del self.world.agent_map_coordinates[self.coordinates]
            self.coordinates = coordinates
            self.world.agent_map_coordinates[self.coordinates] = self
            if self.world.vis is not None:
                self.world.vis.agent_changed(self)
            logging.info("Agent %s successfully moved to %s", str(self.get_id()), self.coordinates)
            self.world.csv_round.update_metrics(steps=1)
            self.csv_agent_writer.write_agent(steps=1)
            self.check_for_carried_matter()
            return True

        return False

    # updates the velocities
    def set_velocities(self, new_velocities):
        if CAPPED_VELS:
            new_velocities = tuple([np.sign(vel) * min(abs(vel), VELOCITY_CAP) for vel in new_velocities])
        self.velocities = tuple(np.hstack([np.array(new_velocities), np.zeros(1)])[:3])

    # adds to the velocities.
    def add_velocities(self, dv):
        self.velocities = tuple(np.add(self.velocities, dv))
