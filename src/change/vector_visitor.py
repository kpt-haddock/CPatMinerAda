from collections import deque
from ctypes import c_int32
from typing import Optional

from libadalang import *
from overrides import overrides

from utils.ada_node_visitor import AdaNodeVisitor
from utils.ada_ast_util import node_type


class VectorVisitor(AdaNodeVisitor):
    method_fragment: int = 2
    loop_statement_fragment: int = 3
    if_statement_fragment: int = 4
    switch_statement_fragment: int = 5
    method_statement: int = 7
    declaration_statement: int = 8
    assert_statement: int = 9
    assign_statement: int = 10
    array_statement: int = 13
    expression: int = 14
    simple_name: int = 18
    literal: int = 19
    other_statement_fragment: int = 29
    other_fragments: int = 30
    not_considered_fragments: int = 31

    @property
    def max_size_of_gram(self) -> int:
        return 2

    @property
    def min_fragment_size(self) -> int:
        return 30

    gram_2_index: dict[int, int] = {}
    index_2_gram: dict[int, int] = {}

    property_vector: dict[AdaNode, Optional[dict[int, int]]] = {}

    indexer: list[int] = [0] * 322

    __vectors: dict[str, dict[int, int]]
    #  stack of children's n-gram vectors
    stack_children_vectors: deque[list[dict[int, int]]]
    #  stack of VERTICAL n-grams starting from the ROOT of the subtrees
    stack_children_root_v_grams: deque[list[dict[int, int]]]
    #  for end token of vector
    last_node: int
    #  for start token of vector
    stack_current_node: deque[int]

    def __init__(self):
        self.__vectors = {}
        self.stack_children_vectors = deque()
        self.stack_children_root_v_grams = deque()
        self.last_node = 0
        self.stack_current_node = deque()

    @property
    def vectors(self) -> dict[str, dict[int, int]]:
        return self.__vectors

    @overrides
    def pre_visit(self, node: AdaNode):
        self.last_node += 1
        self.stack_current_node.append(self.last_node)
        self.stack_children_vectors.append([])
        self.stack_children_root_v_grams.append([])

    @overrides
    def post_visit(self, node: AdaNode):
        self.build_fragment(node)

    def build_fragment(self, node: AdaNode):
        type: int = node_type(node)
        children_vectors: list[dict[int, int]] = self.stack_children_vectors.pop()
        children_root_v_grams: list[dict[int, int]] = self.stack_children_root_v_grams.pop()

        #  VERTICAL n-grams starting from this node
        my_root_v_grams: dict[int, int] = {}
        vector: dict[int, int] = {}

        #  Adding vectors of all children
        if children_vectors:
            vector.update(children_vectors[0].copy())
            for child_vector in children_vectors:
                for i in child_vector.keys():
                    if i in vector:
                        vector[i] = vector[i] + child_vector[i]
                    else:
                        vector[i] = child_vector[i]
        #  This node is also a single node type in the vector
        if VectorVisitor.indexer[type] != VectorVisitor.not_considered_fragments:
            gram: int = c_int32(type << 24).value
            index: int = VectorVisitor.gram_2_index[gram]
            if index in vector:
                vector[index] += 1
            else:
                vector[index] = 1
        #  This node is also a 1-gram in the vector
        if VectorVisitor.indexer[type] <= 11:
            gram: int = -VectorVisitor.indexer[type]
            temporary_index: int
            if gram in VectorVisitor.gram_2_index:
                temporary_index = VectorVisitor.gram_2_index[gram]
            else:
                temporary_index = len(VectorVisitor.gram_2_index)
                VectorVisitor.gram_2_index[gram] = temporary_index
                VectorVisitor.index_2_gram[temporary_index] = gram
            if temporary_index in my_root_v_grams:
                my_root_v_grams[temporary_index] += 1
            else:
                my_root_v_grams[temporary_index] = 1
        #  Building all n-grams starting from this node (will be used by its parent)
        if children_root_v_grams:
            if VectorVisitor.indexer[type] <= 11:
                for child_gram in children_root_v_grams:
                    for index in child_gram.keys():
                        gram: int = VectorVisitor.index_2_gram[index]
                        gram = c_int32(-((VectorVisitor.indexer[type] << int(4 * VectorVisitor.size_of_gram(gram))) - gram)).value
                        temporary_index: int
                        if gram in VectorVisitor.gram_2_index:
                            temporary_index = VectorVisitor.gram_2_index[gram]
                        else:
                            temporary_index = len(VectorVisitor.gram_2_index)
                            VectorVisitor.gram_2_index[gram] = temporary_index
                            VectorVisitor.index_2_gram[temporary_index] = gram
                        if temporary_index in vector:
                            vector[temporary_index] += child_gram[index]
                        else:
                            vector[temporary_index] = child_gram[index]
                        if VectorVisitor.size_of_gram(gram) < self.max_size_of_gram:
                            if temporary_index in my_root_v_grams:
                                my_root_v_grams[temporary_index] += child_gram[index]
                            else:
                                my_root_v_grams[temporary_index] = child_gram[index]
            else:
                for child_gram in children_root_v_grams:
                    for index in child_gram.keys():
                        if index in my_root_v_grams:
                            my_root_v_grams[index] += child_gram[index]
                        else:
                            my_root_v_grams[index] = child_gram[index]
        #  Build the corresponding fragment
        if node.is_a(SubpBody):
            VectorVisitor.property_vector[node] = vector
        #  Pushing the stacks respectively
        if self.stack_children_vectors:  # if not root
            if vector:
                parent_vectors: list[dict[int, int]] = self.stack_children_vectors.pop()  # get siblings
                parent_vectors.append(vector)  # join them (append this node type)
                self.stack_children_vectors.append(parent_vectors)  # back home
            if my_root_v_grams:
                parent_grams: list[dict[int, int]] = self.stack_children_root_v_grams.pop()  # get siblings
                parent_grams.append(my_root_v_grams)  # join them (append this node type)
                self.stack_children_root_v_grams.append(parent_grams)  # back home

    @staticmethod
    def size_of_gram(gram: int) -> int:
        i: int = 0
        g = abs(gram)
        while g != 0:
            i += 1
            g = g / 16
        return g


index: int = 0
for i in range(0, len(VectorVisitor.indexer)):
    if i == 0:
        VectorVisitor.indexer[i] = VectorVisitor.not_considered_fragments
    else:
        gram: int = c_int32(i << 24).value
        VectorVisitor.gram_2_index[gram] = index
        VectorVisitor.index_2_gram[index] = gram
        index += 1

        if i == node_type(SubpBody):
            VectorVisitor.indexer[i] = VectorVisitor.method_fragment
        elif i == node_type(ForLoopSpec):
            VectorVisitor.indexer[i] = VectorVisitor.loop_statement_fragment
        elif i == node_type(WhileLoopSpec):
            VectorVisitor.indexer[i] = VectorVisitor.loop_statement_fragment
        elif i == node_type(LoopStmt):
            VectorVisitor.indexer[i] = VectorVisitor.loop_statement_fragment
        elif i == node_type(IfStmt):
            VectorVisitor.indexer[i] = VectorVisitor.if_statement_fragment
        elif i == node_type(CaseStmt):
            VectorVisitor.indexer[i] = VectorVisitor.switch_statement_fragment
        elif i == node_type(IfExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(BinOp):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(BoxExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(CallExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(CaseExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(ConcatOp):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(DeclExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(MembershipExpr):
            VectorVisitor.indexer[i] = VectorVisitor.expression
        elif i == node_type(Identifier):
            VectorVisitor.indexer[i] = VectorVisitor.simple_name
        elif i == node_type(CharLiteral):
            VectorVisitor.indexer[i] = VectorVisitor.literal
        elif i == node_type(StringLiteral):
            VectorVisitor.indexer[i] = VectorVisitor.literal
        elif i == node_type(NullLiteral):
            VectorVisitor.indexer[i] = VectorVisitor.literal
        elif i == node_type(IntLiteral):
            VectorVisitor.indexer[i] = VectorVisitor.literal
        elif i == node_type(RealLiteral):
            VectorVisitor.indexer[i] = VectorVisitor.literal
        elif i == node_type(Aggregate):
            VectorVisitor.indexer[i] = VectorVisitor.array_statement
        elif i == node_type(BracketAggregate):
            VectorVisitor.indexer[i] = VectorVisitor.array_statement
        elif i == node_type(DeltaAggregate):
            VectorVisitor.indexer[i] = VectorVisitor.array_statement
        elif i == node_type(BracketDeltaAggregate):
            VectorVisitor.indexer[i] = VectorVisitor.array_statement
        elif i == node_type(NullRecordAggregate):
            VectorVisitor.indexer[i] = VectorVisitor.array_statement
        elif i == node_type(AttributeRef):
            VectorVisitor.indexer[i] = VectorVisitor.other_fragments
        else:
            VectorVisitor.indexer[i] = VectorVisitor.other_statement_fragment
