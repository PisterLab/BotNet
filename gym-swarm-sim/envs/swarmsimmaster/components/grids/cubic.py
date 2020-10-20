from components.grids.grid import Grid


class CubicGrid(Grid):

    def __init__(self, size):
        super().__init__()
        self._size = size

    @property
    def size(self):
        return self._size

    @property
    def directions(self):
        return {"LEFT": (-1, 0, 0),
                "RIGHT": (1, 0, 0),
                "UP": (0, 1, 0),
                "DOWN": (0, -1, 0),
                "FORWARD": (0, 0, 1),
                "BACK": (0, 0, -1)}

    def get_box(self, width):
        locations = []
        for x in range(-width, width+1):
            for y in range(-width, width+1):
                for z in range(-width, width+1):
                    locations.append((x, y, z))
        return locations

    def are_valid_coordinates(self, coordinates):
        if coordinates[0] % 1 == 0 and coordinates[1] % 1 == 0 and coordinates[2] % 1 == 0:
            return True
        else:
            return False

    def get_nearest_valid_coordinates(self, coordinates):
        return (round(coordinates[0]),
                round(coordinates[1]),
                round(coordinates[2]))

    def get_dimension_count(self):
        return 3

    def get_distance(self, start, end):
        return abs(start[0] - end[0]) + abs(start[1] - end[1]) + abs(start[2] - end[2])

    def get_center(self):
        return 0, 0, 0
