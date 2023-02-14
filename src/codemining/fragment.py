from __future__ import annotations
from abc import abstractmethod, ABC

from feature import Feature
from src.codemining.bucket import Bucket


class Fragment(ABC):

    @abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError('get_id not implemented')

    @abstractmethod
    def get_vector(self) -> dict[Feature, int]:
        raise NotImplementedError('get_vector not implemented')

    @abstractmethod
    def get_vector_length(self) -> float:
        raise NotImplementedError('get_vector_length not implemented')

    @abstractmethod
    def get_buckets(self) -> set[Bucket]:
        raise NotImplementedError('get_buckets not implemented')

    @abstractmethod
    def get_clones(self) -> set[Fragment]:
        raise NotImplementedError('get_clones not implemented')

    @abstractmethod
    def set_clones(self, clones: set[Fragment]):
        raise NotImplementedError('set_clones not implemented')

    @abstractmethod
    def distance(self, other: Fragment) -> float:
        raise NotImplementedError('distance not implemented')

    @abstractmethod
    def get_size(self) -> int:
        raise NotImplementedError('get_size not implemented')