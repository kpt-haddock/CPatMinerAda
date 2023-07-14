import time

from log import logger
import adaflowgraph
from changegraph.models import ChangeNode, ChangeGraph, ChangeEdge
from adaflowgraph.models import ExtControlFlowGraph, Node
from treed.treed import TreedMapper
from utils import ada_ast_util


class ChangeGraphBuilder:  # TODO: make gumtree optional
    def build_from_files(self, path1, path2, repo_info=None):
        logger.warning(f'Change graph building...', show_pid=True)
        start_building = time.time()

        start = time.time()
        fg1 = adaflowgraph.build_from_file(path1)
        fg2 = adaflowgraph.build_from_file(path2)
        logger.warning('Flow graphs... OK', start_time=start, show_pid=True)

        start = time.time()
        treed_mapper = TreedMapper(fg1.entry_node.ast, fg2.entry_node.ast)
        treed_mapper.map()
        logger.warning('Gumtree... OK', start_time=start, show_pid=True)

        # for node in gt1.nodes:
        #     if node.mapped:
        #         logger.info(f'Gumtree node {node} mapped to {node.mapped}', show_pid=True)

        start = time.time()

        ExtControlFlowGraph.map_by_treed_map(fg1, fg2, treed_mapper)
        logger.warning('Mapping... OK', start_time=start, show_pid=True)

        for node in fg1.nodes:
            if node.mapped:
                logger.log(logger.INFO, f'FG node {node} mapped to {node.mapped}, '
                                        # f'GT node {node.gt_node} to {node.mapped.gt_node}, '
                                        # f'status={node.gt_node.status} '
                                        f'and is_changed={ada_ast_util.is_changed(node.ast)}', show_pid=True)

        for node in fg2.nodes:
            node.version = Node.Version.AFTER_CHANGES
        cg = self._create_change_graph(fg1, fg2, repo_info=repo_info)
        logger.warning('Change graph building... OK', start_time=start_building, show_pid=True)

        for node in cg.nodes:
            logger.info(f'Change graph has node {node}', show_pid=True)

        return cg

    @staticmethod
    def _create_change_graph(fg1, fg2, repo_info=None):
        fg1.calc_changed_nodes_by_treed_map()
        fg2.calc_changed_nodes_by_treed_map()

        fg_changed_nodes = fg1.changed_nodes.union(fg2.changed_nodes)
        fg_node_to_cg_node = {}

        cg = ChangeGraph(repo_info=repo_info)
        for fg_node in fg_changed_nodes:
            if fg_node_to_cg_node.get(fg_node):
                continue

            node = ChangeNode.create_from_fg_node(fg_node)
            cg.nodes.add(node)
            node.set_graph(cg)  # todo: probably better to create method 'add_node'
            fg_node_to_cg_node[fg_node] = node

            if fg_node.mapped and fg_node.mapped in fg_changed_nodes:
                mapped_node = ChangeNode.create_from_fg_node(fg_node.mapped)
                cg.nodes.add(mapped_node)
                mapped_node.set_graph(cg)
                fg_node_to_cg_node[fg_node.mapped] = mapped_node

                node.mapped = mapped_node
                mapped_node.mapped = node

        for fg_node in fg_changed_nodes:
            for e in fg_node.in_edges:
                if e.node_from in fg_changed_nodes:
                    ChangeEdge.create(e.label, fg_node_to_cg_node[e.node_from], fg_node_to_cg_node[e.node_to])
        return cg


class GraphBuildingException(Exception):
    pass