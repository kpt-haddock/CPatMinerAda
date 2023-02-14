from __future__ import annotations

from multimethod import multimethod
from overrides import override

from exas_feature import ExasFeature


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
