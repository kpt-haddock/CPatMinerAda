from __future__ import annotations

from abc import abstractmethod

from multimethod import multimethod
from overrides import override

from codemining.feature import Feature


class ExasFeature(Feature):
    _number_of_features: int = 0  # static
    _number_of_branches: int = 0  # static
    MAX_LENGTH: int = 4           # static

    _hash: int

    _next: dict[ExasSingleFeature, ExasSequentialFeature]

    @abstractmethod
    def get_feature_length(self) -> int:
        pass
    
    _id: int = 0
    _frequency: int = 0

    def __init__(self):
        self._next = {}
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


class ExasSequentialFeature(ExasFeature):
    __sequence: list[ExasSingleFeature]

    def __init__(self, sequence: list[ExasSingleFeature], pre: ExasFeature, single_feature: ExasSingleFeature):
        super().__init__()
        self.__sequence = sequence.copy()
        pre._next[single_feature] = self
        if len(pre._next) > type(self)._number_of_branches:
            type(self)._number_of_branches = len(pre._next)

    def get_sequence(self) -> list[ExasSingleFeature]:
        return self.__sequence

    def set_sequence(self, sequence: list[ExasSingleFeature]):
        self.__sequence = sequence

    @override
    def get_feature_length(self) -> int:
        return len(self.__sequence)

    @override
    def __str__(self) -> str:
        return str(self.__sequence)

    @override
    def __hash__(self) -> int:
        if self._hash is None and len(self.__sequence) > 0:
            for i in range(len(self.__sequence)):
                self._hash = 31 * self._hash + hash(self.__sequence[i])
        return self._hash

    @override
    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if other == self:
            return True
        if isinstance(other, ExasSequentialFeature):
            if self.get_feature_length() != other.get_feature_length():
                return False
            for i in range(self.get_feature_length()):
                if self.__sequence[i] != other.__sequence[i]:
                    return False
            return True
        return False


class ExasSingleFeature(ExasFeature):
    features: dict[str, ExasSingleFeature] = {}  # static
    __label: str

    @multimethod
    def __init__(self, label: str):
        super().__init__()
        self.__label = label
        type(self).features[label] = self

    @multimethod
    def __init__(self, label_id: int):
        super().__init__()
        self.__label = str(label_id)
        type(self).features[self.__label] = self

    def get_label(self) -> str:
        return self.__label

    def set_label(self, label: str):
        self.__label = label

    @override
    def get_feature_length(self) -> int:
        return 1

    @override
    def __str__(self) -> str:
        return self.__label

    @override
    def __hash__(self) -> int:
        if self._hash is None and len(self.__label) > 0:
            self._hash = hash(self.__label)
        return self._hash

    @override
    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if other == self:
            return True
        if isinstance(other, ExasSingleFeature):
            return self.__label == other.get_label()
        return False
