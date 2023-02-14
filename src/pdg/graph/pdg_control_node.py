from libadalang import AdaNode

from pdg_control_edge import PDGControlEdge
from pdg_graph import PDGGraph
from pdg_node import PDGNode


class PDGControlNode(PDGNode):
    __control_edge: PDGControlEdge

    def __init__(self, control: PDGNode, branch: str, ast_node: AdaNode, node_type: int):
        super().__init__(ast_node, node_type)
        self._control = control
        self.__control_edge = PDGControlEdge(control, self, branch)

    # override
    def get_label(self) -> str:
        return self.get_ast_node().kind_name

    # override
    def get_exas_label(self) -> str:
        return self.get_ast_node().kind_name

    # override
    @staticmethod
    def is_definition(self) -> bool:
        return False

    # override
    def to_string(self) -> str:
        return self.get_label()

    def get_body(self) -> PDGGraph:
        graph: PDGGraph = PDGGraph(None)
        graph.get_nodes().add(self)
        for edge in self.get_out_edges():
            node: PDGNode = edge.get_target()
            if not node.is_empty_node():
                graph.get_nodes().add(node)
        for edge in self.get_out_edges():
            node: PDGNode = edge.get_target()
            node.add_neighbors(graph.get_nodes())
        graph.get_nodes().remove(self)
        return graph

    # override
    def is_same(self, node: PDGNode) -> bool:
        if isinstance(node, PDGControlNode):
            return self.get_ast_node_type() == node.get_ast_node_type()
        return False
