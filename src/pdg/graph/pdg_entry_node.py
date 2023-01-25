import string

from pdg_node import PDGNode


class PDGEntryNode(PDGNode):
    __label: string

    def __init__(self, ast_node, node_type, label: string):
        super(ast_node, node_type)
        self.__label = label

    # override
    def get_label(self) -> string:
        return self.__label

    # override
    def get_exas_label(self) -> string:
        return self.__label

    # override
    @staticmethod
    def is_definition() -> bool:
        return False

    # override
    def to_string(self) -> string:
        return self.get_label()