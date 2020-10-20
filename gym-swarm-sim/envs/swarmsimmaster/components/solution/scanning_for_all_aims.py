"""
This solution just scans for agents that are within 5 hops range and prints them out.
"""


def solution(world):
    center = world.grid.get_center()
    if world.get_actual_round() == 1:
        all_matters_list = world.get_agent_map_coordinates()[center].scan_for_matters_within(hop=5)
        for matter in all_matters_list:
            if matter.type == 'agent':
                print("agent at", matter.coordinates)
            elif matter.type == 'item':
                print("item", matter.coordinates)
            elif matter.type == 'location':
                print("location", matter.coordinates)
    if world.get_actual_round() == 2:
        all_matters_list = world.get_agent_map_coordinates()[center].scan_for_agents_within(hop=5)
        for matter in all_matters_list:
            print("agent at", matter.coordinates)
        all_matters_list = world.get_agent_map_coordinates()[center].scan_for_items_within(hop=5)
        for matter in all_matters_list:
            print("item", matter.coordinates)
        all_matters_list = world.get_agent_map_coordinates()[center].scan_for_locations_within(hop=5)
        for matter in all_matters_list:
            print("location", matter.coordinates)
