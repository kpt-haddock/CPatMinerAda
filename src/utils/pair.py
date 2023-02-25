from __future__ import annotations
from multimethod import multimethod


class Pair:
    __object1: object
    __object2: object
    __weight: float = -1.0
    __weight1: float = 0.0

    @multimethod
    def __init__(self, object1: object, object2: object):
        self.__object1 = object1
        self.__object2 = object2

    @multimethod
    def __init__(self, object1: object, object2: object, weight: float):
        self.__init__(object1, object2)
        self.__weight = weight

    @multimethod
    def __init__(self, object1: object, object2: object, weight: float, weight1: float):
        self.__init__(object1, object2, weight)
        self.__weight1 = weight1

    def compute_weight(self, other: Pair) -> float:
        return self.__weight

    def __lt__(self, other: Pair) -> bool:
        return self.compare_to(other) < 0

    def __gt__(self, other: Pair) -> bool:
        return self.compare_to(other) > 0

    def __eq__(self, other: Pair) -> bool:
        return self.compare_to(other) == 0

    def __ne__(self, other: Pair) -> bool:
        return self.compare_to(other) != 0

    def compare_to(self, other: Pair) -> int:
        compare_value: int = self.compare(self.__weight, other.__weight)
        if compare_value == 0:
            compare_value = self.compare(self.__weight1, other.__weight1)
        return compare_value

    def compare(self, f1: float, f2 : float) -> int:
        if f1 < f2:
            return -1
        elif f1 > f2:
            return 1
        return 0
    
    def get_object1(self) -> object:
        return self.__object1

    def get_object2(self) -> object:
        return self.__object2

    def set_object1(self, object1: object):
        self.__object1 = object1

    def set_object2(self, object2: object):
        self.__object2 = object2

    def get_weight(self) -> float:
        return self.__weight

    def set_weight(self, weight: float):
        self.__weight = weight

    def __str__(self) -> str:
        return str(self.__weight)
