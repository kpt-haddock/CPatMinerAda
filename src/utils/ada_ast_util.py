from libadalang import AdaNode


def is_literal(ast_node_type: int) -> bool:
    raise NotImplementedError('ada_ast_util is_literal')


def is_literal(node: AdaNode) -> bool:
    raise NotImplementedError('ada_ast_util is_literal')
