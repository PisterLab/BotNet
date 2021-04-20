import random
import math



class Location:
    def __init__(self, coords):
        self.coords = coords
        self.adjacent = {}
        self.visited = False
        self.next_to_wall = False

    def __eq__(self, other):
        return self.coords == other.coords

    def __str__(self):
        return str(self.coords) + ' | Adjacent: ' + str(
            [(direction, location.coords, location.next_to_wall) for direction, location in self.adjacent.items()])


# Checks if a location exists in a graph
def location_exists(graph, coords):
    for location in graph:
        if location.coords == coords:
            return True
    return False


# Returns the location from a graph given the coordinates
def get_location_with_coords(graph, coords):
    for location in graph:
        if location.coords == coords:
            return location
    return False


# Returns the direction of an adjacent location relative to the current location
def get_dir(current_location, target_location):
    return target_location.coords[0] - current_location.coords[0], \
           target_location.coords[1] - current_location.coords[1], \
           target_location.coords[2] - current_location.coords[2]


# Adds a new location to a graph
def add_location_to_graph(world, graph, location, directions):
    if location in graph:
        return

    graph.append(location)
    location.visited = True

    for direction in directions:

        adjacent_location_coords = world.grid.get_coordinates_in_direction(location.coords,
                                                                           world.grid.get_directions_list()[direction])
        if location_exists(graph, adjacent_location_coords):
            if location in get_location_with_coords(graph, adjacent_location_coords).adjacent.values():
                continue
            get_location_with_coords(graph, adjacent_location_coords).adjacent[
                get_opposite_bearing(world, direction)] = location

        if is_border(world, adjacent_location_coords):
            if location.next_to_wall is True:
                continue

            location.next_to_wall = True
            continue


# Checks if the given coordinates are valid simulator coordinates
def valid_sim_coords(world, coords):
    return world.grid.are_valid_coordinates(coords)


# Checks if the location at the given coordinates is a border or not
def is_border(world, coords):
    for item in world.get_items_list():
        if coords == item.coordinates:
            return True
    return False


# Initializes the new custom agent attributes
def set_agent_attributes(world, agent, search_alg):
    directions = list(range(len(world.grid.get_directions_list())))
    search_algo = []

    if search_alg == 0:
        search_algo.append(0)
    elif search_alg == 1:
        search_algo.append(-1)
    elif search_alg == 2:
        search_algo.append(-1)
        search_algo.append(0)

    search_algorithm = random.choice(search_algo)

    setattr(agent, "direction", directions)
    setattr(agent, "search_algorithm", search_algorithm)

    setattr(agent, "unvisited_queue", [])
    setattr(agent, "visited", [])
    setattr(agent, "graph", [])

    setattr(agent, "origin_coords", agent.coordinates)
    setattr(agent, "start_location", Location(agent.origin_coords))

    setattr(agent, "current_location", None)
    setattr(agent, "next_location", None)
    setattr(agent, "target_location", agent.start_location)
    setattr(agent, "stuck_location", None)
    setattr(agent, "alternative_location", None)
    setattr(agent, "bearing", None)

    setattr(agent, "previous_location", None)
    setattr(agent, "last_visited_locations", [])
    setattr(agent, "alternative_locations", [])
    setattr(agent, "reverse_path", [])

    setattr(agent, "stuck", False)
    setattr(agent, "alternative_reached", True)
    setattr(agent, "target_reached", True)
    setattr(agent, "done", False)


# Discovers the adjacent (Neighbour) locations relative to the agent's current location
def discover_adjacent_locations(world, agent):
    for direction in agent.direction:

        adjacent_location_coords = world.grid.get_coordinates_in_direction(agent.current_location.coords,
                                                                           world.grid.get_directions_list()[direction])

        if not valid_sim_coords(world, adjacent_location_coords):
            continue

        if is_border(world, adjacent_location_coords):
            if agent.current_location.next_to_wall is True:
                continue
            agent.current_location.next_to_wall = True
            continue

        if location_exists(agent.graph, adjacent_location_coords):
            if get_location_with_coords(agent.graph,
                                        adjacent_location_coords) in agent.current_location.adjacent.values():
                continue
            agent.current_location.adjacent[direction] = get_location_with_coords(agent.graph,
                                                                                  adjacent_location_coords)
            continue

        new_location = Location(adjacent_location_coords)
        agent.create_location_on(adjacent_location_coords)
        world.new_location.set_color((0.0, 0.0, 1.0, 1.0))
        agent.current_location.adjacent[direction] = new_location
        agent.unvisited_queue.append(new_location)
        add_location_to_graph(world, agent.graph, new_location, agent.direction)


# Marks the agent's current location as visited and removes it from the agent's unvisited queue
def mark_location(world, agent):
    agent.current_location.visited = True
    agent.visited.append(agent.current_location)
    agent.unvisited_queue = [location for location in agent.unvisited_queue if location not in agent.visited]
    current_location = world.location_map_coordinates[agent.coordinates]

    if current_location.color == (0.0, 0.8, 0.8, 1.0):
        return

    agent.delete_location()
    agent.create_location()
    world.new_location.set_color((0.0, 0.8, 0.8, 1.0))


# Returns the distance between 2 locations
def get_distance(location1, location2):
    x1 = location1.coords[0]
    x2 = location2.coords[0]

    y1 = location1.coords[1]
    y2 = location2.coords[1]

    z1 = location1.coords[2]
    z2 = location2.coords[2]

    return abs(math.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2) + ((z2 - z1) ** 2)))


# Returns the nearest location in the agent's unvisited queue relative to the agent's current location
def get_nearest_unvisited(agent):
    possible_unvisited_locations = []
    for location in agent.unvisited_queue:
        possible_unvisited_locations.append((round(get_distance(agent.current_location, location)), location))

    return min(possible_unvisited_locations, key=lambda t: t[0])[1]


# Returns the next best possible move if the agent's target location is not adjacent to it (path generator)
def get_best_location(agent, target_location):
    possible_moves = []

    for location in agent.current_location.adjacent.values():
        possible_moves.append((get_distance(location, target_location), location))

    best_location = min(possible_moves, key=lambda t: t[0])[1]

    return best_location


# Follows wall
def follow_wall(world, agent, target_location):
    possible_moves = []

    for location in agent.current_location.adjacent.values():

        if location in agent.last_visited_locations:
            continue

        if location.next_to_wall or not location.visited:
            possible_moves.append((get_distance(location, target_location), location))
            agent.alternative_locations.append((get_distance(location, target_location), location))

    if len(possible_moves) == 0:
        for location in agent.current_location.adjacent.values():

            if location in agent.last_visited_locations:
                continue

            if not is_border(world, location.coords):
                possible_moves.append((get_distance(location, target_location), location))
                agent.alternative_locations.append((get_distance(location, target_location), location))

    best_location = min(possible_moves, key=lambda t: t[0])[1]

    return best_location


# Returns the next closest unvisited location relative to the agent's current location
def get_next_unvisited(agent):
    if agent.unvisited_queue[agent.search_algorithm] not in agent.current_location.adjacent.values():
        return get_best_location(agent, get_nearest_unvisited(agent))

    else:
        return agent.unvisited_queue[agent.search_algorithm]


# Returns the direction of the target location relative to the current location
def get_bearing(world, current_location, target_location):
    dirs = world.grid.get_directions_list()

    if current_location == target_location:
        return 0

    d = world.grid.get_nearest_direction(current_location.coords, target_location.coords)

    index = 0
    for direction in dirs:
        if d == direction:
            break
        else:
            index += 1

    return index


# Checks if the path to the target is obstructed by a wall or obstacle
def path_blocked(world, current_location, target_location):
    if target_location in current_location.adjacent.values():
        return False

    ndb = get_bearing(world, current_location, target_location)

    if ndb not in current_location.adjacent.keys():
        return True


# Reverses agent bearing. This is used to terminate the wall following algorithm.
def get_opposite_bearing(world, bearing):

    direction = world.grid.get_directions_list()[bearing]

    return get_bearing(world, Location(direction), Location(world.grid.get_center()))


# Checks if a agent's way is blocked by a wall or obstacle
def check_stuck(world, agent, target_location):
    if path_blocked(world, agent.current_location, target_location):
        return True

    return False


# Returns the next location to move to
def get_next_location(world, agent, target_location):
    if target_location in agent.current_location.adjacent.values():
        agent.target_reached = True
        return target_location

    else:
        if check_stuck(world, agent, target_location):
            agent.stuck = True
            agent.bearing = get_bearing(world, agent.current_location, agent.target_location)
            agent.stuck_location = agent.current_location
            agent.last_visited_locations.append(agent.current_location)
            return follow_wall(world, agent, target_location)

        else:
            return get_best_location(agent, target_location)


# Handles the movement of the agent through the terrain
def move(world, agent, next_location):
    agent.previous_location = agent.current_location
    next_direction = get_dir(agent.current_location, next_location)
    agent.current_location = next_location
    mark_location(world, agent)
    agent.move_to(next_direction)
    agent.current_location = get_location_with_coords(agent.graph, agent.coordinates)
    discover_adjacent_locations(world, agent)


def solution(world):

    if world.config_data.max_round == world.get_actual_round():
        print("last round! (if not yet finished = max_round to small)")

    # 0 = BFS, 1 = DFS, 2 = MIXED
    search_algorithm = 2

    for agent in world.get_agent_list():

        if world.get_actual_round() == 1:
            set_agent_attributes(world, agent, search_algorithm)
            agent.current_location = agent.start_location
            agent.create_location_on(agent.origin_coords)
            world.new_location.set_color((0.0, 0.0, 1.0, 1.0))
            add_location_to_graph(world, agent.graph, agent.current_location, agent.direction)
            discover_adjacent_locations(world, agent)
            continue

        else:

            if not agent.alternative_reached:

                if agent.alternative_location in agent.current_location.adjacent.values():
                    agent.alternative_reached = True
                    agent.alternative_locations.clear()
                    agent.reverse_path.clear()
                    agent.next_location = agent.alternative_location
                    move(world, agent, agent.next_location)
                    if len(agent.unvisited_queue) <= 0:
                        mark_location(world, agent)
                        world.success_termination()
                        return
                    continue

                agent.next_location = agent.reverse_path.pop()
                move(world, agent, agent.next_location)
                if len(agent.unvisited_queue) <= 0:
                    mark_location(world, agent)
                    world.success_termination()
                    return
                continue

            if agent.stuck:
                agent.alternative_locations = [item for item in agent.alternative_locations
                                                  if item[1].coords != agent.current_location.coords]

                if agent.current_location not in agent.last_visited_locations:
                    agent.last_visited_locations.append(agent.current_location)

                if agent.current_location.coords != agent.stuck_location.coords:

                    if get_bearing(world, agent.current_location, agent.stuck_location) == \
                            get_opposite_bearing(world, agent.bearing):
                        agent.stuck = False
                        agent.last_visited_locations.clear()
                        agent.alternative_locations.clear()
                        continue

                if agent.target_location in agent.current_location.adjacent.values():
                    agent.stuck = False
                    agent.target_reached = True
                    agent.last_visited_locations.clear()
                    agent.alternative_locations.clear()
                    agent.next_location = agent.target_location
                    move(world, agent, agent.next_location)
                    if len(agent.unvisited_queue) <= 0:
                        mark_location(world, agent)
                        return
                    continue

                try:
                    next_location = follow_wall(world, agent, agent.target_location)
                    agent.next_location = next_location
                    move(world, agent, agent.next_location)
                    if len(agent.unvisited_queue) <= 0:
                        mark_location(world, agent)
                        return
                    continue

                except ValueError:
                    agent.reverse_path = agent.last_visited_locations.copy()
                    del agent.reverse_path[-1]
                    agent.alternative_location = min(agent.alternative_locations, key=lambda t: t[0])[1]
                    agent.alternative_reached = False
                    continue

            if not agent.target_reached:
                agent.next_location = get_next_location(world, agent, agent.target_location)
                move(world, agent, agent.next_location)
                if len(agent.unvisited_queue) <= 0:
                    mark_location(world, agent)
                    return
                continue

            if len(agent.unvisited_queue) > 0:

                if agent.unvisited_queue[agent.search_algorithm] in agent.current_location.adjacent.values():
                    agent.target_reached = True
                    agent.next_location = agent.unvisited_queue[agent.search_algorithm]
                    move(world, agent, agent.next_location)
                    if len(agent.unvisited_queue) <= 0:
                        mark_location(world, agent)
                        return
                    continue

                else:
                    nearest_unvisited = get_nearest_unvisited(agent)

                    if nearest_unvisited in agent.current_location.adjacent.values():
                        agent.target_reached = True
                        agent.next_location = nearest_unvisited
                        move(world, agent, agent.next_location)
                        if len(agent.unvisited_queue) <= 0:
                            mark_location(world, agent)
                            return
                        continue

                    else:
                        agent.target_reached = False
                        agent.target_location = nearest_unvisited
                        agent.next_location = get_next_location(world, agent, agent.target_location)
                        move(world, agent, agent.next_location)
                        if len(agent.unvisited_queue) <= 0:
                            mark_location(world, agent)
                            return
                        continue

            if len(agent.unvisited_queue) <= 0:
                mark_location(world, agent)
                return
