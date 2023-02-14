from __future__ import annotations

from typing import Optional

from libadalang import AdaNode
from multimethod import multimethod
from overrides import override

from pdg_node import PDGNode
from pdg_data_edge import PDGDataEdge, Type


class PDGDataNode(PDGNode):
    _is_field: bool = False
    _is_declaration: bool = False
    _data_name: str

    @multimethod
    def __init__(self, ast_node: AdaNode, node_type: int, key: str, data_type: str, data_name: str):
        super().__init__(ast_node, node_type, key)
        self._data_type = data_type
        self._data_name = data_name

    @multimethod
    def __init__(self, ast_node: AdaNode, node_type: int, key: str, data_type: str, data_name: str, is_field: bool, is_declaration: bool):
        self.__init__(ast_node, node_type, key, data_type, data_name)
        self._is_field = is_field
        self._is_declaration = is_declaration

    @multimethod
    def __init__(self, node: PDGDataNode):
        self.__init__(node.get_ast_node(), node.get_ast_node_type(), node._data_type, node._data_name, node._is_field, node._is_declaration)

    @override
    def get_data_name(self) -> str:
        return self._data_name

    @override
    def get_label(self) -> str:
        raise NotImplementedError('get_label pdg_data_node')

    @override
    def get_exas_label(self) -> str:
        raise NotImplementedError('get_exas_label pdg_data_node')

    @override
    def is_definition(self) -> bool:
        for edge in self._in_edges:
            if isinstance(edge, PDGDataEdge):
                if edge.get_type() == Type.DEFINITION:
                    return True
        return False

    @override
    def is_same(self, node: PDGNode) -> bool:
        if isinstance(node, PDGDataNode):
            return self._data_name == node._data_name and self._data_type == node._data_type
        return False

    def is_dummy(self) -> bool:
        return self._key.startswith(self._PREFIX_DUMMY)

    def get_qualifier(self) -> Optional[PDGNode]:
        for edge in self.get_in_edges():
            if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.QUALIFIER:
                return edge.get_source()
        return None

    def copy_data(self, node: PDGDataNode):
        self._ast_node = node._ast_node
        self._ast_node_type = node._ast_node_type
        self._data_name = node._data_name
        self._data_type = node._data_type
        self._key = node._key
        self._is_field = node._is_field
        self._is_declaration = node._is_declaration

    @override
    def to_string(self) -> str:
        return self.get_label()
