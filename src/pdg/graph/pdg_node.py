from __future__ import annotations
import abc
import string

from libadalang import AdaNode

from pdg_edge import PDGEdge
from pdg_data_node import PDGDataNode
from pdg_action_node import PDGActionNode
from pdg_data_edge import PDGDataEdge, Type
from pdg_control_edge import PDGControlEdge
from pdg_control_node import PDGControlNode
from src.utils import ada_ast_util


class PDGNode:
    __metaclass__ = abc.ABCMeta

    _ast_node: AdaNode
    _ast_node_type: int
    _key: string
    _control: PDGNode
    _data_type: string
    _in_edges: list[PDGEdge]
    _out_edges: list[PDGEdge]

    version: int

    def __init__(self, ast_node: AdaNode, ast_node_type: int):
        self._ast_node = ast_node
        self._ast_node_type = ast_node_type

    def __init__(self, ast_node: AdaNode, ast_node_type: int, key: string):
        self.__init__(ast_node, ast_node_type)
        self._key = key

    def get_data_type(self) -> string:
        return self._data_type

    def get_data_name(self) -> string:
        if isinstance(self, PDGDataNode):
            return self.get_data_name()
        return None

    @abc.abstractmethod
    def get_label(self) -> string:
        return

    @abc.abstractmethod
    def get_exas_label(self) -> string:
        return

    def get_ast_node_type(self) -> int:
        return self._ast_node_type

    def get_ast_node(self) -> AdaNode:
        return self._ast_node

    def get_in_edges(self) -> list[PDGEdge]:
        return self._in_edges

    def get_out_edges(self) -> list[PDGEdge]:
        return self._out_edges

    def add_in_edge(self, edge: PDGEdge):
        self._in_edges.append(edge)

    def add_out_edge(self, edge: PDGEdge):
        self._out_edges.append(edge)

    def is_literal(self) -> bool:
        return ada_ast_util.is_literal(self._ast_node_type)

    def delete(self):
        for edge in self._in_edges:
            edge.get_source()._out_edges.remove(edge)
        self._in_edges.clear()
        for edge in self._out_edges:
            edge.get_target()._in_edges.remove(edge)
        self._out_edges.clear()
        self._control = None

    def is_definition(self) -> bool:
        if isinstance(self, PDGDataNode):
            return self.is_definition()
        return False

    def is_statement(self) -> bool:
        return self._control is not None

    def get_incoming_empty_nodes(self) -> list[PDGNode]:
        nodes: list[PDGNode] = []
        for edge in self._in_edges:
            if edge.get_source().is_empty_node():
                nodes.append(edge.get_source())
        return nodes

    def get_in_edges_for_exas_vectorization(self) -> list[PDGEdge]:
        edges: list[PDGEdge] = []
        for edge in self._in_edges:
            if (not isinstance(edge, PDGDataEdge)) or edge.get_type() != Type.DEPENDENCE:
                edges.append(edge)
        return edges

    def get_out_edges_for_exas_vectorization(self) -> list[PDGEdge]:
        edges: list[PDGEdge] = []
        for edge in self._out_edges:
            if (not isinstance(edge, PDGDataEdge)) or edge.get_type() != Type.DEPENDENCE:
                edges.append(edge)
        return edges

    def is_empty_node(self) -> bool:
        if isinstance(self, PDGActionNode):
            return self._name == 'empty'
        return False

    def __adjust_control(self, empty: PDGNode, index: int):
        edge: PDGControlEdge = self.get_in_edge(self._control)
        self._control._out_edges.remove(edge)
        edge._source = empty._control
        empty._control._out_edges.insert(index, edge)
        edge._label = empty.get_in_edge(empty._control).get_label()
        self._control = empty._control

    def get_in_edge(self, node: PDGNode) -> PDGEdge:
        for edge in self._in_edges:
            if edge.get_source() == node:
                return edge
        return None

    def adjust_control(self, node: PDGNode, empty: PDGNode):
        node_index: int = self._out_edges.index(node)
        out_edge_index: int = empty._control.get_out_edge_index(empty)
        while node_index < len (self._out_edges) and not self._out_edges[node_index].get_target().is_empty_node():
            out_edge_index += 1
            self._out_edges[node_index].get_target().__adjust_control(empty, out_edge_index)

    def get_in_dependences(self) -> list[PDGEdge]:
        edges: list[PDGEdge] = []
        for edge in self._in_edges:
            if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.DEPENDENCE:
                edges.append(edge)
        return edges

    def get_out_edge_index(self, node: PDGNode) -> int:
        i: int = 0
        while i < len(self._out_edges):
            if self._out_edges[i].get_target() == node:
                return i
            i += 1
        return -1

    def add_neighbors(self, nodes: set[PDGNode]):
        for edge in self._in_edges:
            if not isinstance(edge, PDGDataEdge) or (edge.get_type() != Type.DEPENDENCE and edge.get_type() != Type.REFERENCE):
                if not edge.get_source().is_empty_node() and edge.get_source() not in nodes:
                    nodes.add(edge.get_source())
                    edge.get_source().add_neighbors(nodes)
        for edge in self._out_edges:
            if not isinstance(edge, PDGDataEdge) or (edge.get_type() != Type.DEPENDENCE and edge.get_type() != Type.REFERENCE):
                if not edge.get_target().is_empty_node() and edge.get_target() not in nodes:
                    nodes.add(edge.get_target())
                    edge.get_target().add_neighbors(nodes)

    # TODO: implement this differently
    def is_same(self, node: PDGNode) -> bool:
        if self._key is None and node._key is not None:
            return False
        if self._key != node._key:
            return False
        if isinstance(self, PDGActionNode):
            return
        if isinstance(self, PDGDataNode):
            return
        if isinstance(self, PDGControlNode):
            return
        return False

    def get_definition(self) -> PDGNode:
        if isinstance(self, PDGDataNode) and len (self._in_edges) == 1 and isinstance(self._in_edges[0], PDGDataEdge):
            edge: PDGDataEdge = self._in_edges[0]
            if edge.get_type() == Type.REFERENCE:
                return edge.get_source()
        return None

    def get_definitions(self) -> list[PDGNode]:
        definitions: list[PDGNode] = []
        if isinstance(self, PDGDataNode):
            for edge in self._in_edges:
                if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.REFERENCE:
                    definitions.append(edge.get_source())
        return definitions

    def has_in_edge(self, node: PDGNode, label: string) -> bool:
        for edge in self._in_edges:
            if edge.get_source() == node and edge.get_label() == label:
                return True
        return False

    def has_in_edge(self, edge: PDGEdge) -> bool:
        for e in self._in_edges:
            if e.get_source() == edge.get_source() and e.get_label() == edge.get_label():
                return True
        return False

    def has_in_node(self, pre_node: PDGNode) -> bool:
        for edge in self._in_edges:
            if edge.get_source() == pre_node:
                return True
        return False

    def has_out_node(self, target: PDGNode) -> bool:
        for edge in self._out_edges:
            if edge.get_target() == target:
                return True
        return False

    def is_valid(self) -> bool:
        s: set[PDGNode] = set()
        for edge in self._out_edges:
            if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.DEPENDENCE:
                continue
            if edge.get_target() in s:
                return False
            s.add(edge.get_target())
        return True

