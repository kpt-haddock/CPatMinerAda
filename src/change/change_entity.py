from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import Optional

from libadalang import AdaNode


class Type(Enum):
    UNCHANGED = 0
    DELETED = 1
    ADDED = 2
    MODIFIED = 3
    MODIFIED_MODIFIERS = 4
    MODIFIED_NAME = 5
    MODIFIED_BODY = 6


class ChangeEntity:
    _threshold_distance: int = 20

    _start_line: int = -1
    __change_type: Type = Type.UNCHANGED
    _vector: Optional[dict[int, int]]
    _vector_length: int = 0
    _tree: Optional[dict[AdaNode, list[AdaNode]]]

    number_of_locs: int = 0
    number_of_non_comment_locs: int = 0
    number_of_ast_nodes: int = 0
    number_of_change_locs: int = 0
    number_of_change_ast_nodes: int = 0
    number_of_change_trees: int = 0

    def _get_change_type(self) -> Type:
        return self.__change_type

    def set_change_type(self, change_type: Type):
        self.__change_type = change_type

    def _compute_vector_length(self):
        self._vector_length = 0
        for value in self._vector.values():
            self._vector_length += value

    def _get_vector(self) -> dict[int, int]:
        return self._vector

    def _get_vector_length(self) -> int:
        return self._vector_length

    def get_number_of_locs(self) -> int:
        return self.number_of_locs

    def get_number_of_non_comment_locs(self) -> int:
        return self.number_of_non_comment_locs

    def get_number_of_ast_nodes(self) -> int:
        return self.number_of_ast_nodes

    def get_number_of_change_locs(self) -> int:
        return self.number_of_change_locs

    def get_number_of_change_ast_nodes(self) -> int:
        return self.number_of_change_ast_nodes

    def get_number_of_change_trees(self) -> int:
        return self.number_of_change_trees

    def compute_vector_similarity(self, other: ChangeEntity) -> float:
        v1: dict[int, int] = self._get_vector()
        v2: dict[int, int] = other._get_vector()
        keys: set[int] = set(v1.keys()).intersection(set(v2.keys()))

        common_size: int = 0
        for key in keys:
            common_size += min(v1[key], v2[key])
        return common_size * 2.0 / (self._get_vector_length() + other._get_vector_length())

    @abstractmethod
    def get_name(self) -> str:
        ...

    @abstractmethod
    def get_change_file(self) -> ChangeEntity:
        ...

    @abstractmethod
    def get_mapped_entity(self) -> Optional[ChangeEntity]:
        return None
        # if isinstance(self, ChangeClass):
        #     return self.get_mapped_class()
        # if isinstance(self, ChangeField):
        #     return self.get_mapped_field()
        # if isinstance(self, ChangeMethod):
        #     return self.get_mapped_method()
        # return None

    @abstractmethod
    def get_qualifier_name(self) -> str:
        ...

    @abstractmethod
    def get_change_class(self) -> ChangeEntity:
        ...

    def clean_for_stats(self):
        if self._tree is not None:
            self._tree.clear()
            self._tree = None
        if self._vector is not None:
            self._vector.clear()
            self._vector = None
