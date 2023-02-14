from src.change.change_initializer import ChangeInitializer
from src.change.change_method import ChangeMethod
from src.change.change_source_file import ChangeSourceFile


class ChangeRevision:
    id: int
    number_of_files: int = 0
    files: list[ChangeSourceFile]
    methods: list[ChangeMethod]
    initializers: list[ChangeInitializer]

    def get_id(self) -> int:
        return self.id

    def get_number_of_files(self) -> int:
        return self.number_of_files

    def get_files(self) -> list[ChangeSourceFile]:
        return self.files

    def get_methods(self) -> list[ChangeMethod]:
        return self.methods

    def get_initializers(self) -> list[ChangeInitializer]:
        return self.initializers
