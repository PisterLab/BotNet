# NOTE: AGENT RANDOM ORDER SHOULD BE FALSE WHEN USING THIS
def solution(world):
    round = world.get_actual_round()
    try:
        round_data = world.replication_data[round-1]
        for i, agent in enumerate(world.get_agent_list()):
            agent.move_coord(tuple(round_data[i])) # TODO: check off by one, may be round - 1
            print(i, agent.coordinates)
    except:
        print("Simulation replay done.", end="\r")