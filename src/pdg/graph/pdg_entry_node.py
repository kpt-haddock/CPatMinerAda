from pdg_node import PDGNode


class PDGEntryNode(PDGNode):
    __label: str

    def __init__(self, ast_node, node_type, label: str, ast_node_type: int):
        super().__init__(ast_node, ast_node_type)
        self.__label = label

    # override
    def get_label(self) -> str:
        return self.__label

    # override
    def get_exas_label(self) -> str:
        return self.__label

    # override
    @staticmethod
    def is_definition() -> bool:
        return False

    # override
    def to_string(self) -> str:
        return self.get_label()
