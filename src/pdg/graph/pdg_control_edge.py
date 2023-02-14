from pdg_edge import PDGEdge
from pdg_node import PDGNode


class PDGControlEdge(PDGEdge):
    _label: str

    def __init__(self, point: PDGNode, next: PDGNode, label: str):
        super().__init__(point, next)
        self._label = label
        self._source.add_out_edge(self)
        self._target.add_in_edge(self)

    # override
    def get_label(self) -> str:
        return self._label

    # override
    def get_exas_label(self) -> str:
        return '_control_'

    # override
    def to_string(self) -> str:
        return self.get_label()
