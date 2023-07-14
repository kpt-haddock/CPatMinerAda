import time
from typing import cast

from libadalang import AnalysisContext, AdaNode, AnalysisUnit, SubpBody, GPRProject, UnitProvider

from graphics.dot_graph import DotGraph
from pdg import PDGGraph, PDGBuildingContext


def main():
    # project: GPRProject = GPRProject('../default.gpr')
    # provider: UnitProvider = project.create_unit_provider()
    # context = AnalysisContext(unit_provider=provider)
    context = AnalysisContext()
    unit_c: AnalysisUnit = context.get_from_file('../c.adb')
    node_c: AdaNode = unit_c.root
    for procedure in node_c.finditer(lambda n: isinstance(n, SubpBody)):
        print(procedure)
        graph: PDGGraph = PDGGraph(cast(SubpBody, procedure),
                                   PDGBuildingContext('', '', '', False))
        # graph.prune()
        dot_graph: DotGraph = DotGraph(graph, False)
        print(procedure.p_relative_name.text)
        dot_graph.to_graphics(procedure.p_relative_name.text)
        time.sleep(1)


if __name__ == '__main__':
    main()
