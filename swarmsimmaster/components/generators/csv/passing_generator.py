from components.generators.csv.csv_generator import CsvAgentFile
from components.generators.csv.csv_generator import CsvAgentData
import csv
import pandas as pd
import logging
import os


#WARNING: this logger does not log


class CsvRoundData:
    def __init__(self, task=0, scenario=0, solution=0, seed=20, directory="outputs/", agents=None):
        pass


    def update_agent_num(self, agent):
        pass

    def update_items_num(self, item):
        pass

    def update_locations_num(self, act_locations_num):
        pass

    def success(self):
        pass
    def update_metrics(self, steps=0,
                       agent_read=0, item_read=0, location_read=0, memory_read=0,
                       agent_write=0, item_write=0, location_write=0, memory_write=0,
                       agents_created=0, items_created=0, location_created=0,
                       agents_deleted=0, items_deleted=0, location_deleted=0, items_taken=0, items_dropped=0,
                       agents_taken=0, agents_dropped=0):
        pass

    def next_line(self, sim_round, agents=None):
        pass
        

    def aggregate_metrics(self):
        pass

    def all_aggregate_metrics(self):
       pass