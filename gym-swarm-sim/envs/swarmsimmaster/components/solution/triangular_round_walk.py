# round walk for the triangular grid


def solution(world):
    for agent in world.get_agent_list():
        global ttl
        global max
        global direction

        dirs = world.grid.get_directions_list()

        if world.get_actual_round() == 1:
            max = 0
            ttl = 0
            direction = dirs[0]

        if ttl == 0 and (direction == dirs[0] or direction == dirs[3]):
            max = max + 1

        if ttl == 0:
            print("Round ", world.get_actual_round())
            ttl = max
            if direction == dirs[0]:
                direction = dirs[5]
            elif direction == dirs[5]:
                direction = dirs[3]
            elif direction == dirs[3]:
                direction = dirs[2]
            elif direction == dirs[2]:
                direction = dirs[0]

        agent.create_location()
        agent.move_to(direction)
        ttl = ttl - 1
