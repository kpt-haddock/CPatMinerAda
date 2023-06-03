from __future__ import annotations

from typing import Iterator, Optional

from multimethod import multimethod

from git import Repo, Commit, DiffIndex

from src.repository.changed_file import ChangedFile
import charade


class GitConnector:
    __url: str
    __number_of_commits: int = -1
    __number_of_code_commits: int = -1

    __repository: Repo

    def __init__(self, url: str):
        self.__url = url

    def get_repository(self) -> Repo:
        return self.__repository

    @multimethod
    def get_number_of_commits(self) -> int:
        return self.__number_of_commits

    # this method is not used in CPatMiner
    def get_number_of_code_commits(self) -> int:
        return self.__number_of_code_commits

    def connect(self) -> bool:
        self.__repository = Repo(self.__url)

    def log(self) -> Iterator[Commit]:
        return self.__repository.iter_commits()

    # this method is not used in CPatMiner
    @multimethod
    def get_number_of_commits(self, extension: str) -> int:
        return 500

    def get_commit(self, commit_id: str) -> Commit:
        return self.__repository.commit(commit_id)

    def get_changed_files(self, commit: Commit, string: str) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        parent: Optional[Commit] = None
        if len(commit.parents) > 0:
            parent = commit.parents[0]
        if parent is not None:
            diffs: DiffIndex = parent.diff(commit, paths=['*.adb', '*.ads'])
            print(len(diffs))
            for diff in diffs.iter_change_type('M'):
                try:
                    old_content: str = diff.a_blob.data_stream.read().decode('ISO-8859-2')
                    new_content: str = diff.b_blob.data_stream.read().decode('ISO-8859-2')
                    files.append(ChangedFile(diff.b_path, new_content, diff.a_path, old_content))
                except:
                    print('error: ' + charade.detect(diff.a_blob.data_stream.read()))
        return files
