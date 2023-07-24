import os
import argparse
import multiprocessing
import pickle
import sys

import adaflowgraph
import changegraph
from log import logger
from vcs.traverse import GitAnalyzer
from patterns import Miner
import settings

class RunModes:
    BUILD_ADA_FLOW_GRAPH = 'afg'
    BUILD_CHANGE_GRAPH = 'cg'
    COLLECT_CHANGE_GRAPHS = 'collect-cgs'
    MINE_PATTERNS = 'patterns'
    ALL = [BUILD_ADA_FLOW_GRAPH, BUILD_CHANGE_GRAPH, COLLECT_CHANGE_GRAPHS, MINE_PATTERNS]


def main():
    logger.info('------------------------------ Starting ------------------------------')

    sys.setrecursionlimit(2 ** 31 - 1)
    multiprocessing.set_start_method('spawn', force=True)

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help=f'One of {RunModes.ALL}', type=str)
    args, _ = parser.parse_known_args()

    current_mode = args.mode
    # for example: afg -i c.adb
    if current_mode == RunModes.BUILD_ADA_FLOW_GRAPH:
        parser.add_argument('-i', '--input', help='Path to source code file', type=str, required=True)
        parser.add_argument('-o', '--output', help='Path to output file', type=str, default='adaflowgraph.dot')
        parser.add_argument('--no-closure', action='store_true')
        parser.add_argument('--show-deps', action='store_true')
        parser.add_argument('--hide-op-kinds', action='store_true')
        parser.add_argument('--show-data-keys', action='store_true')
        args = parser.parse_args()

        flow_graph = adaflowgraph.build_from_file(
            args.input, show_dependencies=args.show_deps, build_closure=not args.no_closure
        )
        adaflowgraph.export_graph_image(
            flow_graph, args.output, show_op_kinds=not args.hide_op_kinds, show_data_keys=args.show_data_keys
        )
    # for example: cg -s a.adb -d b.adb
    elif current_mode == RunModes.BUILD_CHANGE_GRAPH:
        parser.add_argument('-s', '--src', help='Path to source code before changes', type=str, required=True)
        parser.add_argument('-d', '--dest', help='Path to source code after changes', type=str, required=True)
        parser.add_argument('-o', '--output', help='Path to output file', type=str, default='changegraph.dot')
        args = parser.parse_args()

        fg = changegraph.build_from_files(args.src, args.dest)
        changegraph.export_graph_image(fg, args.output)
        GitAnalyzer._store_change_graphs([fg])
    elif current_mode == RunModes.COLLECT_CHANGE_GRAPHS:
        GitAnalyzer().build_change_graphs()
    elif current_mode == RunModes.MINE_PATTERNS:
        storage_dir = settings.get('change_graphs_storage_dir')
        file_names = os.listdir(storage_dir)
        
        logger.warning(f'Found {len(file_names)} files in storage directory.')

        change_graphs = []
        for file_num, file_name in enumerate(file_names):
            file_path = os.path.join(storage_dir, file_name)
            try:
                with open(file_path, 'rb') as f:
                    graphs = pickle.load(f)

                for graph in graphs:
                    change_graphs.append(pickle.loads(graph))
            except:
                logger.warning(f'Incorrect file {file_path}.')

            logger.warning(f'Loaded [{1 + file_num}/{len(file_names)}] files.')
        logger.warning('Pattern mining has started.')

        miner = Miner()
        try:
            miner.mine_patterns(change_graphs)
        except KeyboardInterrupt:
            logger.warning('KeyboardInterrupt: mined patterns will be stored before exit.')
        
        miner.print_patterns()
                


if __name__ == '__main__':
    main()