from components.generators.csv.csv_generator import CsvAgentFile
from components.generators.csv.csv_generator import CsvAgentData
import csv
import pandas as pd
import logging
import os


#WARNING: If you use this logger, then you cannot dynamically add agents during simulation
#WARNING: IF you use this logger random agent order must be turned off


class CsvRoundData:
    def __init__(self, task=0, scenario=0, solution=0, seed=20, directory="outputs/", agents=None):
        self.task = task
        self.scenario = scenario
        self.solution = solution
        self.actual_round = 1
        self.seed = seed
        self.steps = 0
        self.steps_sum = 0
        self.agents_created = 0
        self.agents_deleted = 0
        self.agent_num = 0
        self.agent_read = 0
        self.agent_write = 0
        self.items_created = 0
        self.items_deleted = 0
        self.item_num = 0
        self.item_read = 0
        self.item_write = 0
        self.locations_num = 0
        self.location_read = 0
        self.location_write = 0
        self.location_created = 0
        self.location_deleted = 0
        self.memory_read = 0
        self.memory_write = 0
        self.agents_created_sum = 0
        self.agents_deleted_sum = 0
        self.agent_read_sum = 0
        self.agent_write_sum = 0
        self.agents_taken = 0
        self.agents_dropped = 0
        self.agents_taken_sum = 0
        self.agents_dropped_sum = 0
        self.items_created_sum = 0
        self.items_deleted_sum = 0
        self.item_read_sum = 0
        self.item_write_sum = 0
        self.location_read_sum = 0
        self.location_write_sum = 0
        self.location_created_sum = 0
        self.location_deleted_sum = 0
        self.memory_read_sum = 0
        self.memory_write_sum = 0
        self.success_round = 0
        self.success_counter = 0
        self.items_taken = 0
        self.items_dropped = 0
        self.items_taken_sum = 0
        self.items_dropped_sum = 0
        self.directory = directory
        self.file_name = directory + '/rounds.csv'
        self.csv_file = open(self.file_name, 'w', newline='')
        self.writer_round = csv.writer(self.csv_file)

        csv_row = ['',]
        if agents is not None:
            for agent in agents:
                id = agent.get_id()
                csv_row.append(f"{id} pos")
                csv_row.append(f"{id} velos")

        self.writer_round.writerow(csv_row)


    def update_agent_num(self, agent):
        self.agent_num = agent

    def update_items_num(self, item):
        self.item_num = item

    def update_locations_num(self, act_locations_num):
        self.locations_num = act_locations_num

    def success(self):
        self.success_counter = self.success_counter + 1

    def update_metrics(self, steps=0,
                       agent_read=0, item_read=0, location_read=0, memory_read=0,
                       agent_write=0, item_write=0, location_write=0, memory_write=0,
                       agents_created=0, items_created=0, location_created=0,
                       agents_deleted=0, items_deleted=0, location_deleted=0, items_taken=0, items_dropped=0,
                       agents_taken=0, agents_dropped=0):
        logging.debug("CSV: Starting writing_rounds")
        self.location_created_sum = self.location_created_sum + location_created
        self.location_deleted_sum = self.location_deleted_sum + location_deleted
        self.location_read_sum = self.location_read_sum + location_read
        self.location_write_sum = self.location_write_sum + location_write
        self.agents_created_sum = self.agents_created_sum + agents_created
        self.agents_deleted_sum = self.agents_deleted_sum + agents_deleted
        self.agent_read_sum = self.agent_read_sum + agent_read
        self.steps_sum = self.steps_sum + steps
        self.agent_write_sum = self.agent_write_sum + agent_write
        self.memory_write_sum = self.memory_write_sum + memory_write
        self.memory_read_sum = self.memory_read_sum + memory_read
        self.items_created_sum = self.items_created_sum + items_created
        self.items_deleted_sum = self.items_deleted_sum + items_deleted
        self.items_dropped_sum = self.items_dropped_sum + items_dropped
        self.item_read_sum = self.item_read_sum + item_read
        self.items_taken_sum = self.items_taken_sum + items_taken
        self.item_write_sum = self.item_write_sum + item_write
        self.agents_taken_sum = self.agents_taken_sum + agents_taken
        self.agents_dropped_sum = self.agents_dropped_sum + agents_dropped

        self.steps = self.steps + steps
        self.agent_read = self.agent_read + agent_read
        self.item_read = self.item_read + item_read
        self.location_read = self.location_read + location_read
        self.memory_read = self.memory_read + memory_read
        self.agent_write = self.agent_write + agent_write
        self.item_write = self.item_write + item_write
        self.location_write = self.location_write + location_write
        self.memory_write = self.memory_write + memory_write
        self.agents_created = self.agents_created + agents_created
        self.items_created = self.items_created + items_created
        self.location_created = self.location_created + location_created
        self.agents_deleted = self.agents_deleted + agents_deleted
        self.items_deleted = self.items_deleted + items_deleted
        self.location_deleted = self.location_deleted + location_deleted
        self.items_dropped = self.items_dropped + items_dropped
        self.items_taken = self.items_taken + items_taken
        self.agents_taken = self.agents_taken + agents_taken
        self.agents_dropped = self.agents_dropped + agents_dropped
        logging.debug("CSV: Ending writing_rounds")

    def next_line(self, sim_round, agents=None):
        csv_iterator = ['',]
        if agents is not None:
            for agent in agents:
                csv_iterator.append(f"{agent.coordinates}")
                csv_iterator.append(f"{agent.velocities}")


        self.writer_round.writerow(csv_iterator)
        

    def aggregate_metrics(self):
        pass

    def all_aggregate_metrics(self):
       pass