from change_initializer import CInitializer
from change_method import CMethod
from change_source_file import CSourceFile


class CRevision:
    id: int
    number_of_files: int = 0
    files: list[CSourceFile]
    methods: list[CMethod]
    initializers: list[CInitializer]

    def get_id(self) -> int:
        return self.id

    def get_number_of_files(self) -> int:
        return self.number_of_files

    def get_files(self) -> list[CSourceFile]:
        return self.files

    def get_methods(self) -> list[CMethod]:
        return self.methods

    def get_initializers(self) -> list[CInitializer]:
        return self.initializers
