from __future__ import annotations

import abc
import warnings
from collections import deque
from enum import Enum
from typing import Optional, Final, cast
from warnings import warn

from libadalang import *
from multimethod import multimethod
from overrides import override

from src.exas.exas_feature import ExasFeature
from src.treed.treed import TreedConstants
from src.utils import ada_ast_util
from src.utils.ada_ast_util import node_type, start_position


def overlap(s1: set, s2: set) -> bool:
    return len(s1.intersection(s2)) != 0


class PDGNode:
    __metaclass__ = abc.ABCMeta
    PREFIX_DUMMY: Final[str] = 'dummy_'

    _ast_node: Optional[AdaNode]
    _ast_node_type: int
    _key: Optional[str]
    _control: Optional[PDGNode]
    _data_type: Optional[str]
    _in_edges: list[PDGEdge]
    _out_edges: list[PDGEdge]

    version: int

    @multimethod
    def __init__(self, ast_node: Optional[AdaNode], ast_node_type: int):
        self._control = None
        self._data_type = None
        self._ast_node = ast_node
        self._ast_node_type = ast_node_type
        self._in_edges = []
        self._out_edges = []

    @multimethod
    def __init__(self, ast_node: Optional[AdaNode], ast_node_type: int, key: Optional[str]):
        self._control = None
        self._data_type = None
        self._ast_node = ast_node
        self._ast_node_type = ast_node_type
        self._in_edges = []
        self._out_edges = []
        self._key = key

    def get_data_type(self) -> Optional[str]:
        return self._data_type

    def get_data_name(self) -> Optional[str]:
        if isinstance(self, PDGDataNode):
            return self.get_data_name()
        return None

    @abc.abstractmethod
    def get_label(self) -> str:
        warn('abstract method')
        return ''

    @abc.abstractmethod
    def get_exas_label(self) -> str:
        warn('abstract method')
        return ''

    def get_ast_node_type(self) -> int:
        warnings.warn('AST NODE TYPE SHOULD BE AdaNode Type not int')
        return self._ast_node_type

    def set_ast_node_type(self, ast_node_type: int):
        self._ast_node_type = ast_node_type

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

    def get_key(self) -> Optional[str]:
        return self._key

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
        edge: PDGControlEdge = cast(PDGControlEdge, self.get_in_edge(self._control))
        self._control._out_edges.remove(edge)
        edge._source = empty._control
        empty._control._out_edges.insert(index, edge)
        edge._label = empty.get_in_edge(empty._control).get_label()
        self._control = empty._control

    def get_in_edge(self, node: PDGNode) -> Optional[PDGEdge]:
        for edge in self._in_edges:
            if edge.get_source() == node:
                return edge
        return None

    def adjust_control(self, node: PDGNode, empty: PDGNode):
        i: int = 0
        while self._out_edges[i].get_target() != node:
            i += 1
        out_edge_index: int = empty._control.get_out_edge_index(empty)
        while i < len(self._out_edges) and not self._out_edges[i].get_target().is_empty_node():
            out_edge_index += 1
            self._out_edges[i].get_target().__adjust_control(empty, out_edge_index)

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
        warn('PDGNode is_same should be implemented differently?')
        if self._key is None and node._key is not None:
            return False
        if self._key != node._key:
            return False
        if isinstance(self, PDGActionNode):
            raise NotImplementedError
        if isinstance(self, PDGDataNode):
            raise NotImplementedError
        if isinstance(self, PDGControlNode):
            raise NotImplementedError
        return False

    def get_definition(self) -> Optional[PDGNode]:
        if isinstance(self, PDGDataNode) and len (self._in_edges) == 1 and isinstance(self._in_edges[0], PDGDataEdge):
            edge: PDGDataEdge = cast(PDGDataEdge, self._in_edges[0])
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
    _parameter_types: Optional[list[str]]
    _exception_types: list[object]
    __control_edge: PDGControlEdge

    @multimethod
    def __init__(self, control: PDGNode, branch: str, ast_node: Optional[AdaNode], node_type: int, key: Optional[str], type: Optional[str], name: Optional[str]):
        super().__init__(ast_node, node_type, key)
        self._parameter_types = None
        if control is not None:
            self._control = control
            self.__control_edge = PDGControlEdge(control, self, branch)
        self._data_type = type
        self._name = name

    @multimethod
    def __init__(self, control: PDGNode, branch: str, ast_node: Optional[AdaNode], node_type: int, key: Optional[str], type: Optional[str], name: Optional[str], exception_types: list[object]):
        self.__init__(control, branch, ast_node, node_type, key, type, name)
        self._exception_types = exception_types

    @override
    def get_label(self) -> str:
        return self._name + '' if self._parameter_types is None else self.__build_parameters()

    @override
    def get_exas_label(self) -> str:
        i: int = self._name.rfind('.') + 1
        return self._name[i:]

    def __build_parameters(self) -> str:
        return '({})'.format(','.join(self._parameter_types))

    @override
    def is_same(self, node: PDGNode) -> bool:
        if isinstance(node, PDGActionNode):
            return self._name == node._name
        return False

    @override
    def is_definition(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.get_label()

    def has_backward_data_dependence(self, pre_node: PDGActionNode) -> bool:
        definitions: set[PDGNode] = set()
        pre_definitions: set[PDGNode] = set()
        fields: set[str] = set()
        pre_fields: set[str] = set()
        self.get_definitions2(definitions, fields)
        pre_node.get_definitions2(pre_definitions, pre_fields)
        return overlap(definitions, pre_definitions) or overlap(fields, pre_fields)

    def get_definitions2(self, definitions: set[PDGNode], fields: set[str]):
        for e in self._in_edges:
            if isinstance(e.get_source(), PDGDataNode):
                temporary_definitions: list[PDGNode] = e.get_source().get_definitions()
                if len(temporary_definitions) == 0:
                    fields.add(e.get_source()._key)
                else:
                    definitions.update(temporary_definitions)


class PDGBuildingContext:

    method: Optional[SubpBody] = None
    source_file_path: str
    interprocedural: bool

    stack_trys: deque[set[PDGActionNode]]
    local_variables: deque[dict[str, str]]
    local_variable_types: deque[dict[str, str]]
    field_types: dict[str, str]

    def __init__(self, repository, commit, source_file_path, interprocedural: bool):
        self.stack_trys = deque()
        self.local_variables = deque()
        self.local_variable_types = deque()
        self.field_types = dict()
        self.repository = repository
        self.rev_commit = commit
        self.source_file_path = source_file_path
        self.inter_procedural = interprocedural

    def set_method(self, method: SubpBody, build_field_type: bool):
        self.method = method
        if build_field_type:
            raise NotImplementedError('Method seems specific to Java..')

    def build_field_types(self):
        raise NotImplementedError

    def add_method_try(self, node: PDGActionNode):
        raise NotImplementedError('No usage.')

    def push_try(self):
        self.stack_trys.append(set())

    def pop_try(self) -> set[PDGActionNode]:
        return self.stack_trys.pop()

    def get_trys(self):
        raise NotImplementedError('No usage.')

    def is_sub_type(self) -> bool:
        raise NotImplementedError('Usage in get_trys')

    def add_method_trys(self, nodes: set[PDGActionNode]):
        raise NotImplementedError('No usage.')

    def get_key(self):
        raise NotImplementedError

    def get_local_variable_info(self, identifier: str) -> Optional[list[str]]:
        for i in reversed(range(0, len(self.local_variables))):
            variables: dict[str, str] = self.local_variables[i]
            if identifier in variables:
                return [variables[identifier], self.local_variable_types[i][identifier]]
        return None

    def add_scope(self):
        self.local_variables.append(dict())
        self.local_variable_types.append(dict())

    def remove_scope(self):
        self.local_variables.pop()
        self.local_variable_types.pop()

    def add_local_variable(self, identifier: str, key: str, type: str):
        self.local_variables[0][identifier] = key
        self.local_variable_types[0][identifier] = type

    def get_field_type(self, name: str):
        type: str = self.field_types.get(name, None)
        if type is None:
            type = self.field_types.get(name, None)
        return type

    def build_super_field_types(self):
        raise NotImplementedError('No usage.')

    def get_super_type_path(self, super_type: str) -> str:
        raise NotImplementedError('No usage.')


class PDGControlEdge(PDGEdge):
    _label: str

    def __init__(self, point: PDGNode, next_node: PDGNode, label: str):
        super().__init__(point, next_node)
        self._label = label
        self._source.add_out_edge(self)
        self._target.add_in_edge(self)

    @override
    def get_label(self) -> str:
        return self._label

    @override
    def get_exas_label(self) -> str:
        return '_control_'

    def __str__(self) -> str:
        return self.get_label()


class PDGControlNode(PDGNode):
    __control_edge: PDGControlEdge

    def __init__(self, control: PDGNode, branch: str, ast_node: AdaNode, node_type: int):
        super().__init__(ast_node, node_type)
        self._control = control
        self.__control_edge = PDGControlEdge(control, self, branch)

    @override
    def get_label(self) -> str:
        return self.get_ast_node().kind_name

    @override
    def get_exas_label(self) -> str:
        return self.get_ast_node().kind_name

    @staticmethod
    @override
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

    @override
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

    @override
    def get_label(self) -> str:
        match self._type:
            case Type.RECEIVER:
                return 'recv'
            case Type.PARAMETER:
                return 'para'
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

    @override
    def get_exas_label(self) -> str:
        match self._type:
            case Type.RECEIVER:
                return '_recv_'
            case Type.PARAMETER:
                return '_para_'
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
    def __init__(self, ast_node: Optional[AdaNode], node_type: int, key: str, data_type: Optional[str], data_name: str):
        super().__init__(ast_node, node_type, key)
        self._data_type = data_type
        self._data_name = data_name

    @multimethod
    def __init__(self, ast_node: Optional[AdaNode], node_type: int, key: str, data_type: Optional[str], data_name: str, is_field: bool, is_declaration: bool):
        super().__init__(ast_node, node_type, key)
        self._data_type = data_type
        self._data_name = data_name
        self._is_field = is_field
        self._is_declaration = is_declaration

    @multimethod
    def __init__(self, node: PDGDataNode):
        self.__init__(node.get_ast_node(),
                      node.get_ast_node_type(),
                      node._key,
                      node._data_type,
                      node._data_name,
                      node._is_field,
                      node._is_declaration)

    @override
    def get_data_name(self) -> str:
        return self._data_name

    @override
    def get_label(self) -> str:
        if self._ast_node_type == node_type(CharLiteral) or self._ast_node_type == node_type(StringLiteral):
            return str(self._data_type) + '(lit(' + self._data_name + '))'
        return str(self._data_type) + '(' + self._data_name + ')'

    @override
    def get_exas_label(self) -> str:
        if self._ast_node.is_a(NullLiteral):
            return 'Null'
        elif self._ast_node.is_a(CharLiteral):
            return 'Character'
        elif self._ast_node.is_a(StringLiteral):
            return 'String'
        elif self._ast_node.is_a(IntLiteral):
            return 'Integer'
        elif self._ast_node.is_a(RealLiteral):
            return 'Real'
        elif self._ast_node.is_a(Identifier):
            if self._ast_node.text == 'True' or self._ast_node.text == 'False':
                return 'Boolean'
        elif self._ast_node is None:
            return 'UNKNOWN'
        return self._data_type

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
        return self._key.startswith(self.PREFIX_DUMMY)

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

    @multimethod
    def __init__(self, ast_node: Optional[AdaNode], ast_node_type: int, label: str):
        super().__init__(ast_node, ast_node_type)
        self.__label = label

    @override
    def get_label(self) -> str:
        return self.__label

    @override
    def get_exas_label(self) -> str:
        return self.__label

    @override
    def is_definition(self) -> bool:
        return False

    @override
    def __str__(self) -> str:
        return self.get_label()


class PDGGraph:
    __context: PDGBuildingContext
    __definition_store: dict[str, set[PDGDataNode]]
    _entry_node: PDGNode
    _end_node: PDGNode
    _parameters: list[PDGDataNode]
    _nodes: set[PDGNode]
    _statement_nodes: set[PDGNode]
    _data_sources: set[PDGDataNode]
    _statement_sources: set[PDGNode]
    _sinks: set[PDGNode]
    _statement_sinks: set[PDGNode]
    _breaks: set[PDGNode]
    _returns: set[PDGNode]
    _changed_nodes: set[PDGNode]

    __exas_vector: dict[ExasFeature, int]

    @multimethod
    def __init__(self, method_declaration: SubpBody, context: Optional[PDGBuildingContext]):
        self.__init__(context)
        self.__context.add_scope()
        self.__context.set_method(method_declaration, False)
        self._entry_node = PDGEntryNode(method_declaration,
                                        node_type(method_declaration),
                                        'START')
        self._nodes.add(self._entry_node)
        self._statement_nodes.add(self._entry_node)
        self._parameters = []
        for parameter in method_declaration.f_subp_spec.p_params or []:
            if len(parameter.p_defining_names) == 1:
                for name in parameter.p_defining_names:
                    id: str = name.f_name.text
                    self.merge_sequential(self.build_pdg(self._entry_node, '', parameter))
                    info: list[str] = self.__context.get_local_variable_info(id)
                    self._parameters.append(PDGDataNode(
                        name,
                        node_type(name),
                        info[0],
                        info[1],
                        'PARAM_{}'.format(id),
                        False,
                        True
                    ))
            else:
                raise NotImplementedError('multiple parameters in single ParamSpec')
        self.__context.push_try()
        if method_declaration.f_decls and method_declaration.f_decls.f_decls:
            declarations: AdaNodeList = method_declaration.f_decls.f_decls
            self.merge_sequential(self.build_pdg(self._entry_node, '', declarations))
        if method_declaration.f_stmts:
            if method_declaration.f_stmts.f_stmts:
                statements: StmtList = method_declaration.f_stmts.f_stmts
                self.merge_sequential(self.build_pdg(self._entry_node, '', statements))
        if not self.__context.inter_procedural:
            self._statement_sinks.update(self.__context.pop_try())
        self.adjust_return_nodes()
        self.adjust_control_edges()
        self.__context.remove_scope()

    @multimethod
    def __init__(self, context: Optional[PDGBuildingContext]):
        self.__context = context
        self._nodes = set()
        self._statement_nodes = set()
        self._data_sources = set()
        self._statement_sources = set()
        self._sinks = set()
        self._statement_sinks = set()
        self._breaks = set()
        self._returns = set()
        self._changed_nodes = set()
        self.__definition_store = {}
        self.__exas_vector = {}

    @multimethod
    def __init__(self, context: Optional[PDGBuildingContext], node: PDGNode):
        self.__init__(context)
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

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: AdaNode) -> PDGGraph:
        raise NotImplementedError(node)
        # return PDGGraph(self.__context)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node_list: AdaNodeList) -> PDGGraph:
        # TODO: test this and double check with original CPatMiner!!!
        nodes = iter(node_list)
        if len(node_list):
            graph: PDGGraph = self.build_pdg(control, branch, next(nodes))
            for node in nodes:
                graph.merge_sequential(self.build_pdg(control, branch, node))
            return graph
        return PDGGraph(self.__context)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, nodes: list[AdaNode]) -> PDGGraph:
        graphs: list[PDGGraph] = []
        for node in nodes:
            if isinstance(node, NullStmt):
                continue
            graph: PDGGraph = self.build_pdg(control, branch, node)
            if not graph.is_empty():
                graphs.append(graph)
        s: int = 0
        for i in range(1, len(graphs)):
            if graphs[s]._statement_nodes:
                graphs[s].merge_sequential(graphs[i])
            else:
                s = i
        if s == len(graphs):
            return PDGGraph(self.__context)
        return graphs[s]

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: Aggregate) -> PDGGraph:
        if node.f_ancestor_expr:
            raise NotImplementedError(node.f_ancestor_expr)
        graphs: list[PDGGraph] = []
        for assoc in node.f_assocs:
            graphs.append(self.build_argument_pdg(control, branch, assoc))
        action_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            node,
            node_type(node),
            None,
            'Aggregate',
            'Aggregate'
        )
        if graphs:
            for graph in graphs:
                graph.merge_sequential_data(action_node, Type.PARAMETER)
            graph: PDGGraph = PDGGraph(self.__context)
            graph.merge_parallel(graphs)
            return graph
        else:
            return PDGGraph(self.__context, action_node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, nodes: AlternativesList) -> PDGGraph:
        if len(nodes) == 1:
            return self.build_pdg(control, branch, nodes[0])
        graphs: list[PDGGraph] = []
        for node in nodes:
            graphs.append(self.build_pdg(control, branch, node))
        alternatives_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            nodes,
            node_type(nodes),
            None,
            None,
            'Alternatives'
        )
        for graph in graphs:
            graph.merge_sequential_data(alternatives_node, Type.PARAMETER)
        graph: PDGGraph = PDGGraph(self.__context)
        graph.merge_parallel(graphs)
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: AggregateAssoc) -> PDGGraph:
        graph: PDGGraph = PDGGraph(self.__context)
        designators_graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_designators)
        expr_graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_r_expr)
        assoc_node: PDGActionNode = PDGActionNode(control, branch, node, node_type(node), None, None, '=>')
        designators_graph.merge_sequential_data(assoc_node, Type.PARAMETER)
        expr_graph.merge_sequential_data(assoc_node, Type.PARAMETER)
        graph.merge_parallel([designators_graph, expr_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: AttributeRef) -> PDGGraph:

        if len(node.f_args):
            raise NotImplementedError('Arguments in AttributeRef??')

        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_prefix)

        if hasattr(node.f_attribute, 'p_fully_qualified_name'):
            print('YES!')

        action_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            node,
            node_type(node),
            None,
            '',  # TODO!
            node.f_attribute.text
        )
        graph.merge_sequential_data(action_node, Type.RECEIVER)
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: BracketAggregate) -> PDGGraph:
        if node.f_ancestor_expr:
            raise NotImplementedError(node.f_ancestor_expr)
        graphs: list[PDGGraph] = []
        for assoc in node.f_assocs:
            graphs.append(self.build_argument_pdg(control, branch, assoc))
        action_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            node,
            node_type(node),
            None,
            'Bracket Aggregate',
            'Bracket Aggregate'
        )
        if graphs:
            for graph in graphs:
                graph.merge_sequential_data(action_node, Type.PARAMETER)
            graph: PDGGraph = PDGGraph(self.__context)
            graph.merge_parallel(graphs)
            return graph
        else:
            return PDGGraph(self.__context, action_node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: AssignStmt) -> PDGGraph:
        if not isinstance(node.f_dest, Name):
            raise NotImplementedError
        dest_graph: PDGGraph = self.build_pdg(control, branch, node.f_dest)
        dest_node: PDGDataNode = dest_graph.get_only_data_out()
        graph: PDGGraph = self.build_pdg(control, branch, node.f_expr)
        returns: list[PDGActionNode] = graph.get_returns()
        if returns:
            for ret in returns:
                ret._ast_node_type = node_type(node)
                ret._name = ':='
                graph.extend(ret, PDGDataNode(dest_node), Type.DEFINITION)
            graph.get_nodes().update(dest_graph.get_nodes())
            graph._statement_nodes.update(dest_graph._statement_nodes)
            dest_graph._data_sources.remove(dest_node)
            graph._data_sources.update(dest_graph._data_sources)
            graph._statement_sources.update(dest_graph._statement_sources)
            dest_graph.clear()
            return graph
        definitions: list[PDGDataNode] = graph.get_definitions()
        if not definitions:
            graph.merge_sequential_data(
                PDGActionNode(
                    control,
                    branch,
                    node,
                    node_type(AssignStmt),
                    None,
                    None,
                    ':='
                ),
                Type.PARAMETER
            )
            graph.merge_sequential_data(dest_node, Type.DEFINITION)
        else:
            if definitions[0].is_dummy():
                for definition in definitions:
                    del graph.__definition_store[definition.get_key()]
                    definition.copy_data(dest_node)
                    ns: Optional[set[PDGDataNode]] = graph.__definition_store.get(definition.get_key(), None)
                    if ns is None:
                        ns = set()
                        graph.__definition_store[definition.get_key()] = ns
                    ns.add(definition)
            else:
                definition: PDGDataNode = definitions[0]
                graph.merge_sequential_data(
                    PDGDataNode(
                        None,
                        definition.get_ast_node_type(),
                        definition.get_key(),
                        definition.get_data_type(),
                        definition.get_data_name()
                    ),
                    Type.REFERENCE
                )
                graph.merge_sequential_data(
                    PDGActionNode(
                        control,
                        branch,
                        node,
                        node_type(AssignStmt),
                        None,
                        None,
                        ':='
                    ),
                    Type.PARAMETER
                )
                graph.merge_sequential_data(dest_node, Type.DEFINITION)
        graph.get_nodes().update(dest_graph.get_nodes())
        graph._statement_nodes.update(dest_graph._statement_nodes)
        dest_graph._data_sources.remove(dest_node)
        graph._data_sources.update(dest_graph._data_sources)
        graph._statement_sources.update(dest_graph._statement_sources)
        dest_graph.clear()
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: BinOp) -> PDGGraph:
        graph: PDGGraph = PDGGraph(self.__context)
        left_graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_left)
        right_graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_right)
        action_node: PDGActionNode = PDGActionNode(control, branch, node, node_type(node), None, None, node.f_op.text)
        left_graph.merge_sequential_data(action_node, Type.PARAMETER)
        right_graph.merge_sequential_data(action_node, Type.PARAMETER)
        graph.merge_parallel([left_graph, right_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: CallExpr) -> PDGGraph:
        graphs: list[PDGGraph] = []

        # TODO: this doesn't work properly for things other than node.f_name == Identifier, such as AttributeRef...
        action_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            node,
            node_type(node),
            None,
            '',  # TODO
            node.f_name.text
        )
        if hasattr(node.f_name, 'doc_name'):
            names: list[str] = node.f_name.doc_name.split('.')
            data_type: str = '.'.join(names[:-1])
            data_name: str = names[-2]
            graphs.append(PDGGraph(
                self.__context,
                PDGDataNode(
                    None, node_type(DottedName), node.f_name.doc_name, data_type, data_name
                )
            ))
        else:
            # TODO: graphs[0] should be something like package origin? "Printing." "this" does NOT make sense in Ada
            graphs.append(PDGGraph(
                self.__context,
                PDGDataNode(
                    None, node_type(DottedName), 'this', 'this', 'this'
                )
            ))

        match node.f_suffix:
            case AssocList():
                assoc_list: AssocList = cast(AssocList, node.f_suffix)
                for argument in assoc_list:
                    graphs.append(self.build_argument_pdg(control, branch, argument))
            case None:
                pass
            case _:
                raise NotImplementedError(node.f_suffix.__class__)

        graph: Optional[PDGGraph] = None
        graphs[0].merge_sequential_data(action_node, Type.RECEIVER)
        if graphs:
            for i in range(1, len(graphs)):
                graphs[i].merge_sequential_data(action_node, Type.PARAMETER)
            graph = PDGGraph(self.__context)
            graph.merge_parallel(graphs)
        else:
            graph = PDGGraph(self.__context, action_node)
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: CallStmt) -> PDGGraph:
        return self.build_pdg(control, branch, node.f_call)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: CaseExpr) -> PDGGraph:
        raise NotImplementedError(node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: CaseStmt):
        raise NotImplementedError(node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ConcatOp) -> PDGGraph:
        graph: PDGGraph = PDGGraph(self.__context)
        first_operand_graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_first_operand)
        operands_iter = iter(node.f_other_operands)
        second_operand: ConcatOperand = next(operands_iter)
        second_operand_graph: PDGGraph = self.build_argument_pdg(control, branch, second_operand.f_operand)
        action_node: PDGActionNode = PDGActionNode(control,
                                                   branch,
                                                   node,
                                                   node_type(node),
                                                   None,
                                                   None,
                                                   second_operand.f_operator.text)
        first_operand_graph.merge_sequential_data(action_node, Type.PARAMETER)
        second_operand_graph.merge_sequential_data(action_node, Type.PARAMETER)
        graph.merge_parallel([first_operand_graph, second_operand_graph])
        for operand_node in operands_iter:
            operand_graph: PDGGraph = self.build_argument_pdg(control, branch, operand_node.f_operand)
            operand_graph.merge_sequential_data(action_node, Type.PARAMETER)
            graph.merge_parallel([operand_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: CharLiteral) -> PDGGraph:
        return PDGGraph(self.__context,
                        PDGDataNode(
                            node,
                            node_type(node),
                            node.text,
                            'Character',
                            node.text
                        ))

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: DeclarativePart):
        return self.build_pdg(control, branch, node.f_decls)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: DeclBlock):
        self.__context.add_scope()
        graph: PDGGraph = self.build_pdg(control, branch, node.f_decls)
        graph.merge_sequential(self.build_pdg(control, branch, node.f_stmts))
        self.__context.remove_scope()
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: DeclExpr) -> PDGGraph:
        raise NotImplementedError

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: DottedName) -> PDGGraph:
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_prefix)
        data_node: PDGDataNode = graph.get_only_data_out()
        if data_node.get_data_type().startswith('UNKNOWN'):
            name: str = node.f_suffix.text
            #  Uppercase check??
            return PDGGraph(
                self.__context,
                PDGDataNode(
                    node, node_type(node), node.text, node.text, node.f_suffix.text, True, False)
                )
        else:
            graph.merge_sequential_data(
                PDGDataNode(
                    node,
                    node_type(node),
                    node.text,
                    '{}.{}'.format(data_node.get_data_type(), node.f_suffix.text),
                    node.f_suffix.text,
                    True,
                    False
                ),
                Type.QUALIFIER
            )
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ExitStmt) -> PDGGraph:
        action_node: PDGActionNode = PDGActionNode(
            control,
            branch,
            node,
            node_type(node),
            node.f_loop_name.text if node.f_loop_name else '',
            None,
            'Exit'
        )
        if node.f_cond_expr:
            raise NotImplementedError('Conditional Exit not supported!')
        graph: PDGGraph = PDGGraph(self.__context, action_node)
        graph._breaks.add(action_node)
        graph._sinks.remove(action_node)
        graph._statement_sinks.remove(action_node)
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ExtendedReturnStmt) -> PDGGraph:
        self.__context.add_scope()
        graph: PDGGraph = self.build_pdg(control, branch, node.f_decl)
        statements_graph: PDGGraph = self.build_pdg(control, branch, node.f_stmts)
        if not statements_graph.is_empty():
            graph.merge_sequential(statements_graph)

        return_node: PDGActionNode = PDGActionNode(
            control, branch, node, node_type(node), None, None, 'return'
        )
        name: Identifier = node.f_decl.f_ids[0].f_name
        name_graph: PDGGraph = self.build_argument_pdg(control, branch, name)
        name_graph.merge_sequential_data(return_node, Type.PARAMETER)
        graph.merge_sequential(name_graph)
        graph._returns.add(return_node)
        graph._sinks.clear()
        graph._statement_sinks.clear()
        self.__context.remove_scope()
        return graph

    # @multimethod
    # def build_pdg(self, control: PDGNode, branch: str, node: ExtendedReturnStmtObjectDecl) -> PDGGraph:
    #     pass

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ForLoopSpec) -> PDGGraph:
        var_decl_node: PDGDataNode = self.build_pdg_data_node(control, branch, node.f_var_decl)
        if isinstance(node.f_has_reverse, ReversePresent):
            raise NotImplementedError(ReversePresent)
        if node.f_iter_filter:
            raise NotImplementedError(node.f_iter_filter)
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_iter_expr)
        graph.merge_sequential_data(
            PDGActionNode(
                control,
                branch,
                node,
                node_type(AssignStmt),
                None,
                None,
                ':='
            ),
            Type.PARAMETER
        )
        graph.merge_sequential_data(var_decl_node, Type.DEFINITION)
        graph.merge_sequential_data(
            PDGDataNode(
                None,
                var_decl_node.get_ast_node_type(),
                var_decl_node.get_key(),
                var_decl_node.get_data_type(),
                var_decl_node.get_data_name()
            ),
            Type.REFERENCE
        )
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ForLoopStmt) -> PDGGraph:
        self.__context.add_scope()
        graph: PDGGraph = self.build_pdg(control, branch, node.f_spec)
        control_node: PDGControlNode = PDGControlNode(control, branch, node, node_type(node))
        graph.merge_sequential_data(control_node, Type.CONDITION)
        graph.merge_sequential_control(
            PDGActionNode(
                control_node,
                '',
                None,
                node_type(NullStmt),
                None,
                None,
                'empty',
            ),
            ''
        )
        statements_graph: PDGGraph = self.build_pdg(control, branch, node.f_stmts)
        if not statements_graph.is_empty():
            graph.merge_sequential(statements_graph)
        graph.adjust_break_nodes('')
        self.__context.remove_scope()
        return graph

    @multimethod
    def build_pdg_data_node(self, control: PDGNode, branch: str, node: ForLoopVarDecl) -> PDGDataNode:
        if node.f_aspects:
            NotImplementedError(node.f_aspects)
        name: Identifier = node.f_id.f_name
        self.__context.add_local_variable(name.text, str(start_position(name)), '')  # TODO?: type
        return PDGDataNode(
            name,
            node_type(name),
            str(start_position(name)),
            '',  # TODO?: type
            name.text,
            False,
            True
        )


    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: HandledStmts):
        return self.build_pdg(control, branch, node.f_stmts)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: Identifier):
        name: str = node.text

        if name.lower() == 'true' or name.lower() == 'false':
            return PDGGraph(
                self.__context,
                PDGDataNode(
                    node,
                    node_type(node),
                    name,
                    'Boolean',
                    name
                )
            )

        info: list[str] = self.__context.get_local_variable_info(name)
        if node.p_is_call:
            graph: PDGGraph
            if hasattr(node, 'doc_name'):
                names: list[str] = node.doc_name.split('.')
                data_type: str = '.'.join(names[:-1])
                data_name: str = names[-2]
                graph = PDGGraph(
                    self.__context,
                    PDGDataNode(
                        None, node_type(DottedName), node.doc_name, data_type, data_name
                    )
                )
            else:
                # TODO: fix this "this" doesn't make sense in Ada!!
                graph = PDGGraph(
                    self.__context,
                    PDGDataNode(
                        None, node_type(DottedName), 'this', 'this', 'this'
                    )
                )
            action_node: PDGActionNode = PDGActionNode(
                    control,
                    branch,
                    node,
                    node_type(node),
                    None,
                    '',  # TODO! type string, same as CallExpr!
                    node.text
                )
            graph.merge_sequential_data(action_node, Type.QUALIFIER)
            return graph
        if info:
            graph: PDGGraph = PDGGraph(
                self.__context,
                PDGDataNode(node, node_type(node), info[0], info[1], name, False, False)
            )
            return graph
        if node.p_expression_type:
            type: str = node.p_expression_type.f_name.text
            return PDGGraph(
                self.__context,
                PDGDataNode(node, node_type(node), str(start_position(node.p_expression_type)), type, name, False, False)
            )
        print(node.p_expression_type)
        raise NotImplementedError(node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, nodes: list[ElsifExprPart], else_expr: Expr):
        node: ElsifExprPart = nodes[0]
        remaining_nodes: list[ElsifExprPart] = nodes[1:]
        dummy_node: PDGDataNode = PDGDataNode(
            None,
            node_type(Identifier),
            PDGNode.PREFIX_DUMMY + str(start_position(node)) + '_' + str(start_position(node) + len(node.text)),
            'Boolean',
            PDGNode.PREFIX_DUMMY,
            False,
            True
        )
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_cond_expr)
        control_node: PDGControlNode = PDGControlNode(
            control, branch, node, node_type(node)
        )
        graph.merge_sequential_data(control_node, Type.CONDITION)
        then_graph: PDGGraph = self.build_argument_pdg(control_node, 'T', node.f_then_expr)
        then_graph.merge_sequential_data(
            PDGActionNode(control_node, 'T', None, node_type(AssignStmt), None, None, ':='),
            Type.PARAMETER
        )
        then_graph.merge_sequential_data(PDGDataNode(dummy_node), Type.DEFINITION)

        if remaining_nodes:
            alternatives_graph: PDGGraph = self.build_pdg(control_node, 'F', remaining_nodes, else_expr)
            graph.merge_branches([then_graph, alternatives_graph])
        else:
            else_graph: PDGGraph = self.build_argument_pdg(control_node, 'F', else_expr)
            else_graph.merge_sequential_data(
                PDGActionNode(control_node, 'F', None, node_type(AssignStmt), None, None, ':='),
                Type.PARAMETER
            )
            else_graph.merge_sequential_data(PDGDataNode(dummy_node), Type.DEFINITION)
            graph.merge_branches([then_graph, else_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: IfExpr) -> PDGGraph:
        dummy_node: PDGDataNode = PDGDataNode(
            None,
            node_type(Identifier),
            PDGNode.PREFIX_DUMMY + str(start_position(node)) + '_' + str(start_position(node) + len(node.text)),
            'Boolean',
            PDGNode.PREFIX_DUMMY,
            False,
            True
        )
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_cond_expr)
        control_node: PDGControlNode = PDGControlNode(
            control, branch, node, node_type(node)
        )
        graph.merge_sequential_data(control_node, Type.CONDITION)
        then_graph: PDGGraph = self.build_argument_pdg(control_node, 'T', node.f_then_expr)
        then_graph.merge_sequential_data(
            PDGActionNode(control_node, 'T', None, node_type(AssignStmt), None, None, ':='),
            Type.PARAMETER
        )
        then_graph.merge_sequential_data(PDGDataNode(dummy_node), Type.DEFINITION)

        if len(node.f_alternatives):
            alternatives_graph: PDGGraph = self.build_pdg(control_node, 'F', list(node.f_alternatives), node.f_else_expr)
            graph.merge_branches([then_graph, alternatives_graph])
        else:
            else_graph: PDGGraph = self.build_argument_pdg(control_node, 'F', node.f_else_expr)
            else_graph.merge_sequential_data(
                PDGActionNode(control_node, 'F', None, node_type(AssignStmt), None, None, ':='),
                Type.PARAMETER
            )
            else_graph.merge_sequential_data(PDGDataNode(dummy_node), Type.DEFINITION)
            graph.merge_branches([then_graph, else_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, nodes: list[ElsifStmtPart], else_stmts: StmtList) -> PDGGraph:
        node: ElsifStmtPart = nodes[0]
        remaining_nodes: list[ElsifStmtPart] = nodes[1:]
        graph: PDGGraph = self.build_pdg(control, branch, node.f_cond_expr)
        control_node: PDGControlNode = PDGControlNode(control, branch, node, node_type(node))
        graph.merge_sequential_data(control_node, Type.CONDITION)
        empty_then_graph: PDGGraph = PDGGraph(
            self.__context,
            PDGActionNode(
                control_node,
                'T',
                None,
                node_type(NullStmt),
                None,
                None,
                'empty'
            )
        )
        then_graph: PDGGraph = self.build_pdg(control_node, 'T', node.f_stmts)
        if not then_graph.is_empty():
            empty_then_graph.merge_sequential(then_graph)
        empty_else_graph: PDGGraph = PDGGraph(
            self.__context,
            PDGActionNode(
                control_node,
                'F',
                None,
                node_type(NullStmt),
                None,
                None,
                'empty'
            )
        )
        if remaining_nodes:
            alternatives_graph: PDGGraph = self.build_pdg(control_node, 'F', remaining_nodes, else_stmts)
            if not alternatives_graph.is_empty():
                empty_else_graph.merge_sequential(alternatives_graph)
        elif else_stmts:
            else_graph: PDGGraph = self.build_pdg(control_node, 'F', else_stmts)
            if not else_graph.is_empty():
                empty_else_graph.merge_sequential(else_graph)
        graph.merge_branches([empty_then_graph, empty_else_graph])
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: IfStmt) -> PDGGraph:
        self.__context.add_scope()
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_cond_expr)
        control_node: PDGControlNode = PDGControlNode(control, branch, node, node_type(node))
        graph.merge_sequential_data(control_node, Type.CONDITION)
        empty_then_graph: PDGGraph = PDGGraph(
            self.__context,
            PDGActionNode(
                control_node,
                'T',
                None,
                node_type(NullStmt),
                None,
                None,
                'empty'
            )
        )
        then_graph: PDGGraph = self.build_pdg(control_node, 'T', node.f_then_stmts)
        if not then_graph.is_empty():
            empty_then_graph.merge_sequential(then_graph)
        empty_else_graph: PDGGraph = PDGGraph(
            self.__context,
            PDGActionNode(
                control_node,
                'F',
                None,
                node_type(NullStmt),
                None,
                None,
                'empty'
            )
        )

        if len(node.f_alternatives):
            alternatives_graph: PDGGraph = self.build_pdg(control_node, 'F',
                                                          list(node.f_alternatives), node.f_else_stmts)
            if not alternatives_graph.is_empty():
                empty_else_graph.merge_sequential(alternatives_graph)
        elif node.f_else_stmts:
            else_graph: PDGGraph = self.build_pdg(control_node, 'F', node.f_else_stmts)
            if not else_graph.is_empty():
                empty_else_graph.merge_sequential(else_graph)
        graph.merge_branches([empty_then_graph, empty_else_graph])
        self.__context.remove_scope()
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: IntLiteral) -> PDGGraph:
        return PDGGraph(
            self.__context,
            PDGDataNode(
                node,
                node_type(node),
                str(node.p_denoted_value),
                "Integer",
                str(node.p_denoted_value)
            )
        )

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: LoopStmt):
        self.__context.add_scope()
        self.__context.remove_scope()
        raise NotImplementedError

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: NullLiteral) -> PDGGraph:
        return PDGGraph(
            self.__context,
            PDGDataNode(
                node,
                node_type(node),
                node.text,
                'Null',
                node.text
            )
        )

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ObjectDecl) -> PDGGraph:
        # TODO: implement multiple declarations in single ObjectDecl!!!
        for defining_name in node.p_defining_names:
            name: Identifier = defining_name.f_name
            # TODO: getSimpleType
            type: str = node.f_type_expr.text
            self.__context.add_local_variable(name.text, str(start_position(name)), type)
            data_node: PDGDataNode = PDGDataNode(
                name,
                node_type(name),
                str(start_position(name)),
                type,
                name.text,
                False,
                True,
            )
            if node.f_default_expr is None:
                graph: PDGGraph = PDGGraph(self.__context, PDGDataNode(None, node_type(NullLiteral), 'Null', '', 'Null'))
                graph.merge_sequential_data(PDGActionNode(control, branch, node, node_type(AssignStmt), None, None, ':='), Type.PARAMETER)
                graph.merge_sequential_data(data_node, Type.DEFINITION)
                return graph
            graph: PDGGraph = self.build_pdg(control, branch, node.f_default_expr)
            returns: list[PDGActionNode] = graph.get_returns()
            if returns:
                for r in returns:
                    r.set_ast_node_type(node_type(AssignStmt))
                    r._name = ':='
                    graph.extend(r, PDGDataNode(data_node), Type.DEFINITION)
                return graph
            definitions: list[PDGDataNode] = graph.get_definitions()
            if not definitions:
                graph.merge_sequential_data(
                    PDGActionNode(
                        control,
                        branch,
                        node,
                        node_type(AssignStmt),
                        None,
                        None,
                        ':='
                    ),
                    Type.PARAMETER
                )
                graph.merge_sequential_data(data_node, Type.DEFINITION)
            elif definitions[0].is_dummy():
                for definition in definitions:
                    if definition.get_key() in self.__definition_store:
                        del self.__definition_store[definition.get_key()]
                    definition.copy_data(data_node)
                    ns: set[PDGDataNode] = self.__definition_store.get(definition._key, None)
                    if ns is None:
                        ns = set()
                        self.__definition_store[definition._key] = ns
                    ns.add(definition)
            else:
                definition: PDGDataNode = definitions[0]
                graph.merge_sequential_data(
                    PDGDataNode(definition.get_ast_node(),
                                definition.get_ast_node_type(),
                                definition._key,
                                definition._data_type,
                                definition.get_data_name(),
                                definition._is_field,
                                False),
                    Type.REFERENCE)
                graph.merge_sequential_data(PDGActionNode(control, branch, node, node_type(AssignStmt), None, None, ':='),
                                            Type.PARAMETER)
                graph.merge_sequential_data(data_node, Type.DEFINITION)
            return graph
        raise NotImplementedError

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: OthersDesignator) -> PDGGraph:
        return PDGGraph(
            self.__context,
            PDGDataNode(
                node,
                node_type(node),
                node.text,
                None,  # correct type?
                node.text
            )
        )

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ParamAssoc) -> PDGGraph:
        if node.f_designator:
            warn('WARNING: ParamAssoc f_designator is not implemented!')
        return self.build_pdg(control, branch, node.f_r_expr)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ParenExpr) -> PDGGraph:
        return self.build_pdg(control, branch, node.f_expr)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ParamSpec) -> PDGGraph:
        if len(node.f_ids) == 1:
            for name in node.f_ids:
                # TODO: get simple type?
                type: str = node.f_type_expr.text
                self.__context.add_local_variable(name.text, str(start_position(name)), type)
                data_node: PDGDataNode = PDGDataNode(
                    name,
                    node_type(name),
                    str(start_position(name)),
                    type,
                    name.text,
                    False,
                    True
                )
                graph: PDGGraph = PDGGraph(
                    self.__context,
                    PDGDataNode(
                        None,
                        node_type(NullLiteral),
                        'Null',
                        '',
                        'Null'
                    )
                )
                graph.merge_sequential_data(
                    PDGActionNode(
                        control,
                        branch,
                        node,
                        node_type(AssignStmt),
                        None,
                        None,
                        ':='
                    ),
                    Type.PARAMETER
                )
                graph.merge_sequential_data(data_node, Type.DEFINITION)
                return graph
        else:
            raise NotImplementedError(node)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: RealLiteral) -> PDGGraph:
        return PDGGraph(self.__context,
                        PDGDataNode(
                            node,
                            node_type(node),
                            node.text,
                            'Real',
                            node.text
                        ))

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: ReturnStmt) -> PDGGraph:
        graph: Optional[PDGGraph] = None
        action_node: Optional[PDGActionNode] = None
        if node.f_return_expr:
            graph = self.build_argument_pdg(control, branch, node.f_return_expr)
            action_node = PDGActionNode(
                control, branch, node, node_type(node), None, None, 'return'
            )
            graph.merge_sequential_data(action_node, Type.PARAMETER)
        else:
            action_node = PDGActionNode(
                control, branch, node, node_type(node), None, None, 'return'
            )
            graph = PDGGraph(self.__context, action_node)
        graph._returns.add(action_node)
        graph._sinks.clear()
        graph._statement_sinks.clear()
        return graph

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: StmtList) -> PDGGraph:
        if 0 < len(node.children) <= 100:
            self.__context.add_scope()
            graph: PDGGraph = self.build_pdg(control, branch, node.children)
            self.__context.remove_scope()
            return graph
        return PDGGraph(self.__context)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: StringLiteral) -> PDGGraph:
        return PDGGraph(self.__context,
                        PDGDataNode(node, node_type(node), node.text, 'String', node.p_eval_as_string))

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: UsePackageClause) -> PDGGraph:
        # TODO?
        return PDGGraph(self.__context)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: WhileLoopSpec):
        return self.build_pdg(control, branch, node.f_expr)

    @multimethod
    def build_pdg(self, control: PDGNode, branch: str, node: WhileLoopStmt):
        self.__context.add_scope()
        graph: PDGGraph = self.build_argument_pdg(control, branch, node.f_spec)
        control_node: PDGControlNode = PDGControlNode(control, branch, node, node_type(node))
        graph.merge_sequential_data(control_node, Type.CONDITION)
        ebg: PDGGraph = PDGGraph(self.__context,
                                 PDGActionNode(
                                     control_node,
                                     'T',
                                     None,
                                     node_type(NullStmt),
                                     None,
                                     None,
                                     'empty'
                                 ))
        bg: PDGGraph = self.build_pdg(control_node, 'T', node.f_stmts)
        if not bg.is_empty():
            ebg.merge_sequential(bg)
        eg: PDGGraph = PDGGraph(self.__context,
                                PDGActionNode(control_node,
                                              'F',
                                              None,
                                              node_type(NullStmt),
                                              None,
                                              None,
                                              'empty'))
        graph.merge_branches([ebg, eg])
        graph.adjust_break_nodes('')
        self.__context.remove_scope()
        return graph

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
                definitions: set[PDGDataNode] = self.__definition_store.get(source.get_key())
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
        self._nodes.discard(node)
        self._changed_nodes.discard(node)
        self._statement_nodes.discard(node)
        self._data_sources.discard(node)
        self._statement_sources.discard(node)
        self._sinks.discard(node)
        self._statement_sinks.discard(node)
        node.delete()

    def build_argument_pdg(self, control: PDGNode, branch: str, exp: AdaNode) -> PDGGraph:
        graph: PDGGraph = self.build_pdg(control, branch, exp)
        if graph.is_empty():
            return graph
        if len(graph.get_nodes()) == 1:
            for node in graph.get_nodes():
                if isinstance(node, PDGDataNode):
                    return graph
        definitions: list[PDGDataNode] = graph.get_definitions()
        if definitions:
            definition: PDGDataNode = definitions[0]
            graph.merge_sequential_data(PDGDataNode(None,
                                                    definition.get_ast_node_type(),
                                                    definition._key,
                                                    cast(PDGDataNode, definition).get_data_type(),
                                                    cast(PDGDataNode, definition).get_data_name(),
                                                    definition._is_field,
                                                    False),
                                        Type.REFERENCE)
        returns: list[PDGActionNode] = graph.get_returns()
        if returns:
            dummy: PDGDataNode = PDGDataNode(None,
                                             node_type(Identifier),
                                             PDGNode.PREFIX_DUMMY + str(start_position(exp)) + '_' + str(start_position(exp) + len(exp.text)),
                                             returns[0].get_data_type(),
                                             PDGNode.PREFIX_DUMMY, False, True)
            for ret in returns:
                ret.set_ast_node_type(node_type(AssignStmt))
                ret._name = ':='
                graph.extend(ret, PDGDataNode(dummy), Type.DEFINITION)
            graph.merge_sequential_data(PDGDataNode(None,
                                                    dummy.get_ast_node_type(),
                                                    dummy._key,
                                                    dummy.get_data_type(),
                                                    dummy.get_data_name()),
                                        Type.REFERENCE)
            return graph
        node: PDGNode = graph.get_only_out()
        if isinstance(node, PDGDataNode):
            return graph
        dummy: PDGDataNode = PDGDataNode(
            None,
            node_type(Identifier),
            PDGNode.PREFIX_DUMMY + str(start_position(exp)) + '_' + str(start_position(exp) + len(exp.text)),
            node.get_data_type(),
            PDGNode.PREFIX_DUMMY,
            False,
            True
        )
        graph.merge_sequential_data(PDGActionNode(control, branch, None, node_type(AssignStmt), None, None, ':='),
                                    Type.PARAMETER)
        graph.merge_sequential_data(dummy, Type.DEFINITION)
        graph.merge_sequential_data(PDGDataNode(None,
                                                dummy.get_ast_node_type(),
                                                dummy._key,
                                                dummy.get_data_type(),
                                                dummy.get_data_name()),
                                    Type.REFERENCE)
        return graph

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

    @multimethod
    def clear(self, d: dict[object, set[object]]):
        for key in d.keys():
            d[key].clear()
        d.clear()

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
            self.__definition_store[next.get_key()] = s
        elif type == Type.QUALIFIER:
            self._data_sources.add(cast(PDGDataNode, next))
        elif type != Type.REFERENCE and isinstance(next, PDGDataNode):
            s: set[PDGDataNode] = self.__definition_store.get(next.get_key(), None)
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
        self.__definition_store[node.get_key()] = s
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
            if (node.get_key() is None and id is None) or node.get_key() == id:
                self._sinks.add(node)
                self._statement_sinks.add(node)
                self._breaks.remove(node)

    def adjust_return_nodes(self):
        self._sinks.update(self._returns)
        self._statement_sinks.update(self._returns)
        self._returns.clear()
        self._end_node = PDGEntryNode(None, node_type(SubpBody), 'END')
        for sink in self._statement_sinks:
            PDGDataEdge(sink, self._end_node, Type.DEPENDENCE)
        self._sinks.clear()
        self._statement_sinks.clear()
        self._nodes.add(self._end_node)
        if self._entry_node in self._statement_nodes:
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
                            and not isinstance(edge.get_target().get_ast_node_type(), AssignStmt)):
                        branch_nodes.get(edge.get_label()).append(edge.get_target())
                for branch in branch_nodes.keys():
                    nodes: list[PDGNode] = branch_nodes.get(branch)
                    for i in range(0, len(nodes)):  # TODO: this could be implemented with slices
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

    @multimethod
    def build_change_graph(self, other: PDGGraph):
        m: dict[AdaNode, PDGNode] = {}
        for node in other.get_nodes():
            if node.get_ast_node() is not None:
                m[node.get_ast_node()] = node
        for node in self.get_nodes():
            ast_node: AdaNode = node.get_ast_node()
            if ast_node is not None:
                other_ast_node: AdaNode = TreedConstants.PROPERTY_MAP.get(ast_node, None)
                if other_ast_node is not None:
                    other_node: PDGNode = m.get(other_ast_node)
                    if other_node is not None:
                        PDGDataEdge(other_node, node, Type.MAP)
        self._nodes.update(other.get_nodes())
        self._changed_nodes.update(other.get_changed_nodes())

    @multimethod
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
                definition = PDGDataNode(None, node.get_ast_node_type(), node._key, node.get_data_type(), node.get_data_name(), True, True)
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
