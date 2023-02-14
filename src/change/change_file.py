from __future__ import annotations

from typing import Optional

from overrides import override

from src.change.change_class import ChangeClass
from src.change.change_entity import ChangeEntity
from src.change.revision_analyzer import RevisionAnalyzer


class ChangeFile(ChangeEntity):
    MAX_SIZE = 500000
    __revision_analyzer: RevisionAnalyzer
    __path: str
    __simple_name: str
    __mapped_file: ChangeFile
    __compilation_unit = None  # TODO
    __classes: set[ChangeClass] = set()

    def __init__(self, revision_analyzer: RevisionAnalyzer, path: str, content: str):
        ...

    def get_revision_analyzer(self) -> RevisionAnalyzer:
        return self.__revision_analyzer

    def get_path(self) -> str:
        return self.__path

    def get_simple_name(self) -> str:
        return self.__simple_name

    @override
    def get_name(self) -> str:
        return self.get_simple_name()

    def get_classes(self) -> set[ChangeClass]:
        return self.__classes

    def get_mapped_file(self) -> ChangeFile:
        return self.__mapped_file

    def set_mapped_file(self, mapped_file: ChangeFile):
        self.__mapped_file = mapped_file

    @override
    def get_change_file(self) -> ChangeFile:
        return self

    @override
    def get_change_class(self) -> ChangeClass:
        return None

    def compute_similarity(self, other: ChangeFile):
        classes_m: set[ChangeClass] = self.get_classes()
        classes_n: set[ChangeClass] = other.get_classes()
        mapped_classes_m: set[ChangeClass] = set()
        mapped_classes_n: set[ChangeClass] = set()

        class_m: Optional[ChangeClass] = None
        class_n: Optional[ChangeClass] = None
        for change_class in classes_m:
            if change_class.get_simple_name() == self.get_simple_name():
                class_m = change_class
        for change_class in classes_n:
            if change_class.get_simple_name() == other.get_simple_name():
                class_n = change_class
        if class_m is not None and class_n is not None:
            similarity: float = class_m.compute_similarity(class_n, False)
            if similarity > ChangeClass.threshold_similary:
                ChangeClass.set_map(class_m, class_n)
                mapped_classes_m.add(class_m)
                mapped_classes_n.add(class_n)
                classes_m.remove(class_m)
                classes_n.remove(class_n)
        ChangeClass.map_all(classes_m, classes_n, mapped_classes_m, mapped_classes_n)

    def print_changes(self, ps):
        ...

    def print_changes(self, ps, classes):
        ...

    @override
    def __str__(self) -> str:
        return self.__simple_name

    @override
    def get_qualifier_name(self) -> str:
        return self.__path
