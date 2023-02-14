from typing import Optional

from git import Commit, DiffIndex
from multimethod import multimethod

from collections import deque
from src.change.change_analyzer import ChangeAnalyzer
from src.change.change_file import ChangeFile
from src.change.change_class import ChangeClass
from src.change.change_method import ChangeMethod
from src.change.change_entity import Type
from src.change.change_field import ChangeField
from src.change.change_initializer import ChangeInitializer
from src.change.change_revision import ChangeRevision
from src.utils.config import Config


class RevisionAnalyzer:
    __change_analyzer: ChangeAnalyzer
    __revision: int
    __commit: Commit

    __mapped_files_m: set[ChangeFile] = set()
    __mapped_files_n: set[ChangeFile] = set()
    __classes_m: set[ChangeClass] = set()
    __classes_n: set[ChangeClass] = set()
    __mapped_classes_m: set[ChangeClass] = set()
    __mapped_classes_n: set[ChangeClass] = set()
    __methods_m: set[ChangeMethod] = set()
    __methods_n: set[ChangeMethod] = set()
    __mapped_methods_m: set[ChangeMethod] = set()
    __mapped_methods_n: set[ChangeMethod] = set()
    __fields_m: set[ChangeField] = set()
    __fields_n: set[ChangeField] = set()
    __mapped_fields_m: set[ChangeField] = set()
    __mapped_fields_n: set[ChangeField] = set()
    __inits_m: set[ChangeInitializer] = set()
    __inits_n: set[ChangeInitializer] = set()
    __mapped_inits_m: set[ChangeInitializer] = set()
    __mapped_inits_n: set[ChangeInitializer] = set()

    change_revision: ChangeRevision

    @multimethod
    def __init__(self, change_analyzer: ChangeAnalyzer, revision: int):
        self.__change_analyzer = change_analyzer
        self.__revision = revision

    @multimethod
    def __init__(self, change_analyzer: ChangeAnalyzer, commit: Commit):
        self.__change_analyzer = change_analyzer
        self.__commit = commit
        self.__revision = commit.committed_datetime  # TODO

    def get_change_analyzer(self) -> ChangeAnalyzer:
        return self.__change_analyzer

    def get_revision(self) -> int:
        return self.__revision

    def get_mapped_files_m(self) -> set[ChangeFile]:
        return self.__mapped_files_m

    def get_mapped_files_n(self) -> set[ChangeFile]:
        return self.__mapped_files_n

    def get_mapped_classes_m(self) -> set[ChangeClass]:
        return self.__mapped_classes_m

    def get_mapped_classes_n(self) -> set[ChangeClass]:
        return self.__mapped_classes_n

    def get_mapped_methods_m(self) -> set[ChangeMethod]:
        return self.__mapped_methods_m

    def get_mapped_methods_n(self) -> set[ChangeMethod]:
        return self.__mapped_methods_n

    def get_mapped_fields_m(self) -> set[ChangeField]:
        return self.__mapped_fields_m

    def get_mapped_fields_n(self) -> set[ChangeField]:
        return self.__mapped_fields_n

    def get_mapped_inits_m(self) -> set[ChangeInitializer]:
        return self.__mapped_inits_m

    def get_mapped_inits_n(self) -> set[ChangeInitializer]:
        return self.__mapped_inits_n

    def analyze_git(self) -> bool:
        if not self.__build_git_modified_files():
            return False
        if Config.count_change_file_only:
            return True
        if not self.__map():
            return False
        self.__derive_changes()
        if len(self.__mapped_methods_m) > 100:
            return False
        return True

    def __build_git_modified_files(self) -> bool:
        if len(self.__commit.parents) == 1:
            parent: Optional[Commit] = self.__commit.parents[0]
            if parent is None:
                return False
            diffs: DiffIndex = parent.diff(self.__commit, paths=['*.adb'])
            if diffs is None:
                return False
            if len(diffs) > 50:
                return False
            if len(diffs) > 0:
                self.change_revision = ChangeRevision()
                self.change_revision.id = self.__revision
                self.change_revision.number_of_files = len(diffs)
                self.change_revision.files = []
            if Config.count_change_file_only:
                return True
            if len(diffs) > 0:
                self.__change_analyzer.increment_number_of_code_revisions()
                for diff in diffs.iter_change_type('M'):
                    old_content: str
                    new_content: str
                    try:
                        old_content = diff.a_blob.data_stream.read().decode('ISO-8859-2')
                    except:
                        print('Error reading file: ' + diff.a_blob.path)
                        continue
                    try:
                        new_content = diff.b_blob.data_stream.read().decode('ISO-8859-2')
                    except:
                        print('Error reading file: ' + diff.b_blob.path)
                        continue
                    file_m: ChangeFile = ChangeFile(self, diff.a_blob.path, old_content)
                    file_n: ChangeFile = ChangeFile(self, diff.b_blob.path, new_content)
                    self.__mapped_files_m.add(file_m)
                    # // this.crevision.files.add(new CSourceFile(diff
                    # //							.getNewPath(), fileM.getSourceFile().getLines()
                    # //							.size()));
                    self.__mapped_files_n.add(file_n)
                    file_m.set_change_type(Type.MODIFIED)
                    file_n.set_change_type(Type.MODIFIED)
                    file_m.set_mapped_file(file_n)
                    file_n.set_mapped_file(file_m)
        return True

    def __map(self) -> bool:
        self.__map_classes()
        self.__map_methods()
        return True

    def __map_classes(self):
        for file_m in self.__mapped_files_m:
            file_n: ChangeFile = file_m.get_mapped_file()
            file_m.compute_similarity(file_n)
            for change_class in file_m.get_classes():
                if change_class.get_mapped_class() is not None:
                    self.__mapped_classes_m.add(change_class)
                    self.__mapped_classes_n.add(change_class.get_mapped_class())
                    stack_classes: deque = deque()
                    stack_classes.append(change_class)
                    while len(stack_classes) > 0:
                        stack_class: ChangeClass = stack_classes.pop()
                        stack_class.compute_similarity(stack_class.get_mapped_class(), False)
                        for inner_change_class in stack_class.get_inner_classes(False):
                            if inner_change_class.get_mapped_class() is not None:
                                self.__mapped_classes_m.add(inner_change_class)
                                self.__mapped_classes_n.add(inner_change_class.get_mapped_class())
                                stack_classes.append(inner_change_class)
                else:
                    self.__classes_m.add(change_class)
            for change_class in file_n.get_classes():
                if change_class.get_mapped_class() is not None:
                    self.__mapped_classes_n.add(change_class)
                else:
                    self.__classes_n.add(change_class)
                for inner_change_class in change_class.get_inner_classes(True):
                    if inner_change_class.get_mapped_class is not None:
                        self.__mapped_classes_m.add(inner_change_class)
                    else:
                        self.__classes_n.add(inner_change_class)
        ChangeClass.map_all(self.__classes_m, self.__classes_n, self.__mapped_classes_m, self.__mapped_classes_n)
        self.__clear_class_body_mapping()
        for change_class in self.__mapped_classes_m:
            change_class.compute_similarity(change_class.get_mapped_class(), True)
            for change_method in change_class.get_methods():
                if change_method.get_mapped_method() is not None:
                    self.__mapped_methods_m.add(change_method)
                else:
                    self.__methods_m.add(change_method)
            for change_field in change_class.get_fields():
                if change_field.get_mapped_field() is not None:
                    self.__mapped_fields_m.add(change_field)
                else:
                    self.__fields_m.add(change_field)
            for change_initializer in change_class.get_initializers():
                if change_initializer.get_mapped_initializer() is not None:
                    self.__mapped_inits_m.add(change_initializer)
                else:
                    self.__inits_m.add(change_initializer)
        for change_class in self.__mapped_classes_n:
            for change_method in change_class.get_methods():
                if change_method.get_mapped_method() is not None:
                    self.__mapped_methods_n.add(change_method)
                else:
                    self.__methods_n.add(change_method)
            for change_field in change_class.get_fields():
                if change_field.get_mapped_field() is not None:
                    self.__mapped_fields_n.add(change_field)
                else:
                    self.__fields_n.add(change_field)
            for change_initializer in change_class.get_initializers():
                if change_initializer.get_mapped_initializer() is not None:
                    self.__mapped_inits_n.add(change_initializer)
                else:
                    self.__inits_n.add(change_initializer)
        for change_class in self.__classes_m:
            for change_method in change_class.get_methods():
                self.__methods_m.add(change_method)
            for change_field in change_class.get_fields():
                self.__fields_m.add(change_field)
            for change_initializer in change_class.get_initializers():
                self.__inits_m.add(change_initializer)
                    
    def __clear_class_body_mapping(self):
        for change_class in self.__classes_m:
            change_class.clear_body_mapping()
        for change_class in self.__classes_n:
            change_class.clear_body_mapping()
        for change_class in self.__mapped_classes_m:
            change_class.clear_body_mapping()
        for change_class in self.__mapped_classes_n:
            change_class.clear_body_mapping()

    def __map_methods(self):
        ChangeMethod.map_all(self.__methods_m, self.__methods_n, self.__mapped_methods_m, self.__mapped_methods_n, False)

    def __derive_changes(self):
        #  derive_field_changes()
        self.__derive_method_changes()
        #  derive_init_changes()
        #  derive_enum_constant_changes()
        #  derive_class_changes()

    def __derive_method_changes(self):
        for change_method_m in self.__mapped_methods_m:
            change_method_m.derive_changes()
            if change_method_m._get_change_type() == Type.UNCHANGED:
                self.__mapped_classes_m.remove(change_method_m)
                self.__mapped_classes_n.remove(change_method_m.get_mapped_method())