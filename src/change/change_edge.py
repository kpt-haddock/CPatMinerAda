from change_node import ChangeNode
from src.pdg.graph.pdg_edge import PDGEdge


class ChangeEdge:
    source: ChangeNode
    target: ChangeNode
    label: str

    def __init__(self, source: ChangeNode, target: ChangeNode, e: PDGEdge):
        self.source = source
        self.target = target
        self.label = e.get_exas_label()
        source.out_edges.append(self)
        target.in_edges.append(self)

    def get_source(self) -> ChangeNode:
        return self.source

    def get_target(self) -> ChangeNode:
        return self.target

    def get_label(self) -> str:
        return self.label

    def is_mapped(self) -> bool:
        return self.label == '_map_'

    def to_string(self) -> str:
        return self.label
