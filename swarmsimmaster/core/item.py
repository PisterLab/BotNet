"""The item module provides the interface for the items. An item can be taken or dropped
 and be connected to each other to build up islands"""
from core import matter
from core.matter import MatterType


class Item(matter.Matter):
    def __init__(self, world, coordinates, color):
        """Initializing the item constructor"""
        super().__init__(world, coordinates, color, matter_type=MatterType.ITEM,
                         mm_size=world.config_data.item_mm_size)
        self.__isCarried = False

    def is_carried(self):
        """
        Get the item status if it taken or not

        :return: items carry status
        """
        return self.__isCarried

    def set_carried_flag(self, flag):
        """
        Sets the items status

        :param flag: True: Has been taken; False: Is not taken
        :return:
        """
        self.__isCarried = flag

    def take(self):
        """
        Takes the item on the given coordinate if it is not taken

        :return: True: Successful taken; False: Cannot be taken or wrong Coordinates
        """

        if not self.__isCarried:
            if self.coordinates in self.world.item_map_coordinates:
                del self.world.item_map_coordinates[self.coordinates]
            self.__isCarried = True
            if self.world.vis is not None:
                self.world.vis.item_changed(self)
            return True
        else:
            return False

    def drop_me(self, coordinates):
        """
        Drops the item

        :param coordinates: the given position
        :return: None
        """
        self.coordinates = coordinates
        self.world.item_map_coordinates[self.coordinates] = self
        self.__isCarried = False
        if self.world.vis is not None:
            self.world.vis.item_changed(self)

    def set_color(self, color):
        super().set_color(color)
        if self.world.vis is not None:
            self.world.vis.item_changed(self)
