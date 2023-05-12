import subprocess
from typing import Optional

from graphviz import Digraph
from multimethod import multimethod

from src.change import ChangeNode, ChangeGraph
from src.pdg import PDGNode, PDGGraph, PDGEntryNode, PDGControlNode, PDGActionNode, PDGDataNode, PDGDataEdge, Type, \
    PDGControlEdge


class DotGraph:
    SHAPE_BOX: str = 'box'
    SHAPE_DIAMOND: str = 'diamond'
    SHAPE_ELLIPSE: str = 'ellipse'
    COLOR_BLACK: str = 'black'
    COLOR_RED: str = 'red'
    STYLE_ROUNDED: str = 'rounded'
    STYLE_DOTTED: str = 'dotted'
    DOT_PATH: str = 'C:/....path to dot.exe'
    
    __graph: str = ''
    dot: Digraph

    @multimethod
    def __init__(self, graph: str):
        self.__graph = graph

    @multimethod
    def __init__(self, change_graph: ChangeGraph):
        #  add nodes
        self.__graph += self.add_start()
        ids: dict[ChangeNode, int] = {}
        id: int = 0
        for node in change_graph.get_nodes():
            id += 1
            ids[node] = id
            color: Optional[str] = None
            shape: Optional[str] = None
            if node.get_type() == 'a':
                shape = DotGraph.SHAPE_BOX
            elif node.get_type() == 'c':
                shape = DotGraph.SHAPE_DIAMOND
            elif node.get_type() == 'd':
                shape = DotGraph.SHAPE_ELLIPSE
            self.__graph += self.add_node(id, node.get_label(), shape, None, color, color)

        #  add edges
        for node in change_graph.get_nodes():
            t_id: int = ids[node]
            for edge in node.get_in_edges():
                s_id: int = ids[edge.get_source()]
                label: str = edge.get_label()
                if label == 'T' or label == 'F':
                    self.__graph += self.add_edge(s_id, t_id, None, None, label)
                else:
                    self.__graph += self.add_edge(s_id, t_id, DotGraph.STYLE_DOTTED, None, label)
        
        self.__graph += self.add_end()

    @staticmethod
    def add_start() -> str:
        return 'digraph G {\n'

    @multimethod
    def __init__(self, pdg: PDGGraph, change_only: bool):
        self.dot = Digraph()

        ids: dict[PDGNode, int] = {}
        #  add nodes
        id: int = 0
        for node in pdg.get_nodes():
            if change_only and not pdg.is_changed_node(node):
                continue
            id += 1
            ids[node] = id
            color: Optional[str] = None
            if pdg.is_changed_node(node):
                color = DotGraph.COLOR_RED
            if isinstance(node, PDGEntryNode):
                self.dot.node(str(id), node.get_label(), style='dotted', shape=DotGraph.SHAPE_ELLIPSE)
            elif isinstance(node, PDGControlNode):
                self.dot.node(str(id), node.get_label(), shape=DotGraph.SHAPE_DIAMOND)
            elif isinstance(node, PDGActionNode):
                self.dot.node(str(id), node.get_label(), shape=DotGraph.SHAPE_BOX)
            elif isinstance(node, PDGDataNode):
                self.dot.node(str(id), node.get_label(), shape=DotGraph.SHAPE_ELLIPSE)

        #  add edges
        for node in pdg.get_nodes():
            if node not in ids:
                continue
            t_id: int = ids[node]
            number_of_edges: dict[str, int] = {}
            for edge in node.get_in_edges():
                if edge.get_source() not in ids:
                    continue
                s_id: int = ids[edge.get_source()]
                label: str = edge.get_label()
                if isinstance(edge, PDGDataEdge):
                    n: int = 1
                    if label in number_of_edges:
                        n += number_of_edges[label]
                    number_of_edges[label] = n
                    self.dot.edge(str(s_id), str(t_id), style=DotGraph.STYLE_DOTTED, label=label + (str(n) if edge.get_type() == Type.PARAMETER else ''))
                elif isinstance(edge, PDGControlEdge):
                    source: PDGNode = edge.get_source()
                    if isinstance(source, PDGEntryNode) or isinstance(source, PDGControlNode):
                        n: int = 0
                        for out in source.get_out_edges():
                            if out.get_label() == label:
                                n += 1
                            if out == edge:
                                break
                        self.dot.edge(str(s_id), str(t_id), label=label + str(n))
                    else:
                        self.dot.edge(str(s_id), str(t_id), label=label)
                else:
                    self.dot.edge(str(s_id), str(t_id), label=label)

    @staticmethod
    def add_node(id: int, label: str, shape: Optional[str], style: Optional[str],
                 border_color: Optional[str], font_color: Optional[str]) -> str:
        node: str = ''
        node += '{} [label="{}"'.format(id, label)
        if shape is not None and shape != '':
            node += ' shape={}'.format(shape)
        if style is not None and style != '':
            node += ' style={}'.format(style)
        if border_color is not None and border_color != '':
            node += ' color={}'.format(border_color)
        if font_color is not None and font_color != '':
            node += ' fontcolor={}'.format(font_color)
        node += ']\n'
        return node

    @staticmethod
    def add_edge(s_id: int, e_id: int, style: Optional[str], color: Optional[str], label: Optional[str]) -> str:
        edge: str = ''
        if label is None:
            label = ''
        edge += '{} -> {} [label="{}"'.format(s_id, e_id, label)
        if style is not None and style != '':
            edge += ' style={}'.format(style)
        if color is not None and color != '':
            edge += ' color={}'.format(color)
        edge += '];\n'
        return edge

    @staticmethod
    def add_end() -> str:
        return '}'

    def get_graph(self) -> str:
        return self.__graph

    def to_dot_file(self, file: str):
        with open(file, 'w') as f:
            f.write(self.__graph)

    def to_graphics(self, file: str, type: str):
        self.dot.render(view=True)
        # subprocess.call([self.DOT_PATH, '-T{}'.format(type), '{}.dot'.format(file), '-o{}.{}'.format(file, type)])
