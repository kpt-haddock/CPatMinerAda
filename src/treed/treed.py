from typing import Optional

from libadalang import AdaNode, Identifier
from multimethod import multimethod

PROPERTY_MAP: str          = "m"
PROPERTY_STATUS: str       = "s"

GRAM_MAX_LENGTH: int       = 2
MIN_HEIGHT: int            = 2
MIN_SIMILARITY: float      = 0.5
MIN_SIMILARITY_MOVE: float = 0.75
SIMILARITY_SMOOTH: float   = (3 * MIN_SIMILARITY - 1) / (1 - MIN_SIMILARITY)

STATUS_UNCHANGED: int      = 0
STATUS_RELABELED: int      = 1
STATUS_UNMAPPED: int       = 2
STATUS_MOVED: int          = 3


class TreedBuilder:
    __root: AdaNode
    __visit_doc_tags: bool
    tree: dict[AdaNode, list[AdaNode]] = dict()
    tree_height: dict[AdaNode, int] = dict()
    tree_depth: dict[AdaNode, int] = dict()

    def __init__(self, root: AdaNode, visit_doc_tags: bool):
        self.__root = root
        self.__visit_doc_tags = visit_doc_tags
        self.tree_depth[root] = 0

    def pre_visit(self, node: AdaNode):
        ...

    def post_visit(self, node: AdaNode):
        ...

    def build_tree(self, node: AdaNode):
        if node != self.__root:
            parent: AdaNode = node.parent
            children: list[AdaNode] = self.tree.get(parent)
            children.append(node)

    def build_tree_height(self, node: AdaNode):
        children: list[AdaNode] = self.tree.get(node)
        max: int = 0
        for child in children:
            height: int = self.tree_height.get(child)
            if height > max:
                max = height
        self.tree_height[node] = max + 1

    def __build_vector(self, node: AdaNode):
        ...

    def __add(self, vector: dict[str, int], other: dict[str, int]):
        for key in other.keys():
            if key in vector.keys():
                vector[key] += other[key]
            else:
                vector[key] = other[key]

class TreedMapper:
    __ast_m: AdaNode
    __ast_n: AdaNode
    __tree: dict[AdaNode, list[AdaNode]] = dict()
    __tree_height: dict[AdaNode, int] = dict()
    __tree_depth: dict[AdaNode, int] = dict()
    __tree_vector: dict[AdaNode, dict[str, int]] = dict()
    __tree_map: dict[AdaNode, dict[AdaNode, float]] = dict()
    __pivots_m: set[AdaNode] = set()
    __pivots_n: set[AdaNode] = set()
    __name_map_frequency: dict[str, dict[str, int]] = dict()
    __name_frequency: dict[str, int] = dict()
    __rename_map: dict[str, str] = dict()
    __number_of_changes: int = 0
    __number_of_unmaps: int = 0
    __number_of_non_name_unmaps: int = 0
    __visit_doc_tags: bool = False

    def __init__(self, ast_m: AdaNode, ast_n: AdaNode):
        self.__ast_m = ast_m
        self.__ast_n = ast_n

    def get_number_of_changes(self) -> int:
        return self.__number_of_changes

    def get_number_of_unmaps(self) -> int:
        return self.__number_of_unmaps

    def is_changed(self) -> bool:
        return self.__number_of_changes > 0

    def has_unmaps(self) -> bool:
        return self.__number_of_unmaps > 0

    def has_non_name_unmap(self) -> bool:
        return self.__number_of_non_name_unmaps > 0

    def map(self, visit_doc_tags: bool):
        self.__visit_doc_tags = visit_doc_tags
        self.__build_trees(visit_doc_tags)
        self.__map_pivots()
        self.__map_bottom_up()
        self.__map_moving()
        self.__map_top_down()
        self.__mark_changes()

    @multimethod
    def print_changes(self):
        self.print_changes(self.__ast_m)
        self.print_changes(self.__ast_n)

    @multimethod
    def print_changes(self, node: AdaNode):
        ...

    @staticmethod
    def get_status(status: int) -> str:
        match status:
            case STATUS_MOVED:
                return "MOVED"
            case STATUS_RELABELED:
                return "RELABELED"
            case STATUS_UNCHANGED:
                return "UNCHANGED"
            case STATUS_UNMAPPED:
                return "UNMAPPED"
            case _:
                return "NOTHING_ELSE"

    def __mark_changes(self):
        self.__mark_changes(self.__ast_m)
        self.__detect_renaming()
        self.__mark_unmapped(self.__ast_n)

    def __detect_renaming(self):
        imap: dict[str, set[str]] = dict()
        for name_m in self.__name_frequency.keys():
            f: int = self.__name_frequency[name_m]
            mapped: Optional[str] = None
            map_frequency: dict[str, int] = self.__name_map_frequency[name_m]
            for name_n in map_frequency.keys():
                if self.__is_same_name(name_m, name_n):
                    mapped = name_n
                    break
                mf: int = self.__name_map_frequency[name_m][name_n]
                if mf > f * MIN_SIMILARITY:
                    mapped = name_n
            if mapped is not None:
                self.__rename_map[name_m] = mapped
                s: set[str] = imap.get(mapped, None)
                if s is None:
                    s = set()
                    imap[mapped] = s
                s.add(name_m)
        for name_m in set(self.__rename_map.keys()):
            name_n: str = self.__rename_map[name_m]
            if self.__is_same_name(name_m, name_n):
                del self.__rename_map[name_m]
                continue
            for iname in imap[name_n]:
                if self__is_same_name(iname, name_n):
                    del self.__rename_map[name_m]
                    break

    def __is_same_name(self, name_m: str, name_n: str) -> bool:
        index_m: int = name_m.rfind('#')
        index_n: int = name_n.rfind('#')
        if index_m == -1 and index_n == -1:
            return name_m == name_n
        if index_m > -1 and index_n > -1:
            return name_m[index_m:] == name_n[index_n:]
        return False

    def __mark_unmapped(self, node: AdaNode):
        ...

    @multimethod
    def __mark_changes(self, node: AdaNode):
        ...

    @multimethod
    def __mark_changes(self, nodes: list[AdaNode], mapped_nodes: list[AdaNode]):
        d: list[list[int]] = [[0 for _ in range(len(mapped_nodes) + 1)] for _ in range(2)]
        p: list[list[str]] = [[None for _ in range(len(mapped_nodes) + 1)] for _ in range(len(nodes))]
        for i in range(1, len(nodes) + 1):
            node: AdaNode = nodes[i - 1]
            maps: dict[AdaNode, float] = self.__tree_map[node]
            for j in range(0, len(mapped_nodes) + 1):
                d[0][j] = d[1][j]
            for j in range(1, len(mapped_nodes) + 1):
                node_n: AdaNode = mapped_nodes[j - 1]
                if node_n in maps:
                    d[1][j] = d[0][j - 1] + 1
                    p[i][j] = 'D'
                elif d[0][j] > d[1][j - 1]:
                    d[1][j] = d[0][j]
                    p[i][j] = 'U'
                else:
                    d[1][j] = d[1][j - 1]
                    p[i][j] = 'L'
        i: int = len(nodes)
        j: int = len(mapped_nodes)
        while i > 0 and j > 0:
            if p[i][j] == 'D':
                node: AdaNode = nodes[i - 1]
                node2: AdaNode = mapped_nodes[j - 1]
                if TreedUtils.build_label_for_vector(node) == TreedUtils.build_label_for_vector(node2):
                    # node.set_property???
                    # node2.set_property???
                else:
                    # node.set_property???
                    # node2.set_property???
                i -= 1
                j -= 1
            elif p[i][j] == 'U':
                i -= 1
            else:
                j -= 1

    def __update_name_map(self, node_m: AdaNode, node_n: AdaNode):
        if isinstance(node_m, Identifier):
            name_m: str = node_m.text
            name_n: str = node_n.text
            map_frequency: dict[str, int] = self.__name_map_frequency.get(name_m, None)
            i_map_frequency: dict[str, int] = self.__name_map_frequency.get(name_n, None)
            if map_frequency is None:
                map_frequency = dict()
                self.__name_map_frequency[name_m] = map_frequency
            if i_map_frequency is None:
                i_map_frequency = dict()
                self.__name_map_frequency[name_n] = i_map_frequency
            c: int = map_frequency.get(name_n, 0)
            c += 1
            map_frequency[name_n] = c
            i_map_frequency[name_n] = c
            c = self.__name_frequency.get(name_m, 0)
            self.__name_frequency[name_m] = c + 1


    def __check_name_map(self, name_m: str, name_n: str):
        if name_m == name_n:
            return True
        return name_n == self.__rename_map.get(name_m, None)

    @multimethod
    def __build_tree(self, visit_doc_tags: bool):
        self.__build_tree(self.__ast_m, visit_doc_tags)
        self.__build_tree(self.__ast_n, visit_doc_tags)
        
    @multimethod
    def __build_tree(self, root: AdaNode, visit_doc_tags: bool):
        visitor: TreedBuilder = TreedBuilder(root, visit_doc_tags)
        # root.accept(visitor) TODO
        self.tree.update(visitor.tree)
        self.__tree_height.update(visitor.tree_height)
        self.__tree_depth.update(visitor.tree_depth)
        self.__tree_vector.update(visitor.tree_vector)

class TreedUtils:

    @staticmethod
    def build_label_for_vector(node: AdaNode) -> chr:
        ...
    
    @staticmethod
    def build_ast_label(node: AdaNode) -> str:
        ...