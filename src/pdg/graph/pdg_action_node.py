from __future__ import annotations
from multimethod import multimethod

from pdg_node import PDGNode
from pdg_data_node import PDGDataNode
from pdg_control_edge import PDGControlEdge


def overlap(s1: set, s2: set) -> bool:
    return len(s1.intersection(s2)) != 0


class PDGActionNode(PDGNode):
    RECURSIVE: str = 'recur'
    _name: str
    _parameter_types: [str]
    _exception_types: []
    __control_edge: PDGControlEdge
    @multimethod
    def __init__(self, control: PDGNode, branch: str, ast_node, node_type: int, key: str, type: str, name: str):
        super().__init__(ast_node, node_type, key)
        if control is not None:
            self._control = control
            self.__control_edge = PDGControlEdge(control, self, branch)
        self._data_type = type
        self._name = name

    @multimethod
    def __init__(self, control: PDGNode, branch: str, ast_node, node_type: int, key: str, type: str, name: str, exception_types):
        self.__init__(control, branch, ast_node, node_type, key, type, name)
        self._exception_types = exception_types

    # override
    def get_label(self) -> str:
        return self._name + '' if self._parameter_types is None else self.__build_parameters()

    # override
    def get_exas_label(self) -> str:
        i: int = self._name.rfind('.') + 1
        return self._name[i:-1]

    def __build_parameters(self) -> str:
        return '({})'.format(','.join(self._parameter_types))

    # override
    def is_same(self, node: PDGNode) -> bool:
        if isinstance(node, PDGActionNode):
            return self._name == node._name
        return False

    # override
    def is_definition(self) -> bool:
        return False

    # override
    def to_string(self) -> str:
        return self.get_label()

    def has_backward_data_dependence(self, pre_node: PDGActionNode) -> bool:
        definitions: set[PDGNode] = set()
        pre_definitions: set[PDGNode] = set()
        fields: set[str] = set()
        pre_fields: set[str] = set()
        self.get_definitions(definitions, fields)
        pre_node.get_definitions(pre_definitions, pre_fields)
        return overlap(definitions, pre_definitions) or overlap(fields, pre_fields)

    def get_definitions(self, definitions: set[PDGNode], fields: set[str]):
        for e in self._in_edges:
            if isinstance(e.get_source(), PDGDataNode):
                temporary_definitions: list[PDGNode] = e.get_source().get_definitions()
                if len(temporary_definitions) == 0:
                    fields.add(e.get_source()._key)
                else:
                    definitions.update(temporary_definitions)
