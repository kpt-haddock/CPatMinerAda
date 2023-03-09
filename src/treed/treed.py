from bisect import insort
from typing import Optional, T, cast

from libadalang import AdaNode, Identifier
from multimethod import multimethod

from src.utils.pair import Pair

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
                if self.__is_same_name(iname, name_n):
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
        p: list[list[str]] = [[None for _ in range(len(mapped_nodes) + 1)] for _ in range(len(nodes) + 1)]
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
                    ...
                    # node.set_property??? TODO
                    # node2.set_property???
                else:
                    ...
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
    def __map_pivots(self):
        for node in self.__tree.keys():
            self.__tree_map[node] = dict()
        self.__set_map(self.__ast_m, self.__ast_n, 1.0)
        nodes_m: list[AdaNode] = self.__get_children_containers(self.__ast_m)
        nodes_n: list[AdaNode] = self.__get_children_containers(self.__ast_n)
        heights_m: list[AdaNode] = nodes_m.copy()
        heights_n: list[AdaNode] = nodes_n.copy()
        heights_m.sort(key=lambda x: self.__tree_height[x], reverse=True)
        heights_n.sort(key=lambda x: self.__tree_height[x], reverse=True)
        self.__map_pivots(nodes_m, nodes_n, heights_m, heights_n)

    @multimethod
    def __map_pivots(self, nodes_m: list[AdaNode], nodes_n: list[AdaNode], heights_m: list[AdaNode], heights_n: list[AdaNode]):
        lcs_m: list[int] = []
        lcs_n: list[int] = []
        self.__lcs(nodes_m, nodes_n, lcs_m, lcs_n)
        for i in reversed(range(0, len(lcs_m))):
            index_m: int = lcs_m[i]
            index_n: int = lcs_n[i]
            node_m: AdaNode = nodes_m[index_m]
            node_n: AdaNode = nodes_n[index_n]
            self.__set_map(node_m, node_n, 1.0)
            self.__pivots_m.add(node_m)
            self.__pivots_n.add(node_n)
            del nodes_m[index_m]
            del nodes_n[index_n]
            heights_m.remove(node_m)
            heights_n.remove(node_n)
        while nodes_m and nodes_n:
            height_m: int = self.__tree_height.get(heights_m[0])
            height_n: int = self.__tree_height.get(heights_n[0])
            expanded_m: bool = False
            expanded_n: bool = False
            if height_m >= height_n:
                expanded_m = self.__expand_for_pivots(nodes_m, heights_m, height_m)
            if height_n >= height_m:
                expanded_n = self.__expand_for_pivots(nodes_n, heights_n, height_n)
            if expanded_m or expanded_n:
                self.__map_pivots(nodes_m, nodes_n, heights_m, heights_n)
                break

    def __expand_for_pivots(self, node_list: list[AdaNode], heights: list[AdaNode], h: int) -> bool:
        nodes: set[AdaNode] = set()
        for node in heights:
            if self.__tree_height.get(node) == h:
                nodes.add(node)
            else:
                break
        expanded: bool = False
        for i in reversed(range(0, len(node_list))):
            node: AdaNode = node_list[i]
            if node in nodes:
                del node_list[i]
                del heights[0]
                children: list[AdaNode] = self.__get_children_containers(node)
                if children:
                    expanded = True
                    for j in range(0, len(children)):
                        child: AdaNode = children[j]
                        node_list.append(child)
                        insort(heights, child, key=lambda n: self.__tree_height.get(n) * -1)
        return expanded

    def __expand_for_moving(self, node_list: list[AdaNode], heights: list[AdaNode], h: int) -> bool:
        nodes: set[AdaNode] = set()
        for node in heights:
            if self.__tree_height.get(node) == h:
                nodes.add(node)
            else:
                break
        expanded: bool = False
        for i in reversed(range(0, len(node_list))):
            node: AdaNode = node_list[i]
            if node in nodes:
                del node_list[i]
                del heights[0]
                children: list[AdaNode] = self.__get_not_yet_mapped_descendant_containers(node)
                if children:
                    expanded = True
                    for j in range(0, len(children)):
                        child: AdaNode = children[j]
                        node_list.append(child)
                        insort(heights, child, key=lambda n: self.__tree_height.get(n) * -1)
        return expanded

    def __lcs(self, nodes_m: list[AdaNode], nodes_n: list[AdaNode], lcs_m: list[int], lcs_n: list[int]):
        d: list[list[int]] = [[0 for _ in range(len(nodes_n) + 1)] for _ in range(2)]
        p: list[list[str]] = [[None for _ in range(len(nodes_m) + 1)] for _ in range(len(nodes_n) + 1)]
        for i in reversed(range(0, len(nodes_m))):
            node_m: AdaNode = nodes_m[i]
            height_m: int = self.__tree_height.get(node_m)
            vector_m: dict[str, int] = self.__tree_vector.get(node_m)
            for j in range(0, len(nodes_n)):
                d[0][j] = d[1][j]
            for j in reversed(range(0, len(nodes_n))):
                node_n: AdaNode = nodes_n[j]
                height_n: int = self.__tree_height.get(node_n)
                vector_n: dict[str, int] = self.__tree_vector.get(node_n)
                # TODO: sub tree match
                if height_m == height_n and vector_m == vector_n and node_m.:
                    d[1][j] = d[0][j + 1] + 1
                    p[i][j] = 'D'
                elif d[0][j] >= d[1][j + 1]:
                    d[1][j] = d[0][j]
                    p[i][j] = 'U'
                else:
                    d[1][j] = d[1][j + 1]
                    p[i][j] = 'R'
        i: int = 0
        j: int = 0
        while i < len(nodes_m) and j < len(nodes_n):
            if p[i][j] == 'D':
                lcs_m.append(i)
                lcs_n.append(j)
                i += 1
                j += 1
            elif p[i][j] == 'U':
                i += 1
            else:
                j += 1

    def __get_children_containers(self, node: AdaNode) -> list[AdaNode]:
        children: list[AdaNode] = []
        for child in self.__tree.get(node):
            if self.__tree_height.get(child) >= MIN_HEIGHT:
                children.append(child)
        return children

    def __compare_nodes(self, node1: AdaNode, node2: AdaNode) -> int:
        d: int = self.__tree_height.get(node2) - self.__tree_height.get(node1)
        if d != 0:
            return d
        d = self.__tree_depth.get(node1) - self.__tree_depth.get(node2)
        if d != 0:
            return d
        # TODO original code uses start position and not line no.
        return node1.sloc_range.start.line - node2.sloc_range.start.line

    def __map_bottom_up(self):
        heights_m: list[AdaNode] = list(self.__pivots_m)
        heights_m.sort(key=self.__compare_nodes)
        for node_m in heights_m:
            node_n: AdaNode = next(iter(self.__tree_map.get(node_m).keys()))
            ancestors_m: list[AdaNode] = []
            ancestors_n: list[AdaNode] = []
            self.__get_not_yet_mapped_ancestors(node_m, ancestors_m)
            self.__get_not_yet_mapped_ancestors(node_n, ancestors_n)
            self.__map(ancestors_m, ancestors_n, MIN_SIMILARITY)
        

    def __map(self, nodes_m: list[AdaNode], nodes_n: list[AdaNode], threshold: float) -> list[AdaNode]:
        pairs_of_ancestor: dict[AdaNode, set[Pair]] = dict()
        pairs: list[Pair] = []
        for node_m in nodes_m:
            pairs1: set[Pair] = set()
            for node_n in nodes_n:
                similarity: float = self.__compute_similarity(node_m, node_n, threshold)
                if similarity >= threshold:
                    # The original example uses start position and not line number TODO
                    pair: Pair = Pair(node_m, node_n, similarity,
                                      - abs((node_m.parent.sloc_range.start.line - node_m.sloc_range.start.line) -
                                            (node_n.parent.sloc_range.start.line - node_n.sloc_range.start.line)))
                    pairs1.add(pair)
                    pairs2: set[Pair] = pairs_of_ancestor.get(node_n, set())
                    pairs2.add(pair)
                    pairs_of_ancestor[node_n] = pairs2
                    pairs.append(pair)
            pairs_of_ancestor[node_m] = pairs1
        pairs.sort(reverse=True)
        nodes: list[AdaNode] = []
        while pairs:
            pair: Pair = pairs[0]
            node_m: AdaNode = cast(AdaNode, pair.get_object1())
            node_n: AdaNode = cast(AdaNode, pair.get_object2())
            self.__set_map(node_m, node_n, pair.get_weight())
            nodes.append(node_m)
            nodes.append(node_n)
            for p in pairs_of_ancestor.get(node_m):
                pairs.remove(p)
            for p in pairs_of_ancestor.get(node_n):
                pairs.remove(p)
        return nodes

    def __set_map(self, node_m: AdaNode, node_n: AdaNode, w: float):
        self.__tree_map[node_m][node_n] = w
        self.__tree_map[node_n][node_m] = w

    @multimethod
    def __compute_similarity(self, node_m: AdaNode, node_n: AdaNode, threshold: float) -> float:
        # TODO: line 635 TreedMapper.java
        ...

    def __compute_vector_similarity(self, l1: list[AdaNode], l2: list[AdaNode]) -> list[float]:
        similarities: list[float] = [0.0 for _ in range(max(len(l1), len(l2)))]
        pairs_of_node: dict[AdaNode, set[Pair]] = dict()
        pairs: list[Pair] = []
        for node1 in l1:
            pairs1: set[Pair] = set()
            for node2 in l2:
                similarity: float = self.__compute_similarity(self.__tree_vector[node1], self.__tree_vector[node2])
                if similarity > 0:
                    pair: Pair = Pair(node1, node2, similarity)
                    pairs1.add(pair)
                    pairs2: set[Pair] = pairs_of_node.get(node2, set())
                    pairs2.add(pair)
                    pairs_of_node[node2] = pairs2
                    pairs.append(pair)
            pairs_of_node[node1] = pairs1
        pairs.sort(reverse=True)
        i: int = 0
        while pairs:
            pair: Pair = pairs[0]
            similarities[i] = pair.get_weight()
            for p in pairs_of_node[pair.get_object1()]:
                pairs.remove(p)
            for p in pairs_of_node[pair.get_object2()]:
                pairs.remove(p)
        return similarities


    @staticmethod
    @multimethod
    def __compute_similarity(vector_m: dict[str, int], vector_n: dict[str, int]) -> float:
        similarity: float = 0.0
        keys: set[str] = set(vector_m.keys()).intersection(set(vector_n.keys()))
        for key in keys:
            similarity += min(vector_m[key], vector_n[key])
        similarity = 2 * (similarity + SIMILARITY_SMOOTH) / (len(vector_m) + len(vector_n) + 2 * SIMILARITY_SMOOTH)
        return similarity

    @staticmethod
    def __length(self, vector: dict[T, int]) -> int:
        length: int = 0
        for value in vector.values():
            length += value
        return length

    def __get_not_yet_mapped_ancestors(self, node: AdaNode, ancestors: list[AdaNode]):
        parent: AdaNode = node.parent
        if len(self.__tree_map[parent]) == 0:
            ancestors.append(parent)
            self.__get_not_yet_mapped_ancestors(parent, ancestors)

    @multimethod
    def __map_top_down(self):
        self.__map_top_down(self.__ast_m)

    @multimethod
    def __map_top_down(self, node_m: AdaNode):
        #  TODO
        ...

    def __max_height(self, nodes: list[AdaNode], maxima: list[AdaNode]):
        maximum: int = 0
        for node in nodes:
            h: int = self.__tree_height[node]
            if h >= maximum:
                if h > maximum:
                    maximum = h
                    maxima.clear()
                maxima.append(node)
        return maximum

    def __map_unchanged_nodes(self, node_m: AdaNode, node_n: AdaNode):
        self.__set_map(node_m, node_n, 1.0)
        children_m: list[AdaNode] = self.__tree[node_m]
        children_n: list[AdaNode] = self.__tree[node_n]
        for i in range(0, len(children_m)):
            self.__map_unchanged_nodes(children_m[i], children_n[i])

    def __get_not_yet_matched_nodes(self, nodes: list[AdaNode]):
        not_yet_mapped_nodes: list[AdaNode] = []
        for node in nodes:
            if len(self.__tree_map[node]) == 0:
                not_yet_mapped_nodes.append(node)
        return not_yet_mapped_nodes

    @multimethod
    def __map_moving(self):
        ...

    @multimethod
    def __map_moving(self, ast_m: AdaNode, ast_n: AdaNode):
        list_m: list[AdaNode] = self.__get_not_yet_mapped_descendant_containers(ast_m)
        list_n: list[AdaNode] = self.__get_not_yet_mapped_descendant_containers(ast_n)
        heights_m: list[AdaNode] = list_m.copy()
        heights_n: list[AdaNode] = list_n.copy()
        heights_m.sort(key=lambda x: self.__tree_height[x], reverse=True)
        heights_n.sort(key=lambda x: self.__tree_height[x], reverse=True)
        self.__map_moving(list_m, list_n, heights_m, heights_n)

    @multimethod
    def __map_moving(self, list_m: list[AdaNode], list_n: list[AdaNode], heights_m: list[AdaNode], heights_n: list[AdaNode]):
        mapped_nodes: list[AdaNode] = self.__map(list_m, list_n, MIN_SIMILARITY_MOVE)
        for i in range(0, len(mapped_nodes), 2):
            node_m: AdaNode = mapped_nodes[i]
            node_n: AdaNode = mapped_nodes[i + 1]
            list_m.remove(node_m)
            list_n.remove(node_n)
            heights_m.remove(node_m)
            heights_n.remove(node_n)
        while len(list_m) > 0 and len(list_n) > 0:
            height_m: int = self.__tree_height[heights_m[0]]
            height_n: int = self.__tree_height[heights_n[0]]
            expanded_m: bool = False
            expanded_n: bool = False
            if height_m >= height_n:
                expanded_m = self.__expand_for_moving(list_m, heights_m, height_m)
            if height_n >= height_m:
                expanded_n = self.__expand_for_moving(list_n, heights_n, height_n)
            if expanded_m or expanded_n:
                self.__map_moving(list_m, list_n, heights_m, heights_n)
                break

    def __get_not_yet_mapped_descendant_containers(self, node: AdaNode) -> list[AdaNode]:
        children: list[AdaNode] = []
        for child in self.__tree[node]:
            if child not in self.__pivots_m and child not in self.__pivots_n and self.__tree_height[child] >= MIN_HEIGHT:
                if len(self.__tree_map[child]) == 0:
                    children.append(child)
                else:
                    children.extend(self.__get_not_yet_mapped_descendant_containers(child))
        return children                

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