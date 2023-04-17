from __future__ import annotations

import abc
import warnings
from enum import Enum
from typing import Optional, Final, cast

import libadalang
from libadalang import AdaNode, SubpBody, ReturnStmt
from multimethod import multimethod
from overrides import override

from src.exas.exas_feature import ExasFeature
from src.utils import ada_ast_util


def overlap(s1: set, s2: set) -> bool:
    return len(s1.intersection(s2)) != 0


class PDGNode:
    __metaclass__ = abc.ABCMeta
    _PREFIX_DUMMY: Final[str] = 'dummy_'

    _ast_node: AdaNode
    _ast_node_type: int
    _key: str
    _control: PDGNode
    _data_type: str
    _in_edges: list[PDGEdge]
    _out_edges: list[PDGEdge]

    version: int

    @multimethod
    def __init__(self, ast_node: AdaNode, ast_node_type: int):
        self._ast_node = ast_node
        self._ast_node_type = ast_node_type

    @multimethod
    def __init__(self, ast_node: AdaNode, ast_node_type: int, key: str):
        self.__init__(ast_node, ast_node_type)
        self._key = key

    def get_data_type(self) -> str:
        return self._data_type

    def get_data_name(self) -> str:
        if isinstance(self, PDGDataNode):
            return self.get_data_name()
        return None

    @abc.abstractmethod
    def get_label(self) -> str:
        return

    @abc.abstractmethod
    def get_exas_label(self) -> str:
        return

    def get_ast_node_type(self) -> int:
        warnings.warn('AST NODE TYPE SHOULD BE AdaNode Type not int')
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

    def get_definition(self) -> Optional[PDGNode]:
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

    @multimethod
    def has_in_edge(self, node: PDGNode, label: str) -> bool:
        for edge in self._in_edges:
            if edge.get_source() == node and edge.get_label() == label:
                return True
        return False

    @multimethod
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


class PDGEdge:
    __metaclass__ = abc.ABCMeta

    _source: PDGNode
    _target: PDGNode

    def __init__(self, source: PDGNode, target: PDGNode):
        self._source = source
        self._target = target

    @abc.abstractmethod
    def get_label(self) -> str:
        pass

    def get_source(self) -> PDGNode:
        return self._source

    def get_target(self) -> PDGNode:
        return self._target

    @abc.abstractmethod
    def get_exas_label(self) -> str:
        pass


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


class PDGBuildingContext:
    pass


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

    def __str__(self) -> str:
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


class Type(Enum):
    RECEIVER = 1
    PARAMETER = 2
    DEFINITION = 3
    REFERENCE = 4
    CONDITION = 5
    DEPENDENCE = 6
    QUALIFIER = 7
    MAP = 8


class PDGDataEdge(PDGEdge):
    _type: Type

    def __init__(self, source: PDGNode, target: PDGNode, type: Type):
        super().__init__(source, target)
        self._type = type
        self._source.add_out_edge(self)
        self._target.add_in_edge(self)

    def get_type(self) -> Type:
        return self._type

    # override
    def get_label(self) -> str:
        match self._type:
            case Type.RECEIVER:
                return 'recv'
            case Type.PARAMETER:
                return 'oara'
            case Type.DEFINITION:
                return 'def'
            case Type.REFERENCE:
                return 'ref'
            case Type.CONDITION:
                return 'cond'
            case Type.DEPENDENCE:
                return 'dep'
            case Type.QUALIFIER:
                return 'qual'
            case Type.MAP:
                return 'map'
            case _:
                return ''

    # override
    def get_exas_label(self) -> str:
        match self._type:
            case Type.RECEIVER:
                return '_recv_'
            case Type.PARAMETER:
                return '_oara_'
            case Type.DEFINITION:
                return '_def_'
            case Type.REFERENCE:
                return '_ref_'
            case Type.CONDITION:
                return '_cond_'
            case Type.DEPENDENCE:
                return '_dep_'
            case Type.QUALIFIER:
                return '_qual_'
            case Type.MAP:
                return '_map_'
            case _:
                return '_data_'

    def __str__(self) -> str:
        return self.get_label()


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
    def __str__(self) -> str:
        return self.get_label()


class PDGEntryNode(PDGNode):
    __label: str

    def __init__(self, ast_node: AdaNode, ast_node_type: int, label: str):
        super().__init__(ast_node, ast_node_type)
        self.__label = label

    # override
    def get_label(self) -> str:
        return self.__label

    # override
    def get_exas_label(self) -> str:
        return self.__label

    # override
    @staticmethod
    def is_definition() -> bool:
        return False

    # override
    def to_string(self) -> str:
        return self.get_label()


class PDGGraph:
    __context: PDGBuildingContext
    __definition_store: dict[str, set[PDGDataNode]] = {}
    _entry_node: PDGNode
    _end_node: PDGNode
    _parameters: list[PDGDataNode]
    _nodes: set[PDGNode] = set()
    _statement_nodes: set[PDGNode] = set()
    _data_sources: set[PDGDataNode] = set()
    _statement_sources: set[PDGNode] = set()
    _sinks: set[PDGNode] = set()
    _statement_sinks: set[PDGNode] = set()
    _breaks: set[PDGNode] = set()
    _returns: set[PDGNode] = set()
    _changed_nodes: set[PDGNode] = set()

    __exas_vector: dict[ExasFeature, int] = {}

    @multimethod
    def __init__(self, method_declaration, context: Optional[PDGBuildingContext]):
        self.__context = context

    @multimethod
    def __init__(self, context: Optional[PDGBuildingContext], node: PDGNode):
        self.__context = context
        self.__init(node)

    def __init(self, node: PDGNode):
        if isinstance(node, PDGDataNode) and not node.is_literal():
            self._data_sources.add(node)
        self._sinks.add(node)
        self._nodes.add(node)
        if node.is_statement():
            self._statement_nodes.add(node)
            self._statement_sources.add(node)
            self._statement_sinks.add(node)

    def get_nodes(self) -> set[PDGNode]:
        return self._nodes

    def get_changed_nodes(self) -> set[PDGNode]:
        return self._changed_nodes

    def get_exas_vector(self) -> dict[ExasFeature, int]:
        return self.__exas_vector

    # TODO build_PDG methods

    def merge_branches(self, pdgs: list[PDGGraph]):
        definition_store: dict[str, set[PDGDataNode]] = {}
        definition_counts: dict[str, int] = {}
        self._sinks.clear()
        self._statement_sinks.clear()
        for pdg in pdgs:
            self._nodes.update(pdg._nodes)
            self._statement_nodes.update(pdg._statement_nodes)
            self._sinks.update(pdg._sinks)
            self._statement_sinks.update(pdg._statement_sinks)
            for source in pdg._data_sources.copy():  # why do we need a copy?
                definitions: set[PDGDataNode] = self.__definition_store.get(source._key)
                if definitions is not None:
                    for definition in definitions:
                        if definition is not None:
                            PDGDataEdge(definition, source, Type.REFERENCE)
                    if None not in definitions:
                        pdg._data_sources.remove(source)
            self._data_sources.update(pdg._data_sources)
            self._breaks.update(pdg._breaks)
            self._returns.update(pdg._returns)
        for pdg in pdgs:
            local_store: dict[str, set[PDGDataNode]] = self.copy_definition_store()
            self.update_definition_store(local_store, definition_counts, pdg.__definition_store)
            PDGGraph.add(definition_store, local_store)
            pdg.clear()
        for key in definition_counts.keys():
            if definition_counts.get(key) < len(pdgs):
                definition_store.get(key).add(None)
        self.clear_definition_store()
        self.__definition_store = definition_store

    def merge_parallel(self, pdgs: list[PDGGraph]):
        definition_store: dict[str, set[PDGDataNode]] = {}
        definition_counts: dict[str, int] = {}
        for pdg in pdgs:
            local_store: dict[str, set[PDGDataNode]] = self.copy_definition_store()
            self._nodes.update(pdg._nodes)
            self._statement_nodes.update(pdg._statement_nodes)
            self._sinks.update(pdg._sinks)
            self._statement_sinks.update(pdg._statement_sinks)
            self._data_sources.update(pdg._data_sources)
            self._statement_sources.update(pdg._statement_sources)
            self._breaks.update(pdg._breaks)
            self._returns.update(pdg._returns)
            self.update_definition_store(local_store, definition_counts, pdg.__definition_store)
            PDGGraph.add(definition_store, local_store)
            pdg.clear()
        self.clear_definition_store()
        self.__definition_store = definition_store

    @multimethod
    def clear(self):
        self._nodes.clear()
        self._statement_nodes.clear()
        self._data_sources.clear()
        self._statement_sources.clear()
        self._sinks.clear()
        self._statement_sinks.clear()
        self._breaks.clear()
        self._returns.clear()
        self.clear_definition_store()

    def delete(self, node: PDGNode):
        if node in self._statement_sinks:
            for edge in node.get_in_edges():
                if isinstance(edge, PDGDataEdge):
                    if edge.get_type() == Type.DEPENDENCE:
                        self._statement_sinks.add(edge.get_source())
                    elif edge.get_type() == Type.PARAMETER:
                        self._sinks.add(edge.get_source())
        if node in self._sinks and isinstance(node, PDGDataNode):
            for edge in node.get_in_edges():
                if isinstance(edge.get_source(), PDGDataNode):
                    self._sinks.add(edge.get_source())
        if node in self._statement_sources:
            for edge in node.get_out_edges():
                if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.DEPENDENCE:
                    self._statement_sources.add(edge.get_target())
        self._nodes.remove(node)
        self._changed_nodes.remove(node)
        self._statement_nodes.remove(node)
        self._data_sources.remove(node)
        self._statement_sources.remove(node)
        self._sinks.remove(node)
        self._statement_sinks.remove(node)
        node.delete()

    def build_argument_pdg(self, control: PDGNode, branch: str, exp: AdaNode) -> PDGGraph:
        raise NotImplementedError

    def build_pdg(self, control: PDGNode, branch: str, ast_node):  # ast_node: ArrayAccess
        raise NotImplementedError

    # TODO: other buildPDG methods

    def merge_sequential(self, pdg: PDGGraph):
        if not pdg._statement_nodes:
            return
        for source in pdg._data_sources.copy():  # why do we need a copy?
            definitions: set[PDGDataNode] = self.__definition_store.get(source._key)
            if definitions:
                for definition in definitions:
                    if definition:
                        PDGDataEdge(definition, source, Type.REFERENCE)
                if None not in definitions:
                    pdg._data_sources.remove(source)
        self.update_definition_store(pdg.__definition_store)
        for sink in self._statement_sinks:
            for source in pdg._statement_sources:
                PDGDataEdge(sink, source, Type.DEPENDENCE)
        self._data_sources.update(pdg._data_sources)
        self._sinks.clear()
        self._statement_sinks.clear()
        self._statement_sinks.update(pdg._statement_sinks)
        self._nodes.update(pdg._nodes)
        self._statement_nodes.update(pdg._statement_nodes)
        self._breaks.update(pdg._breaks)
        self._returns.update(pdg._returns)
        pdg.clear()


    @staticmethod
    def add(target: dict[str, set[object]],
            source: dict[str, set[object]]):
        for key in source.keys():
            if key in target:
                target.get(key).update(source.get(key).copy())
            else:
                target[key] = source.get(key).copy()

    @staticmethod
    @multimethod
    def clear(map: dict):
        for key in map.keys():
            map[key].clear()
        map.clear()

    @staticmethod
    def update(target: dict[str, set[object]], source: dict[str, set[object]]):
        for key in source.keys():
            s: set[object] = source.get(key)
            if None in s:
                if key in target:
                    s.remove(None)
                    target.get(key).update(s.copy())  # This copy seems unnecessary
                else:
                    target[key] = s.copy()
            else:
                target[key] = s.copy()

    def clear_definition_store(self):
        self.clear(self.__definition_store)

    def copy_definition_store(self) -> dict[str, set[PDGDataNode]]:
        store: dict[str, set[PDGDataNode]] = dict()
        for key in self.__definition_store.keys():
            store[key] = self.__definition_store.get(key).copy()
        return store

    @multimethod
    def update_definition_store(self, store: dict[str, set[PDGDataNode]]):
        PDGGraph.update(self.__definition_store, store)

    @multimethod
    def update_definition_store(self,
                                target: dict[str, set[PDGDataNode]],
                                definition_counts: dict[str, int],
                                source: dict[str, set[PDGDataNode]]):
        for key in source.keys():
            target[key] = source.get(key).copy()
        for key in target.keys():
            c: int = 1
            if key in definition_counts:
                c += definition_counts.get(key)
            definition_counts[key] = c

    @multimethod
    def merge_sequential_control(self, next: PDGNode, label: str):
        self._sinks.clear()
        self._sinks.add(next)
        self._statement_sinks.clear()
        self._statement_sinks.add(next)
        if not self._statement_nodes:
            self._statement_sources.add(next)
        self._nodes.add(next)
        self._statement_nodes.add(next)

    def merge_sequential_data(self, next: PDGNode, type: Type):
        if next.is_statement():
            for sink in self._statement_sinks:
                PDGDataEdge(sink, next, Type.DEPENDENCE)
        if type == Type.DEFINITION:
            s: set[PDGDataNode] = set()
            s.add(cast(PDGDataNode, next))
            self.__definition_store[next._key] = s
        elif type == Type.QUALIFIER:
            self._data_sources.add(cast(PDGDataNode, next))
        elif type != Type.REFERENCE and isinstance(next, PDGDataNode):
            s: set[PDGDataNode] = self.__definition_store.get(next._key, None)
            if s is not None:
                for definition in s:
                    PDGDataEdge(definition, next, Type.REFERENCE)
        for node in self._sinks:
            PDGDataEdge(node, next, type)
        self._sinks.clear()
        self._sinks.add(next)
        if not self._nodes and isinstance(next, PDGDataNode):
            self._data_sources.add(cast(PDGDataNode, next))
        self._nodes.add(next)
        if next.is_statement():
            self._statement_nodes.add(next)
            if not self._statement_sources:
                self._statement_sources.add(next)
            self._statement_sinks.clear()
            self._statement_sinks.add(next)

    def extend(self, ret: PDGNode, node: PDGDataNode, type: Type):
        s: set[PDGDataNode] = set()
        s.add(node)
        self.__definition_store[node._key] = s
        self._nodes.add(node)
        self._sinks.remove(ret)
        self._sinks.add(node)
        PDGDataEdge(ret, node, type)

    @multimethod
    def merge_sequential_control(self, pdg: PDGGraph):
        if not pdg._statement_nodes:
            return
        if not self._statement_nodes or not pdg._statement_nodes:
            raise SystemError('Merging an empty graph?!')
        self._sinks.clear()
        self._statement_sinks.clear()
        self._statement_sinks.update(pdg._statement_sinks)
        self._nodes.update(pdg._nodes)
        self._statement_nodes.update(pdg._statement_nodes)
        self._breaks.update(pdg._breaks)
        self._returns.update(pdg._returns)
        pdg.clear()

    def adjust_break_nodes(self, id: Optional[str]):
        for node in self._breaks.copy():
            if (node._key is None and id is None) or node._key == id:
                self._sinks.add(node)
                self._statement_sinks.add(node)
                self._breaks.remove(node)

    def adjust_return_nodes(self):
        self._sinks.update(self._returns)
        self._statement_sinks.update(self._returns)
        self._returns.clear()
        self._end_node = PDGEntryNode(None, SubpBody, 'END')
        for sink in self._statement_sinks:
            PDGDataEdge(sink, self._end_node, Type.DEPENDENCE)
        self._sinks.clear()
        self._statement_sinks.clear()
        self._nodes.add(self._end_node)
        self._statement_nodes.remove(self._entry_node)

    def adjust_control_edges(self):
        for node in self._statement_nodes:
            incoming_empty_nodes: list[PDGNode] = node.get_incoming_empty_nodes()
            if len(incoming_empty_nodes) == 1 and len(node.get_in_dependences()) == 1:
                empty_node: PDGNode = incoming_empty_nodes[0]
                if node._control != empty_node._control:
                    node._control.adjust_control(node, empty_node)

    def get_definitions(self) -> list[PDGDataNode]:
        definitions: list[PDGDataNode] = []
        for node in self._sinks:
            if node.is_definition():
                definitions.append(cast(PDGDataNode, node))
        return definitions

    def get_returns(self) -> list[PDGActionNode]:
        nodes: list[PDGActionNode] = []
        for node in self._statement_sinks:
            if node.get_ast_node_type() == ReturnStmt:
                nodes.append(cast(PDGActionNode, node))
        return nodes

    def get_only_out(self) -> PDGNode:
        if len(self._sinks) == 1:
            for n in self._sinks:
                return n
        raise RuntimeError('Error in getting the only output node!!!')

    def get_only_data_out(self):
        if len(self._sinks) == 1:
            for n in self._sinks:
                if isinstance(n, PDGDataNode):
                    return cast(PDGDataNode, n)
        raise SystemExit('Error in getting the only data output node!!!')

    def is_empty(self) -> bool:
        if self._nodes:
            return False
        return True

    def build_closure(self):
        done_nodes: set[PDGNode] = set()
        for node in self._nodes:
            if node not in done_nodes:
                self.build_data_closure(node, done_nodes)
        self.build_sequential_closure()
        done_nodes.clear()
        done_nodes = set()  # why?
        for node in self._nodes:
            if node not in done_nodes:
                self.build_control_closure(node, done_nodes)

    @multimethod
    def build_sequential_closure(self):
        pre_nodes_of_node: dict[PDGNode, list[PDGNode]] = {self._entry_node: []}
        for node in self._nodes:
            if node == self._entry_node or isinstance(node, PDGControlNode):
                branch_nodes: dict[str, list[PDGNode]] = {'T': [], 'F': [], '': []}
                for edge in node.get_out_edges():
                    if (edge.get_target() != self._end_node
                            and edge.get_target()._control is not None
                            and not isinstance(edge.get_target().get_ast_node_type(), libadalang.AssignStmt)):
                        branch_nodes.get(edge.get_label()).append(edge.get_target())
                for branch in branch_nodes.keys():
                    nodes: list[PDGNode] = branch_nodes.get(branch)
                    for i in range(0, len(nodes)): # TODO: this could be implemented with slices
                        n: PDGNode = nodes[i]
                        pre_nodes: list[PDGNode] = []
                        for j in range(0, i):
                            pre_nodes.append(nodes[j])
                        pre_nodes_of_node[n] = pre_nodes
        done_nodes: set[PDGNode] = {self._entry_node}
        for node in pre_nodes_of_node.keys():
            if node not in done_nodes:
                self.build_sequential_closure(node, done_nodes, pre_nodes_of_node)
        for node in pre_nodes_of_node.keys():
            if isinstance(node, PDGActionNode):
                for pre_node in pre_nodes_of_node.get(node):
                    if (isinstance(pre_node, PDGActionNode)
                            and not node.has_in_node(pre_node)
                            and node.has_backward_data_dependence(pre_node)):
                        PDGDataEdge(pre_node, node, Type.DEPENDENCE)

    @multimethod
    def build_sequential_closure(self, node: PDGNode, done_nodes: set[PDGNode], pre_nodes_of_node: dict[PDGNode, list[PDGNode]]):
        if node._control not in done_nodes:
            self.build_sequential_closure(node._control, done_nodes, pre_nodes_of_node)
        pre_nodes_of_node.get(node).extend(pre_nodes_of_node.get(node._control))
        done_nodes.add(node)

    def build_data_closure(self, node: PDGNode, done_nodes: set[PDGNode]):
        if not node.get_definitions():
            for edge in node.get_in_edges().copy():  # why do we need a copy?
                if isinstance(edge, PDGDataEdge):
                    label: str = edge.get_label()
                    in_nodes: list[PDGNode] = edge.get_source().get_definitions()
                    if not in_nodes:
                        in_nodes.append(edge.get_source())
                    else:
                        for in_node in in_nodes:
                            if not node.has_in_edge(in_node, label):
                                PDGDataEdge(in_node, node, edge.get_type())
                    for in_node in in_nodes:
                        if in_node not in done_nodes:
                            self.build_data_closure(in_node, done_nodes)
                        for in_edge in in_node.get_in_edges():
                            if isinstance(in_edge, PDGDataEdge) and not isinstance(in_edge.get_source(), PDGDataNode):
                                if not node.has_in_edge(in_edge.get_source(), label):
                                    PDGDataEdge(in_edge.get_source(), node, edge.get_type())
        done_nodes.add(node)

    def build_control_closure(self, node: PDGNode, done_nodes: set[PDGNode]):
        for edge in node.get_in_edges().copy():  # why do we need a copy?
            if isinstance(edge, PDGControlEdge):
                in_node: PDGNode = edge.get_source()
                if in_node not in done_nodes:
                    self.build_control_closure(in_node, done_nodes)
                for in_edge in in_node.get_in_edges():
                    if isinstance(node, (PDGActionNode, PDGControlNode)) and not node.has_in_edge(in_edge):
                        PDGControlEdge(in_edge.get_source(), node, in_edge.get_label())
        done_nodes.add(node)

    def prune(self):
        self.delete(self._end_node)
        self.prune_data_nodes()
        self.prune_empty_statement_nodes()
        self.prune_temporary_data_dependence()

    # TODO: check if no mistakes were made copying this method!
    def prune_temporary_data_dependence(self):
        for node in self._nodes:
            if node == self._entry_node or node == self._end_node:
                continue
            i: int = 0
            while i < len(node.get_in_edges()):
                edge: PDGEdge = node.get_in_edges()[i]
                if edge.get_source() != self._entry_node\
                        and isinstance(edge, PDGDataEdge)\
                        and edge.get_type() == Type.DEPENDENCE:
                    del node.get_in_edges()[i]
                    edge.get_source().get_out_edges().remove(edge)
                    edge._source = None
                    edge._target = None
                else:
                    i += 1
            i = 0
            while i < len(node.get_out_edges()):
                edge: PDGEdge = node.get_out_edges()[i]
                if edge.get_target() != self._end_node\
                        and isinstance(edge, PDGDataEdge)\
                        and edge.get_type() == Type.DEPENDENCE:
                    del node.get_out_edges()[i]
                    edge.get_target().get_in_edges().remove(edge)
                    edge._source = None
                    edge._target = None
                else:
                    i += 1

    def prune_isolated_nodes(self):
        raise NotImplementedError('This method had no uses in CPatMiner.')

    def get_reachable_nodes(self) -> set[PDGNode]:
        raise NotImplementedError('This method was used in prune_isolated_nodes.')

    def prune_data_nodes(self):
        # self.prune_definition_nodes()
        self.prune_dummy_nodes()

    def prune_dummy_nodes(self):
        for node in self._nodes.copy():  # why do we need a copy?
            if isinstance(node, PDGDataNode):
                data_node: PDGDataNode = cast(PDGDataNode, node)
                if data_node.is_dummy() and data_node.is_definition() and len(data_node.get_out_edges()) <= 1:
                    a: PDGNode = data_node.get_in_edges()[0].get_source()
                    s: PDGNode = a.get_in_edges()[0].get_source()
                    if isinstance(s, PDGDataNode):
                        dr: PDGNode = data_node.get_out_edges()[0].get_target()
                        if len(dr.get_in_edges()) == 1:
                            edge: PDGDataEdge = cast(PDGDataEdge, dr.get_out_edges()[0])
                            PDGDataEdge(s, edge.get_target(), edge.get_type())
                            self.delete(dr)
                            self.delete(data_node)
                            self.delete(a)

    def prune_definition_nodes(self):
        for node in self._nodes.copy():
            if node.is_definition() and cast(PDGDataNode, node)._is_declaration and not node.get_out_edges():
                for edge1 in node.get_in_edges().copy():
                    for edge2 in edge1.get_source().get_in_edges():
                        if isinstance(edge2, PDGDataEdge) and edge2.get_type() == Type.PARAMETER:
                            self.delete(edge2.get_source())
                    self.delete(edge1.get_source())
                self.delete(node)

    def prune_empty_statement_nodes(self):
        for node in self._statement_nodes.copy():
            if node.is_empty_node():
                index: int = node._control.get_out_edge_index(node)
                for out in node.get_out_edges().copy():
                    if out.get_target()._control != node._control:
                        out.get_source().get_out_edges().remove(out)
                        out._source = node._control
                        index += 1
                        out.get_source().get_out_edges().insert(index, out)
                self.delete(node)
                # node = None # I do not think this statement makes sense.

    @multimethod
    def build_exas_vector(self):
        raise NotImplementedError('This method has no usages in CPatMiner original')

    @multimethod
    def build_exas_vector(self, exas_graph: set[PDGNode], node: PDGNode):
        raise NotImplementedError('This method was used in build_exas_vector in CPatMiner original')

    def backward_dfs(self):
        raise NotImplementedError('This method was used in build_exas_vector in CPatMiner original')

    def forward_dfs(self):
        raise NotImplementedError('This method was used in backward_dfs in CPatMiner original')

    def add_feature(self):
        raise NotImplementedError('This method was used in forward_dfs in CPatMiner original')

    def print_vector(self):
        raise NotImplementedError('This method has no usages in CPatMiner original')

    def build_change_graph(self, version: int):
        self.add_definitions()
        # self.mark_changes(self._entry_node.get_ast_node())
        for node in self._nodes:
            if isinstance(node, PDGEntryNode):
                continue
            ast_node: AdaNode = node.get_ast_node()
            if ast_node is not None and ada_ast_util.is_changed(ast_node):
                definitions: list[PDGNode] = node.get_definitions()
                if definitions:
                    self._changed_nodes.update(definitions)
                    for definition in definitions:
                        definition.version = version
                self._changed_nodes.add(node)
                node.version = version
        self.prune()
        self.build_closure()
        self.clean_up()

    @multimethod
    def add_definitions(self):
        definitions: dict[str, PDGNode] = {}
        for node in self._nodes.copy():
            if isinstance(node, PDGDataNode) and not node.is_literal() and not node.is_definition():
                self.add_definitions(cast(PDGDataNode, node), definitions)

    @multimethod
    def add_definitions(self, node: PDGDataNode, definitions: dict[str, PDGNode]):
        if not node.get_definitions() and node.get_qualifier() is None:
            definition: PDGNode = definitions.get(node._key)
            if definition is None:
                definition = PDGDataNode(None, node.get_ast_node_type(), node._key, node.get_data_type(), node.get_data_name, True, True)
                definitions[node._key] = definition
                self._nodes.add(definition)
            PDGDataEdge(definition, node, Type.REFERENCE)
            for edge in node.get_out_edges():
                if not definition.has_out_node(edge.get_target()):
                    PDGDataEdge(definition, edge.get_target(), cast(PDGDataEdge, edge).get_type())

    def clean_up(self):
        self.clear_definition_store()
        for node in self._nodes:
            i: int = 0
            while i < len(node.get_in_edges()):
                edge: PDGEdge = node.get_in_edges()[i]
                if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.DEPENDENCE:
                    del node._in_edges[i]
                else:
                    i += 1
            i: int = 0
            while i < len(node.get_out_edges()):
                edge = node.get_out_edges()[i]
                if isinstance(edge, PDGDataEdge) and edge.get_type() == Type.DEPENDENCE:
                    del node._out_edges[i]
                else:
                    i += 1

    def is_changed_node(self, node: PDGNode) -> bool:
        return node in self._changed_nodes

    def is_valid(self) -> bool:
        for node in self._nodes:
            if not node.is_valid():
                return False
        return True
