import libadalang as lal
from utils.ada_node_visitor import AdaNodeVisitor
from overrides import overrides


class AdaNodeIdMapper(AdaNodeVisitor):
    node_id = {}
    id_node = {}
    cnt = 1

    @overrides
    def pre_visit(self, node: lal.AdaNode):
        self.node_id[node] = self.cnt
        self.id_node[self.cnt] = node
        self.cnt += 1
