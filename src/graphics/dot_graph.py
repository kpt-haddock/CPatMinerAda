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
    dot: Digraph

    @multimethod
    def __init__(self, change_graph: ChangeGraph):
        #  add nodes
        self.dot = Digraph()
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
            self.dot.node(str(id), node.get_label(), shape=shape)

        #  add edges
        for node in change_graph.get_nodes():
            t_id: int = ids[node]
            for edge in node.get_in_edges():
                s_id: int = ids[edge.get_source()]
                label: str = edge.get_label()
                if label == 'T' or label == 'F':
                    self.dot.edge(str(s_id), str(t_id), label)
                else:
                    self.dot.edge(str(s_id), str(t_id), style=DotGraph.STYLE_DOTTED, label=label)

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

    def to_graphics(self, file: str):
        self.dot.render(view=False, filename=file)
