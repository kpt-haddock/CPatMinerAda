import string

from pdg_edge import PDGEdge
from pdg_node import PDGNode


class PDGControlEdge(PDGEdge):
    _label: string

    def __init__(self, point: PDGNode, next: PDGNode, label: string):
        super().__init__(point, next)
        self._label = label
        self._source.add_out_edge(self)
        self._target.add_in_edge(self)

    # override
    def get_label(self) -> string:
        return self._label

    # override
    def get_exas_label(self) -> string:
        return '_control_'

    # override
    def to_string(self):
        return self.get_label()
