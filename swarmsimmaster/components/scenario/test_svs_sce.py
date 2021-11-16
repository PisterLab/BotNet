import numpy as np

DEFENSE_CLR = [0, 0, 255, 1]
OFFENSE_CLR = [255, 0, 0, 1]
DEFENSE_CENTER = [-10, 0, 0]
OFFENSE_CENTER = [10, 0, 0]

DEFENSE_MAX_SPEED = 0.1
OFFENSE_MAX_SPEED = 0.1
# offense_max_speed = 0.09
COMMS_MODEL = "disk"
DISK_RANGE = 3

def scenario(world):
    defense_size = 30
    offense_size = 60

    world.add_location(tuple(DEFENSE_CENTER), [0, 0, 255, 1])

    # spawn defense agents
    for _ in range(defense_size):
        spawn = list(circle_spawn(defense_size)) + [0]
        spawn = np.array(spawn) + np.array(DEFENSE_CENTER)
        world.add_agent(tuple(spawn), color=DEFENSE_CLR)

    # spawn offense agents
    for _ in range(offense_size):
        spawn = list(circle_spawn(offense_size)) + [0]
        spawn = np.array(spawn) + np.array(OFFENSE_CENTER)
        world.add_agent(tuple(spawn), color=OFFENSE_CLR)


def circle_spawn(swarm_size):
    density = 0.22
    t = 2 * np.pi * np.random.random()
    u = np.random.random() + np.random.random()
    r = 2 - u if u > 1 else u
    radius =  pow(swarm_size / (density * np.pi), 0.5)
    return np.array([r * np.cos(t) * radius, r * np.sin(t) * radius])
