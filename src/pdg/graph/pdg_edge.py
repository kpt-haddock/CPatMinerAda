from pdg_node import PDGNode
import abc


class PDGEdge:
    __metaclass__ = abc.ABCMeta

    _source: PDGNode
    _target: PDGNode

    def __init__(self, source: PDGNode, target: PDGNode):
        self._source = source
        self._target = target

    @abc.abstractmethod
    def get_label(self) -> str:
        ...

    def get_source(self) -> PDGNode:
        return self._source

    def get_target(self) -> PDGNode:
        return self._target

    @abc.abstractmethod
    def get_exas_label(self) -> str:
        ...

