from abc import ABC, abstractmethod


class Feature(ABC):

    @abstractmethod
    def get_id(self):
        pass
