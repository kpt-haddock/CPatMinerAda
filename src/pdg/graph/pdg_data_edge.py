import string
from enum import Enum
from pdg_node import PDGNode
from pdg_edge import PDGEdge


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
    def get_label(self) -> string:
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
    def get_exas_label(self) -> string:
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

    # override
    def to_string(self) -> string:
        return self.get_label()
