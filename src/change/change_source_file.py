import string


class CSourceFile:
    __lines_of_code: int = 0
    __path: string

    def __init__(self, path: string, lines_of_code: int):
        self.__lines_of_code = lines_of_code
        self.__path = path

    def get_path(self) -> string:
        return self.__path

    def get_lines_of_code(self) -> int:
        return self.__lines_of_code
