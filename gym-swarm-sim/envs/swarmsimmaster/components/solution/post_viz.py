# NOTE: AGENT RANDOM ORDER SHOULD BE FALSE WHEN USING THIS
def solution(world):
    round = world.get_actual_round()
    round_data = list(world.replication_data.iloc[round])
    i = 1
    for agent in world.get_agent_list():
        agent.coordinates = eval(round_data[i]) # NOTE: careful when using eval
        i += 1 # FIXME: this should enumerate agent list