from . import visual
from .build import ChangeGraphBuilder

_builder = ChangeGraphBuilder()

build_from_files = _builder.build_from_files
build_from_trees = _builder.build_from_trees

export_graph_image = visual.export_graph_image
print_out_nodes = visual.print_out_nodes
