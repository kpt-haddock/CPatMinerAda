from __future__ import annotations

from abc import abstractmethod

from multimethod import multimethod
from overrides import override

from src.codemining.feature import Feature
from exas_sequential_feature import ExasSequentialFeature
from exas_single_feature import ExasSingleFeature


class ExasFeature(Feature):
    _number_of_features: int = 0  # static
    _number_of_branches: int = 0  # static
    MAX_LENGTH: int = 4           # static

    _hash: int

    _next: dict[ExasSingleFeature, ExasSequentialFeature] = {}

    @abstractmethod
    def get_feature_length(self) -> int:
        pass
    
    _id: int = 0
    _frequency: int = 0

    def __init__(self):
        type(self)._number_of_features += 1

    def get_number_of_features(self) -> int:
        return type(self)._number_of_features

    @override
    def get_id(self) -> int:
        return self._id

    def get_frequency(self) -> int:
        return self._frequency

    def set_frequency(self, frequency: int):
        self._frequency = frequency

    @staticmethod
    @multimethod
    def get_feature(sequence: list[ExasSingleFeature]) -> ExasFeature:
        if len(sequence) == 1:
            return sequence[0]
        feature: ExasFeature = sequence[0]
        for i in range(1, len(sequence)):
            single_feature: ExasSingleFeature = sequence[i]
            if single_feature in feature._next:
                feature = feature._next[single_feature]
            else:
                feature = ExasSequentialFeature(sequence[0:i+1],feature, single_feature)
        return feature

    @staticmethod
    @multimethod
    def get_feature(label: str) -> ExasSingleFeature:
        feature: ExasSingleFeature = ExasSingleFeature.features.get(label)
        if feature is None:
            feature = ExasSingleFeature(label)
        return feature

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def __eq__(self, other) -> bool:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

    def compare_to(self, other: ExasFeature) -> int:
        raise NotImplementedError('Method not implemented, compare_to for string')
        if self.get_feature_length() < other.get_feature_length():
            return -1
        if self.get_feature_length() > other.get_feature_length():
            return 1
        if isinstance(self, ExasSingleFeature):
            return self.get_label().compare_to(other.get_label())
        for i in range(0, self.get_feature_length()):
            c: int = self.get_sequence()[i].get_label().compare_to(other.get_sequence()[i].get_label())
            if c != 0:
                return c
        return 0
