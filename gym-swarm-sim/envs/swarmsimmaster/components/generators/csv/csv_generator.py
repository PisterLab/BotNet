"""

TODO:
1- Order the names based on agents, locations, and items and transparencybetic
2- A new column called round_success
3- On demand extenstion of the metrics.


"""

import csv
import pandas as pd
import logging
import os


class CsvAgentFile:
    def __init__(self, directory):
        self.file_name = directory + '/agent.csv'
        file_exists = os.path.isfile(self.file_name)
        if not file_exists:
            self.csv_file = open(self.file_name, 'w', newline='')
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(['Agent ID', 'Agent Number',
                                  'Locations Created', 'Locations Deleted',
                                  'Location Read', 'Location Write',
                                  'Memory Read', 'Memory Write',
                                  'Agents Created', 'Agents Deleted',
                                  'Agents Dropped',
                                  'Agent Read', 'Agent Steps',
                                  'Agents Taken', 'Agent Write',
                                  'Items Created', 'Items Deleted',
                                  'Items Dropped',
                                  'Item Read', 'Items Taken',
                                  'Item Write', 'Success'
                                  ])

    def write_agent(self, agent):
        csv_iterator = [agent.csv_agent_writer.id, agent.csv_agent_writer.number,
                        agent.csv_agent_writer.location_created, agent.csv_agent_writer.location_deleted,
                        agent.csv_agent_writer.location_read, agent.csv_agent_writer.location_write,
                        agent.csv_agent_writer.memory_read, agent.csv_agent_writer.memory_write,
                        agent.csv_agent_writer.agents_created, agent.csv_agent_writer.agents_dropped,
                        agent.csv_agent_writer.agents_deleted, agent.csv_agent_writer.agent_read,
                        agent.csv_agent_writer.steps, agent.csv_agent_writer.agents_taken,
                        agent.csv_agent_writer.agent_write,
                        agent.csv_agent_writer.items_created, agent.csv_agent_writer.items_deleted,
                        agent.csv_agent_writer.items_dropped,
                        agent.csv_agent_writer.item_read, agent.csv_agent_writer.items_taken,
                        agent.csv_agent_writer.item_write, agent.csv_agent_writer.success]
        self.writer.writerow(csv_iterator)


class CsvAgentData:
    def __init__(self, agent_id, agent_number):
        self.id = agent_id
        self.number = agent_number
        self.steps = 0
        self.agents_created = 0
        self.agents_deleted = 0
        self.agents_dropped = 0
        self.agent_read = 0
        self.agents_taken = 0
        self.agent_write = 0
        self.items_created = 0
        self.items_deleted = 0
        self.item_read = 0
        self.item_write = 0
        self.location_read = 0
        self.location_write = 0
        self.location_created = 0
        self.location_deleted = 0
        self.memory_read = 0
        self.memory_write = 0
        self.items_taken = 0
        self.items_dropped = 0
        self.success = 0

    def write_agent(self, steps=0, agent_read=0, agents_created=0, agents_deleted=0, agents_dropped=0,
                    agents_taken=0,
                    agent_write=0, items_created=0, items_deleted=0, item_read=0, item_write=0, location_read=0,
                    location_write=0, location_created=0, location_deleted=0, memory_read=0, memory_write=0,
                    items_taken=0, items_dropped=0, success=0):
        self.steps = self.steps + steps
        self.agents_created = self.agents_created + agents_created
        self.agents_deleted = self.agents_deleted + agents_deleted
        self.agents_dropped = self.agents_dropped + agents_dropped
        self.agents_taken = self.agents_taken + agents_taken
        self.agent_read = self.agent_read + agent_read
        self.agent_write = self.agent_write + agent_write
        self.items_created = self.items_created + items_created
        self.items_deleted = self.items_deleted + items_deleted
        self.item_read = self.item_read + item_read
        self.item_write = self.item_write + item_write
        self.location_read = self.location_read + location_read
        self.location_write = self.location_write + location_write
        self.location_created = self.location_created + location_created
        self.location_deleted = self.location_deleted + location_deleted
        self.memory_read = self.memory_read + memory_read
        self.memory_write = self.memory_write + memory_write
        self.items_taken = self.items_taken + items_taken
        self.items_dropped = self.items_dropped + items_dropped
        self.success = self.success + success


class CsvRoundData:
    def __init__(self, task=0, scenario=0, solution=0, seed=20, directory="outputs/"):
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
        self.writer_round.writerow(['',
                                    'scenario', 'solution', 'Seed', 'Round Number',
                                    'Success Counter', 'Success Round',
                                    'Agent Counter',
                                    'Agents Created', 'Agents Created Sum',
                                    'Agents Deleted', 'Agents Deleted Sum',
                                    'Agents Dropped', 'Agents Dropped Sum',
                                    'Agent Read', 'Agent Read Sum',
                                    'Agent Steps', 'Agent Steps Sum',
                                    'Agents Taken', 'Agents Taken Sum',
                                    'Agent Write', 'Agent Write Sum',
                                    'Memory Read', 'Memory Read Sum',
                                    'Memory Write', 'Memory Write Sum',
                                    'Location Counter',
                                    'Location Created', 'Location Created Sum',
                                    'Location Deleted', 'Location Deleted Sum',
                                    'Location Read', 'Location Read Sum',
                                    'Location Write', 'Location Write Sum',
                                    'Item Counter',
                                    'Items Created', 'Items Created Sum',
                                    'Items Deleted', 'Items Deleted Sum',
                                    'Items Dropped', 'Items Dropped Sum',
                                    'Item Read', 'Item Read Sum',
                                    'Items Taken', 'Items Taken Sum',
                                    'Item Write', 'Item Write Sum',
                                    ])

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

    def next_line(self, sim_round):
        csv_iterator = ['', self.scenario, self.solution, self.seed, sim_round,
                        self.success_counter, self.success_round,
                        self.agent_num, self.agents_created, self.agents_created_sum,
                        self.agents_deleted, self.agents_deleted_sum,
                        self.agents_dropped, self.agents_dropped_sum,
                        self.agent_read, self.agent_read_sum,
                        self.steps, self.steps_sum,
                        self.agents_taken, self.agents_taken_sum,
                        self.agent_write, self.agent_write_sum,
                        self.memory_read, self.memory_read_sum, self.memory_write, self.memory_write_sum,
                        self.locations_num, self.location_created, self.location_created_sum,
                        self.location_deleted, self.location_deleted_sum,
                        self.location_read, self.location_read_sum,
                        self.location_write, self.location_write_sum,
                        self.item_num, self.items_created, self.items_created_sum,
                        self.items_deleted, self.items_deleted_sum, self.items_dropped, self.items_dropped_sum,
                        self.item_read, self.item_read_sum, self.items_taken, self.items_taken_sum,
                        self.item_write, self.item_write_sum]
        self.writer_round.writerow(csv_iterator)
        self.actual_round = sim_round
        self.steps = 0
        self.agent_read = 0
        self.item_read = 0
        self.location_read = 0
        self.memory_read = 0
        self.agent_write = 0
        self.item_write = 0
        self.location_write = 0
        self.memory_write = 0
        self.agents_created = 0
        self.items_created = 0
        self.location_created = 0
        self.agents_deleted = 0
        self.items_deleted = 0
        self.location_deleted = 0
        self.items_dropped = 0
        self.items_taken = 0
        self.success_round = 0
        self.success_counter = 0
        self.agents_taken = 0
        self.agents_dropped = 0

    def aggregate_metrics(self):
        self.csv_file.close()
        data = pd.read_csv(self.file_name)
        file_name = self.directory + "/aggregate_rounds.csv"
        csv_file = open(file_name, 'w', newline='')
        writer_round = csv.writer(csv_file)
        """Average Min Max for all other metrics"""
        writer_round.writerow(['Scenario', 'Solution', 'Seed', 'Rounds Total',
                               'Success Rate Sum', 'Success Ratio',
                               'Success Rate Avg', 'Success Rate Min', 'Success Rate Max',
                               'Success Round Min', 'Success Round Max',
                               'Agent Counter',
                               'Agents Created Sum', 'Agents Created Avg',
                               'Agents Created Min', 'Agents Created Max',
                               'Agents Deleted Sum', 'Agents Deleted Avg',
                               'Agents Deleted Min', 'Agents Deleted Max',
                               'Agents Dropped Sum', 'Agents Dropped Avg',
                               'Agents Dropped Min', 'Agents Dropped Max',
                               'Agent Read Sum', 'Agent Read Avg', 'Agent Read Min', 'Agent Read Max',
                               'Agent Steps Total', 'Agent Steps Avg',
                               'Agent Steps Min', 'Agent Steps Max',
                               'Agents Taken Sum', 'Agents Taken Avg',
                               'Agents Taken Min', 'Agents Taken Max',
                               'Agent Write Sum', 'Agent Write Avg', 'Agent Write Min', 'Agent Write Max',
                               'Location Counter',
                               'Location Created Sum', 'Location Created Avg',
                               'Location Created Min', 'Location Created Max',
                               'Location Deleted Sum', 'Location Deleted Avg',
                               'Location Deleted Min', 'Location Deleted Max',
                               'Location Read Sum', 'Location Read Avg', 'Location Read Min', 'Location Read Max',
                               'Location Write Sum', 'Location Write Avg', 'Location Write Min', 'Location Write Max',
                               'Memory Read Sum', 'Memory Read Avg', 'Memory Read Min', 'Memory Read Max',
                               'Memory Write Sum', 'Memory Write Avg', 'Memory Write Min', 'Memory Write Max',
                               'Item Counter',
                               'Items Created Sum', 'Items Created Avg', 'Items Created Min', 'Items Created Max',
                               'Items Deleted Sum', 'Items Deleted Avg', 'Items Deleted Min', 'Items Deleted Max',
                               'Items Dropped Sum', 'Items Dropped Avg', 'Items Dropped Min', 'Items Dropped Max',
                               'Item Read Sum', 'Item Read Avg', 'Item Read Min', 'Item Read Max',
                               'Items Taken Sum', 'Items Taken Avg', 'Items Taken Min', 'Items Taken Max',
                               'Item Write Sum', 'Item Write Avg', 'Item Write Min', 'Item Write Max'])

        csv_interator = [self.scenario, self.solution, self.seed, data['Round Number'].count(),

                         data['Success Counter'].sum(),
                         data['Success Counter'].sum() / data['Round Number'].sum(),

                         data['Success Counter'].mean(), data['Success Counter'].min(),
                         data['Success Counter'].max(),

                         data['Success Round'].min(),
                         data['Success Round'].max(),

                         self.agent_num,
                         data['Agents Created'].sum(), data['Agents Created'].mean(),
                         data['Agents Created'].min(), data['Agents Created'].max(),

                         data['Agents Deleted'].sum(), data['Agents Deleted'].mean(),
                         data['Agents Deleted'].min(), data['Agents Deleted'].max(),

                         data['Agents Dropped'].sum(), data['Agents Dropped'].mean(),
                         data['Agents Dropped'].min(), data['Agents Dropped'].max(),

                         data['Agent Read'].sum(), data['Agent Read'].mean(), data['Agent Read'].min(),
                         data['Agent Read'].max(),

                         data['Agent Steps'].sum(), data['Agent Steps'].mean(),
                         data['Agent Steps'].min(), data['Agent Steps'].max(),

                         data['Agents Taken'].sum(), data['Agents Taken'].mean(), data['Agents Taken'].min(),
                         data['Agents Taken'].max(),

                         data['Agent Write'].sum(), data['Agent Write'].mean(), data['Agent Write'].min(),
                         data['Agent Write'].max(),

                         self.locations_num,
                         data['Location Created'].sum(), data['Location Created'].mean(),
                         data['Location Created'].min(), data['Location Created'].max(),

                         data['Location Deleted'].sum(), data['Location Deleted'].mean(),
                         data['Location Deleted'].min(), data['Location Deleted'].max(),

                         data['Location Read'].sum(), data['Location Read'].mean(), data['Location Read'].min(),
                         data['Location Read'].max(),

                         data['Location Write'].sum(), data['Location Write'].mean(), data['Location Write'].min(),
                         data['Location Write'].max(),

                         data['Memory Read'].sum(), data['Memory Read'].mean(), data['Memory Read'].min(),
                         data['Memory Read'].max(),

                         data['Memory Write'].sum(), data['Memory Write'].mean(), data['Memory Write'].min(),
                         data['Memory Write'].max(),

                         self.item_num,
                         data['Items Created'].sum(), data['Items Created'].mean(), data['Items Created'].min(),
                         data['Items Created'].max(),

                         data['Items Deleted'].sum(), data['Items Deleted'].mean(), data['Items Deleted'].min(),
                         data['Items Deleted'].max(),

                         data['Items Dropped'].sum(), data['Items Dropped'].mean(), data['Items Dropped'].min(),
                         data['Items Dropped'].max(),

                         data['Item Read'].sum(), data['Item Read'].mean(), data['Item Read'].min(),
                         data['Item Read'].max(),

                         data['Items Taken'].sum(), data['Items Taken'].mean(), data['Items Taken'].min(),
                         data['Items Taken'].max(),

                         data['Item Write'].sum(), data['Item Write'].mean(), data['Item Write'].min(),
                         data['Item Write'].max()]

        writer_round.writerow(csv_interator)
        csv_file.close()

    def all_aggregate_metrics(self):
        self.csv_file.close()
        data = pd.read_csv(self.file_name)
        file_name = self.directory + "/aggregate_rounds.csv"
        csv_file = open(file_name, 'w', newline='')
        writer_round = csv.writer(csv_file)
        """Average Min Max for all other metrics"""
        writer_round.writerow(['Scenario', 'Solution', 'Seed', 'Rounds Total',
                               'Agent Counter',
                               'Success Rate Sum', 'Success Ratio',
                               'Success Rate Avg', 'Success Rate Min', 'Success Rate Max',
                               'Success Round Min', 'Success Round Max',
                               'Agent Counter',
                               'Agents Created Sum', 'Agents Created Avg',
                               'Agents Created Min', 'Agents Created Max',
                               'Agents Deleted Sum', 'Agents Deleted Avg',
                               'Agents Deleted Min', 'Agents Deleted Max',
                               'Agents Dropped Sum', 'Agents Dropped Avg',
                               'Agents Dropped Min', 'Agents Dropped Max',
                               'Agent Read Sum', 'Agent Read Avg', 'Agent Read Min', 'Agent Read Max',
                               'Partilcle Steps Total', 'Agent Steps Avg',
                               'Agent Steps Min', 'Agent Steps Max',
                               'Agents Taken Sum', 'Agents Taken Avg',
                               'Agents Taken Min', 'Agents Taken Max',
                               'Agent Write Sum', 'Agent Write Avg', 'Agent Write Min', 'Agent Write Max',
                               'Location Counter',
                               'Location Created Sum', 'Location Created Avg',
                               'Location Created Min', 'Location Created Max',
                               'Location Deleted Sum', 'Location Deleted Avg',
                               'Location Deleted Min', 'Location Deleted Max',
                               'Location Read Sum', 'Location Read Avg', 'Location Read Min', 'Location Read Max',
                               'Location Write Sum', 'Location Write Avg', 'Location Write Min', 'Location Write Max',
                               'Memory Read Sum', 'Memory Read Avg', 'Memory Read Min', 'Memory Read Max',
                               'Memory Write Sum', 'Memory Write Avg', 'Memory Write Min', 'Memory Write Max',
                               'Item Counter',
                               'Items Created Sum', 'Items Created Avg', 'Items Created Min', 'Items Created Max',
                               'Items Deleted Sum', 'Items Deleted Avg', 'Items Deleted Min', 'Items Deleted Max',
                               'Items Dropped Sum', 'Items Dropped Avg', 'Items Dropped Min', 'Items Dropped Max',
                               'Item Read Sum', 'Item Read Avg', 'Item Read Min', 'Item Read Max',
                               'Items Taken Sum', 'Items Taken Avg', 'Items Taken Min', 'Items Taken Max',
                               'Item Write Sum', 'Item Write Avg', 'Item Write Min', 'Item Write Max'])

        csv_interator = [self.scenario, self.solution, self.seed, data['Round Number'].count(),

                         self.agent_num,
                         data['Success Counter'].sum(),
                         data['Success Counter'].sum() / data['Round Number'].sum(),

                         data['Success Counter'].mean(), data['Success Counter'].min(),
                         data['Success Counter'].max(),

                         data['Success Round'].min(),
                         data['Success Round'].max(),

                         self.agent_num,
                         data['Agents Created'].sum(), data['Agents Created'].mean(),
                         data['Agents Created'].min(), data['Agents Created'].max(),

                         data['Agents Deleted'].sum(), data['Agents Deleted'].mean(),
                         data['Agents Deleted'].min(), data['Agents Deleted'].max(),

                         data['Agents Dropped'].sum(), data['Agents Dropped'].mean(),
                         data['Agents Dropped'].min(), data['Agents Dropped'].max(),

                         data['Agent Read'].sum(), data['Agent Read'].mean(), data['Agent Read'].min(),
                         data['Agent Read'].max(),

                         data['Agent Steps'].sum(), data['Agent Steps'].mean(),
                         data['Agent Steps'].min(), data['Agent Steps'].max(),

                         data['Agents Taken'].sum(), data['Agents Taken'].mean(), data['Agents Taken'].min(),
                         data['Agents Taken'].max(),

                         data['Agent Write'].sum(), data['Agent Write'].mean(), data['Agent Write'].min(),
                         data['Agent Write'].max(),

                         self.locations_num,
                         data['Location Created'].sum(), data['Location Created'].mean(),
                         data['Location Created'].min(), data['Location Created'].max(),

                         data['Location Deleted'].sum(), data['Location Deleted'].mean(),
                         data['Location Deleted'].min(), data['Location Deleted'].max(),

                         data['Location Read'].sum(), data['Location Read'].mean(), data['Location Read'].min(),
                         data['Location Read'].max(),

                         data['Location Write'].sum(), data['Location Write'].mean(), data['Location Write'].min(),
                         data['Location Write'].max(),

                         data['Memory Read'].sum(), data['Memory Read'].mean(), data['Memory Read'].min(),
                         data['Memory Read'].max(),

                         data['Memory Write'].sum(), data['Memory Write'].mean(), data['Memory Write'].min(),
                         data['Memory Write'].max(),

                         self.item_num,
                         data['Items Created'].sum(), data['Items Created'].mean(), data['Items Created'].min(),
                         data['Items Created'].max(),

                         data['Items Deleted'].sum(), data['Items Deleted'].mean(), data['Items Deleted'].min(),
                         data['Items Deleted'].max(),

                         data['Items Dropped'].sum(), data['Items Dropped'].mean(), data['Items Dropped'].min(),
                         data['Items Dropped'].max(),

                         data['Item Read'].sum(), data['Item Read'].mean(), data['Item Read'].min(),
                         data['Item Read'].max(),

                         data['Items Taken'].sum(), data['Items Taken'].mean(), data['Items Taken'].min(),
                         data['Items Taken'].max(),

                         data['Item Write'].sum(), data['Item Write'].mean(), data['Item Write'].min(),
                         data['Item Write'].max()]

        writer_round.writerow(csv_interator)
        csv_file.close()
