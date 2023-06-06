from typing import cast

from libadalang import AnalysisContext, AdaNode, AnalysisUnit, SubpBody

from src.graphics.dot_graph import DotGraph
from src.pdg import PDGGraph, PDGBuildingContext


def main():
    context = AnalysisContext()
    unit_c: AnalysisUnit = context.get_from_file('../c.adb')
    node_c: AdaNode = unit_c.root
    for procedure in node_c.finditer(lambda n: isinstance(n, SubpBody)):
        print(procedure)
        graph: PDGGraph = PDGGraph(cast(SubpBody, procedure),
                                   PDGBuildingContext('', '', '', False))
        # graph.prune()
        dot_graph: DotGraph = DotGraph(graph, False)
        dot_graph.to_graphics('dotfile', 'typetype')


if __name__ == '__main__':
    main()
