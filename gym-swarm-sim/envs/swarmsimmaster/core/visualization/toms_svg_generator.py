import math


class Line:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def to_svg(self, style):
        return f'<line x1="{self.x1}" y1="{self.y1}" x2="{self.x2}" y2="{self.y2}" style="{style}"  />'


class Circle:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

    def to_svg(self, style):
        return f'<circle cx="{self.x}" cy="{self.y}" r="{self.radius}" style="{style}"  />'


class NGon:
    def __init__(self, x, y, radius, n):
        self.x = x
        self.y = y
        self.radius = radius
        self.n = n

    def to_svg(self, style):
        n = self.n
        starting_angle = 0.5 * 2.0 * math.pi / n
        points = []
        for i in range(n):
            angle = 2.0 * math.pi * i / n + starting_angle
            x = self.x + self.radius * math.cos(angle)
            y = self.y + self.radius * math.sin(angle)
            points.append(f"{x},{y}")
        points = " ".join(points)
        return f'<polygon points="{points}" style="{style}"  />'


class Ring:
    def __init__(self, x, y, inner_radius, outer_radius):
        self.x = x
        self.y = y
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius

    def to_svg(self, style):
        r0 = self.inner_radius
        r1 = self.outer_radius

        path = f'''
        M {self.x} {self.y - r1}
        A {r1} {r1} 0 1 0 {self.x} {self.y + r1}
        A {r1} {r1} 0 1 0 {self.x} {self.y - r1}
        Z
        M {self.x} {self.y - r0}
        A {r0} {r0} 0 1 1 {self.x} {self.y + r0}
        A {r0} {r0} 0 1 1 {self.x} {self.y - r0}
        Z
        '''

        path = " ".join(path.split())

        return f'<path d="{path}" style="{style}"  />'


def make_svg_header(width, height):
    return f'''<svg version="1.1"
    baseProfile="full"
    width="{width}" height="{height}"
    xmlns="http://www.w3.org/2000/svg">'''


def draw_world(
        filename,
        items,
        locations,
        agents,
        world_size_x,
        world_size_y,
        padding,
        scale,
        stroke_width,
):
    # squish vertically to make triangles equilateral
    squish = math.sqrt(1 - 0.5 ** 2)

    width = (world_size_x + 2 * padding) * scale
    height = (world_size_y + 2 * padding) * scale * squish

    svg = [make_svg_header(width, height),
           f'<g transform="scale({scale} {scale})">',
           '<g transform="translate(0.5, 0.5)">']

    def draw_line(ax, ay, bx, by):
        line_style = f'stroke: rgb(0,0,0); stroke-width: {stroke_width}'
        svg.append(Line(ax, ay, bx, by).to_svg(line_style))

    # draw horizontal lines
    for y in range(world_size_y + 1):
        shift = 0.0 if y % 2 == 0 else 0.5
        draw_line(shift, y * squish, shift + world_size_x - 1, y * squish)

    # draw diagonal lines which start at 0
    for x2 in range(world_size_x):
        x3 = min(world_size_x - 0.5, x2 + 0.5 * world_size_y)
        draw_line(x2, 0, x3, (x3 - x2) * 2 * squish)
        x4 = max(0, x2 - 0.5 * world_size_y)
        draw_line(x2, 0, x4, (x2 - x4) * 2 * squish)

    # draw diagonal lines that don't start at 0
    for y2 in range(1, world_size_y):
        shift = 0.0 if y2 % 2 == 0 else 0.5
        y3 = min(world_size_y, y2 + world_size_y)
        draw_line(shift, y2 * squish, shift + 0.5 * (y3 - y2), y3 * squish)
        x = shift + world_size_x - 1
        draw_line(x, y2 * squish, x - 0.5 * (y3 - y2), y3 * squish)

    # draw circles at intersection points
    # for y in range(world_size_y + 1):
    #     shift = 0.0 if y % 2 == 0 else 0.5
    #     for x in range(world_size_x):
    #         style = f'stroke: rgb(0,0,0); stroke-width: {stroke_width}'
    #         svg.append(Circle(x + shift, y * squish, 0.05).to_svg(style))

    # draw items
    for x, y in items:
        shift = 0.0 if y % 2 == 0 else -0.5
        style = f'fill:rgb(77, 77, 204); stroke:rgb(77, 77, 204);stroke-width: {stroke_width}'
        svg.append(NGon(x + shift, y * squish, 0.5, 6).to_svg(style))
        # draw green ring
    for x, y in locations:
        shift = 0.0 if y % 2 == 0 else -0.5
        style = f'fill:rgb(77, 204, 77); stroke:rgb(77, 204, 77);stroke-width: {stroke_width}'
        svg.append(Ring(x + shift, y * squish, 0.2, 0.5 * squish).to_svg(style))
    for x, y in agents:
        shift = 0.0 if y % 2 == 0 else -0.5
        style = f'fill:rgb(204, 77, 77); stroke:rgb(204, 77, 77);stroke-width: {stroke_width}'
        svg.append(Circle(x + shift, y * squish, 0.3).to_svg(style))

    svg.append('</g>')
    svg.append('</g>')
    svg.append('</svg>\n')

    svg = "\n".join(svg)
    with open(filename, "w") as f:
        f.write(svg)


def create_svg(world, filename):
    item_coordinates = world.item_map_coordinates.keys()
    location_coordinates = world.location_map_coordinates.keys()
    agent_coordinates = world.agent_map_coordinates.keys()

    minimum_x_coordinate, maximum_x_coordinate, minimum_y_coordinate, maximum_y_coordinate \
        = calculate_bounds(item_coordinates, agent_coordinates, location_coordinates)
    print(minimum_y_coordinate, minimum_x_coordinate, maximum_y_coordinate, maximum_x_coordinate)
    x_offset = int(minimum_x_coordinate - 4)
    y_offset = int(maximum_y_coordinate + 4)
    size_x = int(maximum_x_coordinate - x_offset + 4)
    size_y = int(y_offset - minimum_y_coordinate + 4)
    img_size = max(size_x, size_y)  # make a square image
    print(img_size)
    item_coordinates_in_image = []
    location_coordinates_in_image = []
    agent_coordinates_in_image = []
    for coordinates in item_coordinates:
        item_coordinates_in_image.append((int(coordinates[0] - x_offset + (0 if coordinates[1] % 2 == 0 else 1)),
                                          int(- coordinates[1] + y_offset)))
    for coordinates in location_coordinates:
        location_coordinates_in_image.append((int(coordinates[0] - x_offset + (0 if coordinates[1] % 2 == 0 else 1)),
                                              int(- coordinates[1] + y_offset)))
    for coordinates in agent_coordinates:
        agent_coordinates_in_image.append((int(coordinates[0] - x_offset + (0 if coordinates[1] % 2 == 0 else 1)),
                                           int(- coordinates[1] + y_offset)))

    draw_world(
        items=item_coordinates_in_image,
        locations=location_coordinates_in_image,
        agents=agent_coordinates_in_image,
        world_size_x=img_size,
        world_size_y=img_size,
        scale=60,
        padding=0.5,
        stroke_width=0.02,
        filename=filename)


def calculate_bounds(item_coordinates, agent_coordinates, location_coordinates):
    minx = 0
    miny = 0
    maxx = 0
    maxy = 0

    all_coords = []
    all_coords.extend(item_coordinates)
    all_coords.extend(agent_coordinates)
    all_coords.extend(location_coordinates)

    for coords in all_coords:
        if coords[0] < minx:
            minx = coords[0]
        if coords[0] > maxx:
            maxx = coords[0]
        if coords[1] < miny:
            miny = coords[1]
        if coords[1] > maxy:
            maxy = coords[1]

    return minx, maxx, miny, maxy
