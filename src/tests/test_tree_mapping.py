from libadalang import AnalysisContext, AnalysisUnit, AdaNode
from treed.treed import TreedMapper

def test_tree_mapping():
    prefix = 'examples/double_negation'
    for i in range(1, 2):
        path_old = f'{prefix}/{i}_old.adb'
        path_new = f'{prefix}/{i}_new.adb'
        with open(path_old, 'r') as src1, open(path_new, 'r') as src2:
            context = AnalysisContext()
            unit_old = context.get_from_file(path_old)
            unit_new = context.get_from_file(path_new)
            node_old = unit_old.root
            node_new = unit_new.root
            tree_mapper = TreedMapper(node_old, node_new, src1.read(), src2.read())
            tree_mapper.map()
            tree_mapper.print_changes()
            print('Number of changed AST nodes: {}'.format(tree_mapper.get_number_of_changes()))
            print('Number of unmaps: {}'.format(tree_mapper.get_number_of_unmaps()))
            print('Number of non name unmaps: {}'.format(tree_mapper.get_number_of_non_name_unmaps()))


if __name__ == '__main__':
    test_tree_mapping()