from components.grids.grid import Grid


class CCPGrid(Grid):

    def __init__(self, size):
        super().__init__()
        self._size = size

    @property
    def size(self):
        return self._size

    @property
    def directions(self):
        return {"LEFT_UP": (-1.0, 1.0, 0.0),
                "FORWARD_UP": (0.0, 1.0, 1.0),
                "RIGHT_UP": (1.0, 1.0, 0.0),
                "BACK_UP": (0.0, 1.0, -1.0),
                "LEFT_FORWARD": (-1.0, 0.0, 1.0),
                "RIGHT_FORWARD": (1.0, 0.0, 1.0),
                "RIGHT_BACK": (1.0, 0.0, -1.0),
                "LEFT_BACK": (-1.0, 0.0, -1.0),
                "LEFT_DOWN": (-1.0, -1.0, 0.0),
                "FORWARD_DOWN": (0.0, -1.0, 1.0),
                "RIGHT_DOWN": (1.0, -1.0, 0.0),
                "BACK_DOWN": (0.0, -1.0, -1.0)}

    def get_box(self, width):
        locations = []

        for x in range(-width, width+1):
            for y in range(-width, width+1):
                for z in range(-width, width+1):
                    if self.are_valid_coordinates((x, y, z)):
                        locations.append((x, y, z))

        return locations

    def are_valid_coordinates(self, coordinates):
        x = coordinates[0]
        y = coordinates[1]
        z = coordinates[2]
        if y % 2.0 == 0:
            if x % 2.0 == z % 2.0 == 0 or x % 2.0 == z % 2.0 == 1:
                return True
        else:
            if x % 2.0 == 1 and z % 2.0 == 0 or x % 2.0 == 0 and z % 2.0 == 1:
                return True
        return False

    def get_nearest_valid_coordinates(self, coordinates):
        x = round(coordinates[0])
        y = round(coordinates[1])
        z = round(coordinates[2])

        if y % 2.0 == 0:
            if x % 2.0 != z % 2.0:
                z = z + 1
        else:
            if x % 2.0 == z % 2.0:
                z = z + 1

        return x, y, z

    def get_dimension_count(self):
        return 3

    def get_distance(self, start, end):
        dx = abs(start[0] - end[0])
        dy = abs(start[1] - end[1])
        dz = abs(start[2] - end[2])
        if dy > dx + dz:
            return dy
        if dx > dy + dz:
            return dx
        if dz > dx + dy:
            return dz
        return (dx + dy + dz) / 2.0

    def get_center(self):
        return 0, 0, 0
