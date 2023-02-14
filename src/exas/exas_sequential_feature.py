from overrides import override

from exas_feature import ExasFeature
from exas_single_feature import ExasSingleFeature


class ExasSequentialFeature(ExasFeature):
    __sequence: list[ExasSingleFeature] = []

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
