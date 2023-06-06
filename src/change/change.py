from __future__ import annotations

from abc import abstractmethod
from builtins import NotImplementedError
from collections import deque
from enum import Enum
from typing import Optional, cast
from warnings import warn

import libadalang
from git import Commit, DiffIndex
from libadalang import *
from multimethod import multimethod
from overrides import override

from src.change.vector_visitor import VectorVisitor
from src.pdg import PDGNode, PDGEdge, PDGGraph, PDGBuildingContext
from src.repository.git_connector import GitConnector
from src.treed.treed import TreedMapper
from src.utils import Config, string_processor
from src.utils.ada_ast_util import node_type
from src.utils.ada_node_matcher import match
from src.utils.ada_node_visitor import accept
from src.utils.file_io import FileIO
from src.utils.pair import Pair
from src.utils.string_processor import serialize, do_lcs


class ChangeNode:
    ast_node_type: int
    change_type: int = -1
    version: int = -1
    starts: list[int]
    lengths: list[int]
    type: str
    label: str
    data_type: str
    data_name: str

    in_edges: list[ChangeEdge]
    out_edges: list[ChangeEdge]

    def __init__(self, node: PDGNode):
        self.starts = []
        self.lengths = []
        self.in_edges = []
        self.out_edges = []
        self.ast_node_type = node.get_ast_node_type()
        self.version = node.version
        if node.get_ast_node() is not None:
            pass

    def __set_position_info(self):
        ...

    def get_ast_node_type(self) -> int:
        return self.ast_node_type

    def get_change_type(self) -> int:
        return self.change_type

    def get_data_type(self) -> str:
        return self.data_type

    def get_data_name(self) -> str:
        return self.data_name

    def get_in_edges(self) -> list[ChangeEdge]:
        return self.in_edges

    def get_out_edges(self) -> list[ChangeEdge]:
        return self.out_edges

    def get_type(self) -> str:
        return self.type

    def get_label(self) -> str:
        if self.data_type is not None:
            if self.data_name is not None:
                return '{}({})'.format(self.data_type, self.data_name)
            return self.data_type
        return self.label


class ChangeEdge:
    source: ChangeNode
    target: ChangeNode
    label: str

    def __init__(self, source: ChangeNode, target: ChangeNode, e: PDGEdge):
        self.source = source
        self.target = target
        self.label = e.get_exas_label()
        source.out_edges.append(self)
        target.in_edges.append(self)

    def get_source(self) -> ChangeNode:
        return self.source

    def get_target(self) -> ChangeNode:
        return self.target

    def get_label(self) -> str:
        return self.label

    def is_mapped(self) -> bool:
        return self.label == '_map_'

    def to_string(self) -> str:
        return self.label


class ChangeAnalyzer:
    __project_name: str
    __project_id: int
    __url: str
    __start_revision: int = -1
    __end_revision: int = -1
    __number_of_revisions: int = -1
    __number_of_code_revisions: int = -1
    __number_of_extracted_revisions: int = -1
    __git_connector: GitConnector
    # __revision_analyzers: list[RevisionAnalyzer] = []
    __change_project: ChangeProject
    __output_path: str = 'C:/change graphs'

    @multimethod
    def __init__(self, project_name: str, project_id: int, url: str, start: int, end: int):
        self.__project_name = project_name
        self.__project_id = project_id
        self.__url = url
        self.__start_revision = start
        self.__end_revision = end

    @multimethod
    def __init__(self, project_name: str, project_id: int, url: str):
        self.__project_name = project_name
        self.__project_id = project_id
        self.__url = url

    def get_project_name(self) -> str:
        return self.__project_name

    def get_project_id(self) -> int:
        return self.__project_id

    def set_project_id(self, project_id: int):
        self.__project_id = project_id

    def get_svn_connector(self):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('get_svn_connector change_analyzer')

    def get_start_revision(self) -> int:
        return self.__start_revision

    def get_end_revision(self) -> int:
        return self.__end_revision

    def get_number_of_revisions(self) -> int:
        if self.__number_of_revisions == -1:
            self.__number_of_revisions = self.__git_connector.get_number_of_commits(None)
        return self.__number_of_revisions

    def get_number_of_code_revisions(self) -> int:
        return self.__number_of_code_revisions

    def increment_number_of_code_revisions(self):
        self.__number_of_code_revisions += 1

    def get_log_entry(self):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('get_log_entry change_analyzer')

    # def get_revision_analyzers(self) -> list[RevisionAnalyzer]:
    #     return self.__revision_analyzers

    def get_change_project(self) -> ChangeProject:
        return self.__change_project

    def build_svn_connection(self):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('build_svn_connector change_analyzer')

    def build_git_connector(self):
        self.__git_connector = GitConnector(self.__url + '/.git')
        self.__git_connector.connect()

    @multimethod
    def build_log_entries(self):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('build_log_entries change_analyzer')

    @multimethod
    def build_log_entries(self, start_revision: int, end_revision: int):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('build_log_entries change_analyzer')

    def build_log_and_analyze(self):
        # Not Implemented.
        # Why: SVN
        raise NotImplementedError('build_log_and_analyze change_analyzer')

    # Not Implemented.
    # Why: SVN
    # def analyze(self):
    #     self.__analyze(self.__start_revision, self.__end_revision)

    def analyze_git(self):
        self.__change_project = ChangeProject(self.__project_id, self.__project_name)
        self.__change_project.revisions = []
        dir: str = 'C:/CPatMinerAda/out' + '/' + self.__project_name
        # self.__analyze_git(self.__git_connector.get_commit('HEAD'))

        commits = self.__git_connector.log()

        self.__number_of_code_revisions = 0
        self.__number_of_revisions = 0
        self.__number_of_extracted_revisions = 0

        for commit in commits:
            #  TODO: check if  dir/ commit name .dat exists
            self.__analyze_git(commit)

    def __analyze_git(self, commit: Commit):
        self.__number_of_revisions += 1
        if self.__number_of_revisions % 1000 == 0:
            print('Analyzing revision: {} {} from projectName'
                  .format(self.__number_of_revisions, commit.name_rev, self.__number_of_revisions))
        revision_analyzer: RevisionAnalyzer = RevisionAnalyzer(self, commit)
        analyzed: bool = revision_analyzer.analyze_git()
        print('analyzed: {}'.format(analyzed))
        if analyzed:
            change_graphs: dict[str, dict[str, ChangeGraph]] = dict()
            for e in revision_analyzer.get_mapped_methods_m():
                change_graph: ChangeGraph = e.get_change_graph(self.__git_connector.get_repository(), commit)
                change_sizes: list[int] = change_graph.get_change_sizes()
                if 100 >= change_sizes[0] > 0 and 100 >= change_sizes[1] > 0 and change_sizes[0] + change_sizes[
                    1] >= 3:  # and change_graph.has_methods():
                    cgs: Optional[dict[str, ChangeGraph]] = change_graphs.get(e.get_change_file().get_path())
                    if cgs is None:
                        cgs = dict()
                        change_graphs[e.get_change_file().get_path()] = cgs
                    cgs['{},{},{},'.format(e.get_change_package().get_name(), e.get_simple_name(),
                                           e.get_parameter_types(), e._start_line)] = change_graph
                e.clean_for_stats()
            if len(change_graphs) > 0:
                # write change graphs to file
                raise NotImplementedError('pickle change_graphs and write to file')
                self.__number_of_extracted_revisions += 1

    # Not Implemented.
    # Why: SVN
    # def __analyze(self, start_revision: int, end_revision: int):
    #     for r in range(start_revision, end_revision + 1):
    #         ...


class RevisionAnalyzer:
    __change_analyzer: Optional[ChangeAnalyzer]
    __revision: int
    __commit: Commit

    __mapped_files_m: set[ChangeFile]
    __mapped_files_n: set[ChangeFile]
    __packages_m: set[ChangePackage]
    __packages_n: set[ChangePackage]
    __mapped_packages_m: set[ChangePackage]
    __mapped_packages_n: set[ChangePackage]
    __methods_m: set[ChangeMethod]
    __methods_n: set[ChangeMethod]
    __mapped_methods_m: set[ChangeMethod]
    __mapped_methods_n: set[ChangeMethod]
    __fields_m: set[ChangeField]
    __fields_n: set[ChangeField]
    __mapped_fields_m: set[ChangeField]
    __mapped_fields_n: set[ChangeField]
    __inits_m: set[ChangeInitializer]
    __inits_n: set[ChangeInitializer]
    __mapped_inits_m: set[ChangeInitializer]
    __mapped_inits_n: set[ChangeInitializer]

    change_revision: ChangeRevision

    @multimethod
    def __init__(self):
        self.__mapped_files_m = set()
        self.__mapped_files_n = set()
        self.__packages_m = set()
        self.__packages_n = set()
        self.__mapped_packages_m = set()
        self.__mapped_packages_n = set()
        self.__methods_m = set()
        self.__methods_n = set()
        self.__mapped_methods_m = set()
        self.__mapped_methods_n = set()
        self.__fields_m = set()
        self.__fields_n = set()
        self.__mapped_fields_m = set()
        self.__mapped_fields_n = set()
        self.__inits_m = set()
        self.__inits_n = set()
        self.__mapped_inits_m = set()
        self.__mapped_inits_n = set()

    @multimethod
    def __init__(self, change_analyzer: ChangeAnalyzer, revision: int):
        self.__init__()
        self.__change_analyzer = change_analyzer
        self.__revision = revision

    @multimethod
    def __init__(self, change_analyzer: ChangeAnalyzer, commit: Commit):
        self.__init__()
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

    def get_mapped_packages_m(self) -> set[ChangePackage]:
        return self.__mapped_packages_m

    def get_mapped_packages_n(self) -> set[ChangePackage]:
        return self.__mapped_packages_n

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

    def analyze(self):
        raise NotImplementedError('Not implementing SVN methods!')

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
                        print(old_content)
                    except:
                        warn('Error reading file: ' + diff.a_blob.path)
                        continue
                    try:
                        new_content = diff.b_blob.data_stream.read().decode('ISO-8859-2')
                    except:
                        warn('Error reading file: ' + diff.b_blob.path)
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
        self.__map_packages()
        self.__map_methods()
        return True

    def __map_bodies(self):
        for file_m in self.__mapped_files_m:
            file_n: ChangeFile = file_m.get_mapped_file()
            file_m.compute_similarity(file_n)  # <--- TODO

    def __map_packages(self):
        for file_m in self.__mapped_files_m:
            file_n: ChangeFile = file_m.get_mapped_file()
            file_m.compute_similarity(file_n)
            for change_package in file_m.get_packages():
                if change_package.get_mapped_package() is not None:
                    self.__mapped_packages_m.add(change_package)
                    self.__mapped_packages_n.add(change_package.get_mapped_package())
                    stack_packages: deque = deque()
                    stack_packages.append(change_package)
                    while len(stack_packages) > 0:
                        stack_package: ChangePackage = stack_packages.pop()
                        stack_package.compute_similarity(stack_package.get_mapped_package(), False)
                        for inner_change_package in stack_package.get_inner_packages(False):
                            if inner_change_package.get_mapped_package() is not None:
                                self.__mapped_packages_m.add(inner_change_package)
                                self.__mapped_packages_n.add(inner_change_package.get_mapped_package())
                                stack_packages.append(inner_change_package)
                else:
                    self.__packages_m.add(change_package)
            for change_package in file_n.get_packages():
                if change_package.get_mapped_package() is not None:
                    self.__mapped_packages_n.add(change_package)
                else:
                    self.__packages_n.add(change_package)
                for inner_change_package in change_package.get_inner_packages(True):
                    if inner_change_package.get_mapped_package is not None:
                        self.__mapped_packages_m.add(inner_change_package)
                    else:
                        self.__packages_n.add(inner_change_package)
        ChangePackage.map_all(self.__packages_m, self.__packages_n, self.__mapped_packages_m, self.__mapped_packages_n)
        self.__clear_package_body_mapping()
        for change_package in self.__mapped_packages_m:
            change_package.compute_similarity(change_package.get_mapped_package(), True)
            for change_method in change_package.get_methods():
                if change_method.get_mapped_method() is not None:
                    self.__mapped_methods_m.add(change_method)
                else:
                    self.__methods_m.add(change_method)
            for change_field in change_package.get_fields():
                if change_field.get_mapped_field() is not None:
                    self.__mapped_fields_m.add(change_field)
                else:
                    self.__fields_m.add(change_field)
            for change_initializer in change_package.get_initializers():
                if change_initializer.get_mapped_initializer() is not None:
                    self.__mapped_inits_m.add(change_initializer)
                else:
                    self.__inits_m.add(change_initializer)
        for change_package in self.__mapped_packages_n:
            for change_method in change_package.get_methods():
                if change_method.get_mapped_method() is not None:
                    self.__mapped_methods_n.add(change_method)
                else:
                    self.__methods_n.add(change_method)
            for change_field in change_package.get_fields():
                if change_field.get_mapped_field() is not None:
                    self.__mapped_fields_n.add(change_field)
                else:
                    self.__fields_n.add(change_field)
            for change_initializer in change_package.get_initializers():
                if change_initializer.get_mapped_initializer() is not None:
                    self.__mapped_inits_n.add(change_initializer)
                else:
                    self.__inits_n.add(change_initializer)
        for change_package in self.__packages_m:
            for change_method in change_package.get_methods():
                self.__methods_m.add(change_method)
            for change_field in change_package.get_fields():
                self.__fields_m.add(change_field)
            for change_initializer in change_package.get_initializers():
                self.__inits_m.add(change_initializer)

    def __clear_package_body_mapping(self):
        for change_package in self.__packages_m:
            change_package.clear_body_mapping()
        for change_package in self.__packages_n:
            change_package.clear_body_mapping()
        for change_package in self.__mapped_packages_m:
            change_package.clear_body_mapping()
        for change_package in self.__mapped_packages_n:
            change_package.clear_body_mapping()

    def __map_methods(self):
        ChangeMethod.map_all(self.__methods_m, self.__methods_n, self.__mapped_methods_m, self.__mapped_methods_n,
                             False)

    def __derive_changes(self):
        #  derive_field_changes()
        self.__derive_method_changes()
        #  derive_init_changes()
        #  derive_enum_constant_changes()
        #  derive_package_changes()

    def __derive_method_changes(self):
        mapped_methods_m_copy: set[ChangeMethod] = self.__mapped_methods_m.copy()
        print('__derive_method_changes')
        print(self.__mapped_methods_m)
        for change_method_m in mapped_methods_m_copy:
            change_method_m.derive_changes()
            if change_method_m.get_change_type() == Type.UNCHANGED:
                self.__mapped_methods_m.remove(change_method_m)
                self.__mapped_methods_n.remove(change_method_m.get_mapped_method())


class Type(Enum):
    UNCHANGED = 0
    DELETED = 1
    ADDED = 2
    MODIFIED = 3
    MODIFIED_MODIFIERS = 4
    MODIFIED_NAME = 5
    MODIFIED_BODY = 6


class ChangeEntity:
    _threshold_distance: int = 20

    _start_line: int
    __change_type: Type = Type.UNCHANGED
    _vector: Optional[dict[int, int]]
    _vector_length: int

    number_of_locs: int
    number_of_non_comment_locs: int
    number_of_ast_nodes: int
    number_of_change_locs: int
    number_of_change_ast_nodes: int
    number_of_change_trees: int

    def __init__(self):
        self._start_line = -1
        self.__change_type = Type.UNCHANGED
        self._vector_length = 0
        self.number_of_locs = 0
        self.number_of_non_comment_locs = 0
        self.number_of_ast_nodes = 0
        self.number_of_change_locs = 0
        self.number_of_change_ast_nodes = 0
        self.number_of_change_trees = 0

    def get_change_type(self) -> Type:
        return self.__change_type

    def set_change_type(self, change_type: Type):
        self.__change_type = change_type

    def _compute_vector_length(self):
        self._vector_length = 0
        for value in self._vector.values():
            self._vector_length += value

    def _get_vector(self) -> dict[int, int]:
        return self._vector

    def _get_vector_length(self) -> int:
        return self._vector_length

    def get_number_of_locs(self) -> int:
        return self.number_of_locs

    def get_number_of_non_comment_locs(self) -> int:
        return self.number_of_non_comment_locs

    def get_number_of_ast_nodes(self) -> int:
        return self.number_of_ast_nodes

    def get_number_of_change_locs(self) -> int:
        return self.number_of_change_locs

    def get_number_of_change_ast_nodes(self) -> int:
        return self.number_of_change_ast_nodes

    def get_number_of_change_trees(self) -> int:
        return self.number_of_change_trees

    def compute_vector_similarity(self, other: ChangeEntity) -> float:
        v1: dict[int, int] = self._get_vector().copy()
        v2: dict[int, int] = other._get_vector().copy()
        keys: set[int] = set(v1.keys()).intersection(set(v2.keys()))

        common_size: int = 0
        for key in keys:
            common_size += min(v1[key], v2[key])
        return common_size * 2.0 / (self._get_vector_length() + other._get_vector_length())

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_change_file(self) -> ChangeEntity:
        pass

    @abstractmethod
    def get_mapped_entity(self) -> Optional[ChangeEntity]:
        return None
        # if isinstance(self, ChangePackage):
        #     return self.get_mapped_package()
        # if isinstance(self, ChangeField):
        #     return self.get_mapped_field()
        # if isinstance(self, ChangeMethod):
        #     return self.get_mapped_method()
        # return None

    @abstractmethod
    def get_qualifier_name(self) -> str:
        pass

    @abstractmethod
    def get_change_package(self) -> ChangeEntity:
        pass

    def clean_for_stats(self):
        if self._vector is not None:
            self._vector.clear()
            self._vector = None


class ChangePackage(ChangeEntity):
    threshold_similarity: float = 0.75
    __change_file: ChangeFile
    __modifiers: int
    __annotation: str = ''
    __simple_name: str
    __declaration: PackageBody
    __parent_package: Optional[PackageBody]

    __mapped_package: ChangePackage
    __outer_package: Optional[ChangePackage]
    __inner_packages: list[ChangePackage]
    __fields: list[ChangeField]
    __methods: list[ChangeMethod]
    __initializers: list[ChangeInitializer]

    @multimethod
    def __init__(self):
        super().__init__()
        self.__inner_packages = []
        self.__fields = []
        self.__methods = []
        self.__initializers = []

    @multimethod
    def __init__(self, change_file: ChangeFile, package: PackageBody, outer_package: Optional[ChangePackage]):
        self.__init__()
        self._start_line = package.sloc_range.start.line
        self.__change_file = change_file
        self.__outer_package = outer_package
        self.__modifiers = 0  # TODO: remove modifiers!
        self.__simple_name = package.f_package_name.f_name.text
        self._declaration = package

        #  TODO: parentpackage?
        self.__parent_package = None

        #  interface types doesn't seem appropriate here..

        #  TODO: fields?

        #  add methods:
        methods: list[SubpBody] = list(filter(lambda n: n.is_a(SubpBody), package.f_decls.f_decls))
        for method in methods:
            self.__methods.append(ChangeMethod(self, method))

        #  add inner packages:
        packages: list[PackageBody] = list(filter(lambda n: n.is_a(PackageBody), package.f_decls.f_decls))
        for package in packages:
            self.__inner_packages.append(ChangePackage(self.__change_file, package, self))

        #  TODO: initializers?

    @override
    def get_change_file(self) -> ChangeFile:
        return self.__change_file

    @override
    def get_change_package(self) -> ChangePackage:
        return self

    def get_modifiers(self) -> int:
        return self.__modifiers

    def get_annotation(self) -> str:
        return self.__annotation

    def get_simple_name(self) -> str:
        return self.__simple_name

    def get_name(self) -> str:
        return self.__simple_name

    @override
    def get_qualifier_name(self) -> str:
        return self.__change_file.get_path() + '.' + self.__simple_name

    def get_full_qualifier_name(self) -> str:
        return self.get_qualifier_name

    def get_declaration(self):
        raise NotImplementedError('No Usage.')

    @override
    def get_mapped_entity(self) -> ChangePackage:
        return self.get_mapped_package()

    def get_mapped_package(self) -> ChangePackage:
        return self.__mapped_package

    def set_mapped_package(self, mapped_package: ChangePackage):
        self.__mapped_package = mapped_package

    def get_inner_packages(self, recursive: bool) -> list[ChangePackage]:
        packages: list[ChangePackage] = self.__inner_packages.copy()
        if recursive:
            for inner_change_package in self.__inner_packages:
                packages.extend(inner_change_package.get_inner_packages(True))
        return packages

    def get_inner_methods(self, recursive: bool) -> list[ChangeMethod]:
        raise NotImplementedError

    def get_fields(self) -> list[ChangeField]:
        return self.__fields

    def get_methods(self) -> list[ChangeMethod]:
        return self.__methods

    def get_initializers(self) -> list[ChangeInitializer]:
        return self.__initializers

    def get_field_types(self) -> dict[str, str]:
        raise NotImplementedError('No Usage.')

    def compute_similarity(self, other: ChangePackage, in_mapped: bool) -> float:
        common_size: float = 0.0
        total_size: float = 0.0
        methods_m: set[ChangeMethod] = set(self.get_methods())
        methods_n: set[ChangeMethod] = set(other.get_methods())
        mapped_methods_m: set[ChangeMethod] = set()
        mapped_methods_n: set[ChangeMethod] = set()
        fields_m: set[ChangeField] = set(self.get_fields())
        fields_n: set[ChangeField] = set(other.get_fields())
        mapped_fields_m: set[ChangeField] = set()
        mapped_fields_n: set[ChangeField] = set()
        initializers_m: set[ChangeInitializer] = set(self.get_initializers())
        initializers_n: set[ChangeInitializer] = set(other.get_initializers())
        mapped_initializers_m: set[ChangeInitializer] = set()
        mapped_initializers_n: set[ChangeInitializer] = set()

        # TODO: type
        size = ChangeMethod.map_all(methods_m, methods_n, mapped_methods_m, mapped_methods_n, in_mapped)
        common_size += size[0]
        total_size += size[1]

        size = ChangeField.map_all(fields_m, fields_n, mapped_fields_m, mapped_fields_n)
        common_size += size[0]
        total_size += size[1]

        # temp solution:
        if initializers_m:
            size = ChangeInitializer.map_all(initializers_m, initializers_n, mapped_initializers_m, mapped_initializers_n)
            common_size += size[0]
            total_size += size[1]
        else:
            common_size += 1.0
            total_size += 1.0

        # map inner packages?
        mapped_inners_m: set[ChangePackage] = set()
        mapped_inners_n: set[ChangePackage] = set()
        self.map_all(set(self.__inner_packages), set(other.get_inner_packages(False)), mapped_inners_m, mapped_inners_n)
        common_size += len(mapped_inners_m)
        total_size += len(mapped_inners_m)

        return common_size / total_size

    @staticmethod
    def set_map(package_m: ChangePackage, package_n: ChangePackage):
        package_m.set_mapped_package(package_n)
        package_n.set_mapped_package(package_m)

    @staticmethod
    def map(packages_m: set[ChangePackage], packages_n: set[ChangePackage],
            mapped_packages_m: set[ChangePackage], mapped_packages_n: set[ChangePackage]):
        pairs_of_methods1: dict[ChangePackage, set[Pair]] = dict()
        pairs_of_methods2: dict[ChangePackage, set[Pair]] = dict()
        pairs: list[Pair] = []
        for change_package_m in packages_m:
            pairs1: set[Pair] = set()
            for change_package_n in packages_n:
                similarity: float = change_package_m.compute_similarity(change_package_n, False)
                if similarity >= ChangePackage.threshold_similarity:
                    pair: Pair = Pair(change_package_m, change_package_n, similarity)
                    pairs1.add(pair)
                    pairs2: set[pair] = pairs_of_methods2.get(change_package_n, set())
                    pairs2.add(pair)
                    pairs_of_methods2[change_package_n] = pairs2
                    pairs.append(pair)
            pairs_of_methods1[change_package_m] = pairs1
        pairs.sort(reverse=True)
        while pairs:
            pair: Pair = pairs[0]
            change_package_m: ChangePackage = cast(ChangePackage, pair.get_object1())
            change_package_n: ChangePackage = cast(ChangePackage, pair.get_object2())
            ChangePackage.set_map(change_package_m, change_package_n)
            mapped_packages_m.add(change_package_m)
            mapped_packages_n.add(change_package_n)
            for p in pairs_of_methods1[change_package_m]:
                if p in pairs:
                    pairs.remove(p)
            for p in pairs_of_methods2[change_package_n]:
                if p in pairs:
                    pairs.remove(p)

    @staticmethod
    def map_all(packages_m: set[ChangePackage], packages_n: set[ChangePackage],
                mapped_packages_m: set[ChangePackage], mapped_packages_n: set[ChangePackage]):
        package_with_name_m: dict[str, ChangePackage] = dict()
        package_with_name_n: dict[str, ChangePackage] = dict()
        for change_package in packages_m:
            package_with_name_m[change_package.get_simple_name()] = change_package
        for change_package in packages_n:
            package_with_name_n[change_package.get_simple_name()] = change_package
        intersection_names: set[str] = set(package_with_name_m.keys()).intersection(set(package_with_name_n.keys()))
        for name in intersection_names:
            change_package_m: ChangePackage = package_with_name_m[name]
            change_package_n: ChangePackage = package_with_name_n[name]
            ChangePackage.set_map(change_package_m, change_package_n)
            mapped_packages_m.add(change_package_m)
            mapped_packages_n.add(change_package_n)
            packages_m.discard(change_package_m)
            packages_n.discard(change_package_n)

        # map other packages
        if packages_m and packages_n:
            temporary_mapped_packages_m: set[ChangePackage] = set()
            temporary_mapped_packages_n: set[ChangePackage] = set()
            ChangePackage.map(packages_m, packages_n, temporary_mapped_packages_m, temporary_mapped_packages_n)
            mapped_packages_m.update(temporary_mapped_packages_m)
            mapped_packages_n.update(temporary_mapped_packages_n)
            packages_m.difference_update(temporary_mapped_packages_m)
            packages_n.difference_update(temporary_mapped_packages_n)

    def derive_changes(self):
        if self.__mapped_package is None:
            return
        change_package_n: ChangePackage = self.__mapped_package
        same: bool = self.__simple_name == change_package_n.get_simple_name() \
                     and self.__modifiers == change_package_n.__modifiers \
                     and self.__annotation == change_package_n.__annotation
        # and self.__super_package_names == change_package_n.__super_package_names
        if same:
            for change_field in self.get_fields():
                if change_field.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        if same:
            for change_field in change_package_n.get_fields():
                if change_field.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        if same:
            for change_method in self.get_methods():
                if change_method.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        if same:
            for change_method in change_package_n.get_methods():
                if change_method.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        if same:
            for change_initializer in self.get_initializers():
                if change_initializer.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        if same:
            for change_initializer in change_package_n.get_initializers():
                if change_initializer.get_change_type() != Type.UNCHANGED:
                    same = False
                    break
        # TODO: inner_packages? skipped for now.
        if not same:
            self.set_change_type(Type.MODIFIED)
            change_package_n.set_change_type(Type.MODIFIED)

    @multimethod
    def print_changes(self, stream):
        raise NotImplementedError

    @multimethod
    def print_changes(self, stream, l):
        raise NotImplementedError

    def has_changed_name(self) -> bool:
        raise NotImplementedError('No Usage.')

    def __str__(self) -> str:
        return self.get_name()

    def clear_body_mapping(self):
        for change_method in self.__methods:
            change_method.set_mapped_method(None)
        for change_field in self.__fields:
            change_field.set_mapped_field(None)
        for change_initializer in self.__initializers:
            change_initializer.set_mapped_initializer(None)


class ChangeField(ChangeEntity):
    __threshold_similarity: float = 0.75

    __change_package: ChangePackage
    __modifiers: int
    __string_modifiers: set[str]
    __annotation: str = ''
    __name: str
    __type: str
    __initializer: Expr
    __mapped_field: ChangeField
    __types: set[str]
    __fields: set[str]
    __literals: set[str]

    def __init__(self, change_package: ChangePackage, field, type: str, object_declaration: ObjectDecl):
        super().__init__()
        self.__string_modifiers = set()
        self.__literals = set()
        self._start_line = object_declaration.sloc_range.start.line
        self.__change_package = change_package
        self._compute_vector_length()
        # TODO: implement
        raise NotImplementedError

    def get_modifiers(self) -> int:
        return self.__modifiers

    def get_string_modifiers(self) -> set[str]:
        return self.__string_modifiers

    def get_annotation(self) -> str:
        return self.__annotation

    @override
    def get_name(self) -> str:
        return self.__name

    @override
    def get_qualifier_name(self) -> str:
        return self.__change_package.get_simple_name() + '.' + self.__name

    def get_full_qualifier_name(self) -> str:
        return self.get_change_package().get_full_qualifier_name() + '.' + self.__name

    def get_type(self) -> str:
        return self.__type

    def get_initializer(self) -> Expr:
        return self.__initializer

    def get_mapped_field(self) -> ChangeField:
        return self.__mapped_field

    def set_mapped_field(self, mapped_field: Optional[ChangeField]):
        self.__mapped_field = mapped_field

    def get_types(self) -> set[str]:
        return self.__types

    def get_fields(self) -> set[str]:
        return self.__fields

    def get_literals(self) -> set[str]:
        return self.__literals

    @override
    def get_change_file(self) -> ChangeFile:
        return self.__change_package.get_change_file()

    @override
    def get_change_package(self) -> ChangePackage:
        return self.__change_package

    @override
    def get_mapped_entity(self) -> Optional[ChangeEntity]:
        return self.get_mapped_field()

    def compute_similarity(self, other: ChangeField) -> list[float]:
        similarity: list[float] = [0, 0, 0, 0]
        sequence1: list[str] = string_processor.serialize(text=self.__type)
        sequence2: list[str] = string_processor.serialize(other.__type)
        lcs_m: list[int] = []
        lcs_n: list[int] = []
        string_processor.do_lcs(sequence1, sequence2, 0, 0, lcs_m, lcs_n)
        similarity_type: float = len(lcs_m) * 2.0 / (len(sequence1) + len(sequence2))

        sequence1 = string_processor.serialize(text=self.__name)
        sequence2 = string_processor.serialize(other.__name)
        lcs_m = []
        lcs_n = []
        string_processor.do_lcs(sequence1, sequence2, 0, 0, lcs_m, lcs_n)
        similarity_name: float = len(lcs_m) * 2.0 / (len(sequence1) + len(sequence2))
        signature: float = (similarity_type + 2.0 * similarity_name) / 3.0
        body: float = 1.0
        if len(self._vector) > 0 or len(other._get_vector()) > 0:
            body = self.compute_vector_similarity(other)
        similarity[0] = signature
        similarity[1] = body
        similarity[2] = signature + body
        similarity[3] = round(signature * 10.0) + signature + body

        return similarity

    @staticmethod
    def set_map(field_m: ChangeField, field_n: ChangeField):
        field_m.set_mapped_field(field_n)
        field_n.set_mapped_field(field_m)

    @staticmethod
    def map(fields_m: set[ChangeField], fields_n: set[ChangeField], mapped_fields_m: set[ChangeField],
            mapped_fields_n: set[ChangeField]):
        pairs_of_methods1: dict[ChangeField, set[Pair]] = {}
        pairs_of_methods2: dict[ChangeField, set[Pair]] = {}
        pairs: list[Pair] = []
        for change_field_m in fields_m:
            pairs1: set[Pair] = set()
            for change_field_n in fields_n:
                similarity: list[float] = change_field_m.compute_similarity(change_field_n)
                if similarity[0] >= ChangeField.__threshold_similarity \
                        and similarity[1] >= ChangeField.__threshold_similarity:
                    pair: Pair = Pair(change_field_m, change_field_n, similarity[3])
                    pairs1.add(pair)
                    pairs2: set[Pair] = pairs_of_methods2.get(change_field_n)
                    if pairs2 is None:
                        pairs2 = set()
                    pairs2.add(pair)
                    pairs_of_methods2[change_field_n] = pairs2
                    pairs.append(pair)
            pairs_of_methods1[change_field_m] = pairs1
        pairs.sort(reverse=True)
        while pairs:
            pair: Pair = pairs[0]
            change_field_m: ChangeField = cast(ChangeField, pair.get_object1())
            change_field_n: ChangeField = cast(ChangeField, pair.get_object2())
            ChangeField.set_map(change_field_m, change_field_n)
            mapped_fields_m.add(change_field_m)
            mapped_fields_n.add(change_field_n)
            for p in pairs_of_methods1[change_field_m]:
                if p in pairs:
                    pairs.remove(p)
            for p in pairs_of_methods2[change_field_n]:
                if p in pairs:
                    pairs.remove(p)

    @staticmethod
    def map_all(fields_m: set[ChangeField], fields_n: set[ChangeField], mapped_fields_m: set[ChangeField],
                mapped_fields_n: set[ChangeField]) -> tuple[float, float]:
        common_size: int = 0
        total_size: int = 0
        field_with_name_m: dict[str, ChangeField] = {}
        field_with_name_n: dict[str, ChangeField] = {}
        for change_field in fields_m:
            field_with_name_m[change_field.get_name()] = change_field
        for change_field in fields_n:
            field_with_name_n[change_field.get_name()] = change_field
        intersection_names: set[str] = set(field_with_name_m.keys()).intersection(set(field_with_name_n.keys()))
        for name in intersection_names:
            change_field_m: ChangeField = field_with_name_m[name]
            change_field_n: ChangeField = field_with_name_n[name]
            ChangeField.set_map(change_field_m, change_field_n)
            mapped_fields_m.add(change_field_m)
            mapped_fields_n.add(change_field_n)
            fields_m.remove(change_field_m)
            fields_n.remove(change_field_n)
            common_size += 1
            total_size += 1

        # map other fields
        ChangeField.map(fields_m, fields_n, mapped_fields_m, mapped_fields_n)
        common_size += len(mapped_fields_m)
        total_size += len(mapped_fields_m)

        return common_size, total_size

    def print_changes(self, ps):
        # TODO: print stream
        if self.get_change_type() != Type.UNCHANGED:
            mapped_field_name: str = 'None'
            if self.__mapped_field is not None:
                mapped_field_name = self.__mapped_field.get_name()
            print('\t\t\tField: {} ---> {}'.format(self.get_name(), mapped_field_name))

    def __str__(self):
        return self.get_qualifier_name()


class ChangeFile(ChangeEntity):
    MAX_SIZE = 500000
    __revision_analyzer: RevisionAnalyzer
    __path: str
    __simple_name: str
    __mapped_file: ChangeFile
    __compilation_unit = None  # TODO
    __context: AnalysisContext = None
    __unit: AnalysisUnit = None
    __packages: set[ChangePackage]
    main_procedure: Optional[ChangeMethod]

    @multimethod
    def __init__(self):
        super().__init__()
        self.__packages = set()

    @multimethod
    def __init__(self, revision_analyzer: RevisionAnalyzer, path: str, content: str):
        self.__init__()
        self._start_line = 0
        self.__revision_analyzer = revision_analyzer
        self.__path = path
        self.__simple_name = FileIO.get_simple_file_name(path)
        self.__context = AnalysisContext()
        self.__unit = self.__context.get_from_buffer(path, content)
        self.main_procedure = None
        if self.__unit.root:
            vector_visitor: VectorVisitor = VectorVisitor()
            accept(self.__unit.root, vector_visitor)
            package_body: Optional[PackageBody] = self.__unit.root.find(lambda n: n.is_a(PackageBody))
            if package_body:
                self.__packages.add(ChangePackage(self, package_body, None))
            else:
                main_procedure: Optional[SubpBody] = self.__unit.root.find(lambda n: n.is_a(SubpBody))
                if main_procedure:
                    self.main_procedure: ChangeMethod = ChangeMethod(self, main_procedure)

    def get_revision_analyzer(self) -> RevisionAnalyzer:
        return self.__revision_analyzer

    def get_path(self) -> str:
        return self.__path

    def get_simple_name(self) -> str:
        return self.__simple_name

    @override
    def get_name(self) -> str:
        return self.get_simple_name()

    def get_packages(self) -> set[ChangePackage]:
        return self.__packages

    def get_mapped_file(self) -> ChangeFile:
        return self.__mapped_file

    def set_mapped_file(self, mapped_file: ChangeFile):
        self.__mapped_file = mapped_file

    @override
    def get_change_file(self) -> ChangeFile:
        return self

    # @override
    def get_change_package(self) -> ChangePackage:
        return None

    def compute_similarity(self, other: ChangeFile):
        packages_m: set[ChangePackage] = self.get_packages().copy()
        packages_n: set[ChangePackage] = other.get_packages().copy()
        mapped_packages_m: set[ChangePackage] = set()
        mapped_packages_n: set[ChangePackage] = set()

        package_m: Optional[ChangePackage] = None
        package_n: Optional[ChangePackage] = None
        for change_package in packages_m:
            # TODO: improve name comparison for package name and file name
            if change_package.get_simple_name().lower() == self.get_simple_name().lower():
                package_m = change_package
        for change_package in packages_n:
            if change_package.get_simple_name().lower() == other.get_simple_name().lower():
                package_n = change_package
        if package_m is not None and package_n is not None:
            similarity: float = package_m.compute_similarity(package_n, False)
            if similarity > ChangePackage.threshold_similarity:
                ChangePackage.set_map(package_m, package_n)
                mapped_packages_m.add(package_m)
                mapped_packages_n.add(package_n)
                packages_m.discard(package_m)
                packages_n.discard(package_n)
        ChangePackage.map_all(packages_m, packages_n, mapped_packages_m, mapped_packages_n)

    @multimethod
    def print_changes(self, ps):
        raise NotImplementedError

    @multimethod
    def print_changes(self, ps, packages):
        raise NotImplementedError

    @override
    def __str__(self) -> str:
        return self.__simple_name

    @override
    def get_qualifier_name(self) -> str:
        return self.__path


class ChangeGraph:
    __nodes: set[ChangeNode]

    def __init__(self, graph: PDGGraph):
        self.__nodes = set()
        changed_nodes: set[PDGNode] = graph.get_changed_nodes()
        if len(changed_nodes) == 0:
            return
        node_dict: dict[PDGNode, ChangeNode] = dict()
        for node in changed_nodes:
            change_node = ChangeNode(node)
            node_dict[node] = change_node
            self.__nodes.add(change_node)
        for node in changed_nodes:
            change_node = node_dict[node]
            for edge in node.get_in_edges():
                if edge.get_source() in changed_nodes:
                    ChangeEdge(node_dict[edge.get_source()], change_node, edge)

    def get_nodes(self) -> set[ChangeNode]:
        return self.__nodes

    def is_multi_graph(self) -> bool:
        for node in self.__nodes:
            s: set[ChangeNode] = set()
            for edge in node.out_edges:
                if edge.target in s:
                    return False
                s.add(edge.target)
        return True

    def has_methods(self) -> bool:
        for node in self.__nodes:
            if node.ast_node_type == node_type(CallStmt):
                return True
        return False

    def get_change_sizes(self) -> list[int]:
        sizes: list[int] = [0, 0]
        for node in self.__nodes:
            sizes[node.version] += 1
        return sizes


class ChangeInitializer:
    pass


class ChangeMethod(ChangeEntity):
    __separator_parameter: str = '#'
    __threshold_signature_similarity: float = 0.625
    __threshold_body_similarity: float = 0.75
    __maximum_number_of_statements: int = 1000

    __change_package: Optional[ChangePackage]
    __modifiers: int
    __annotation: Optional[str] = ''
    __name: str
    __simple_name: str
    __number_of_parameters: int
    __return_type: Optional[str]
    __declaration: Optional[SubpBody]
    __mapped_method: Optional[ChangeMethod] = None
    __parameter_types: str
    __literals: Optional[set[str]]
    __local_var_locs: dict[Identifier, set[Identifier]] = dict()  # TODO: probably unused?

    @multimethod
    def __init__(self):
        super().__init__()
        self.__literals = set()

    @multimethod
    def __init__(self, change_file: ChangeFile, method: SubpBody):
        self.__init__()
        self._start_line = method.sloc_range.start.line
        self._change_file = change_file
        self.__simple_name = method.f_subp_spec.f_subp_name.f_name.text
        self.__number_of_parameters = len(method.f_subp_spec.p_params)
        self.__name = '{}({})'.format(self.__simple_name, self.__number_of_parameters)
        self.__declaration = method
        self.__parameter_types = self.__separator_parameter
        for parameter in method.f_subp_spec.p_params:
            print(parameter)
            raise NotImplementedError
        if method.f_subp_spec.f_subp_kind.is_a(SubpKindFunction):
            self.__return_type = method.f_subp_spec.f_subp_returns.text
        self._vector = VectorVisitor.property_vector[method].copy()
        VectorVisitor.property_vector[method] = None
        self._compute_vector_length()

    @multimethod
    def __init__(self, change_package: ChangePackage, method: SubpBody):
        self.__init__()
        self._start_line = method.sloc_range.start.line
        self.__change_package = change_package
        self.__modifiers = 0  # TODO: remove modifiers
        self.__simple_name = method.f_subp_spec.f_subp_name.f_name.text
        self.__number_of_parameters = len(method.f_subp_spec.p_params)
        self.__name = '{}({})'.format(self.__simple_name, self.__number_of_parameters)
        self.__declaration = method
        self.__parameter_types = self.__separator_parameter
        for parameter in method.f_subp_spec.p_params:
            self.__parameter_types += parameter.f_type_expr.text
        if method.f_subp_spec.f_subp_kind.is_a(SubpKindFunction):
            self.__return_type = method.f_subp_spec.p_returns.text
        else:
            self.__return_type = ''
        self._vector = VectorVisitor.property_vector[method].copy()
        VectorVisitor.property_vector[method] = None
        self._compute_vector_length()

    def get_modifiers(self) -> int:
        raise NotImplementedError('No usage.')

    def get_annotations(self) -> str:
        raise NotImplementedError('No usage.')

    @override
    def get_name(self) -> str:
        return self.__name

    def get_simple_name(self) -> str:
        return self.__simple_name

    @override
    def get_qualifier_name(self) -> str:
        return self.__change_package.get_simple_name() + '.' + self.__name

    def get_number_of_parameters(self) -> int:
        return self.__number_of_parameters

    def get_parameter_types(self) -> str:
        return self.__parameter_types

    def get_return_type(self) -> str:
        return self.__return_type

    def get_full_name(self) -> str:
        return self.__simple_name + self.__parameter_types

    def get_full_qualifier_name(self) -> str:
        raise NotImplementedError('No usage.')

    def get_declaration(self):
        raise NotImplementedError('No usage.')

    @override
    def get_mapped_entity(self) -> Optional[ChangeMethod]:
        return self.get_mapped_method()

    def get_mapped_method(self) -> ChangeMethod:
        return self.__mapped_method

    def set_mapped_method(self, mapped_method: Optional[ChangeMethod]):
        self.__mapped_method = mapped_method

    @override
    def get_change_file(self) -> ChangeFile:
        return self.__change_package.get_change_file()

    @override
    def get_change_package(self) -> ChangePackage:
        return self.__change_package

    def get_local_var_locs(self) -> dict[libadalang.Identifier, set[libadalang.Identifier]]:
        return self.__local_var_locs

    @staticmethod
    def set_map(method_m: ChangeMethod, method_n: ChangeMethod):
        method_m.set_mapped_method(method_n)
        method_n.set_mapped_method(method_m)

    @staticmethod
    def map(methods_m: set[ChangeMethod],
            methods_n: set[ChangeMethod],
            mapped_methods_m: set[ChangeMethod],
            mapped_methods_n: set[ChangeMethod],
            in_mapped_packages: bool):
        pairs_of_methods1: dict[ChangeMethod, set[Pair]] = dict()
        pairs_of_methods2: dict[ChangeMethod, set[Pair]] = dict()
        pairs: list[Pair] = []
        for change_method_m in methods_m:
            pairs1: set[Pair] = set()
            for change_method_n in methods_n:
                similarity: list[float] = change_method_m.compute_similarity(change_method_n, in_mapped_packages)
                is_mapped: bool = (in_mapped_packages
                                   and similarity[0] >= ChangeMethod.__threshold_signature_similarity) \
                                  or (similarity[0] > 0 and similarity[1] == 1.0) \
                                  or (similarity[0] >= ChangeMethod.__threshold_signature_similarity
                                      and similarity[1] >= ChangeMethod.__threshold_body_similarity)
                if is_mapped:
                    pair: Pair = Pair(change_method_m, change_method_n, similarity[3])
                    pairs1.add(pair)
                    pairs2: set[Pair] = pairs_of_methods2.get(change_method_n, set())
                    pairs2.add(pair)
                    pairs_of_methods2[change_method_n] = pairs2
                    pairs.append(pair)
            pairs_of_methods1[change_method_m] = pairs1
        pairs.sort(reverse=True)
        while pairs:
            pair: Pair = pairs[0]
            change_method_m: ChangeMethod = cast(ChangeMethod, pair.get_object1())
            change_method_n: ChangeMethod = cast(ChangeMethod, pair.get_object2())
            ChangeMethod.set_map(change_method_m, change_method_n)
            mapped_methods_m.add(change_method_m)
            mapped_methods_n.add(change_method_n)
            for p in pairs_of_methods1.get(cast(ChangeMethod, pair.get_object1())):
                if p in pairs:
                    pairs.remove(p)
            for p in pairs_of_methods2.get(cast(ChangeMethod, pair.get_object2())):
                if p in pairs:
                    pairs.remove(p)

    @override
    def _compute_vector_length(self):
        self._vector_length = 0
        for key in self._vector.keys():
            self._vector_length += self._vector.get(key)

    def compute_similarity(self, other: ChangeMethod, in_mapped_packages: bool):
        similarity: list[float] = [0.0, 0.0, 0.0, 0.0]
        signature: float = self.compute_name_similarity(other, in_mapped_packages)
        body: float = 1.0
        if len(self._vector) > 0 or len(other._get_vector()) > 0:
            body = self.compute_vector_similarity(other)
        similarity[0] = signature
        similarity[1] = body
        similarity[2] = signature + body
        similarity[3] = round(signature * 10.0) + signature + body

        return similarity

    def compute_name_similarity(self, other: ChangeMethod, in_mapped_packages: bool):
        signature: float = 0.0
        full_name1: str = self.get_full_name()
        full_name2: str = other.get_full_name()
        # this check is for constructors, which doesn't make sense in Ada.
        if (in_mapped_packages
                and self.__change_package.get_simple_name() != other.__change_package.get_simple_name()
                and self.__simple_name == self.__change_package.get_simple_name()
                and other.__simple_name == other.__change_package.get_simple_name()):
            full_name1 = 'package' + self.__parameter_types
            full_name2 = 'package' + other.__parameter_types
        # TODO: special case for getters and setters?
        if self.__simple_name == other.__simple_name:
            if full_name1 == full_name2:
                signature = 1.0
            else:
                seq_parameter_types1: list[str] = []
                seq_parameter_types2: list[str] = []
                if len(self.get_parameter_types()) > 1:
                    seq_parameter_types1: list[str] = self.get_parameter_types()[1:].split(self.__separator_parameter)
                if len(other.get_parameter_types()) > 1:
                    seq_parameter_types2: list[str] = other.get_parameter_types()[1:].split(self.__separator_parameter)
                lcs_m: list[int] = []
                lcs_n: list[int] = []
                do_lcs(seq_parameter_types1, seq_parameter_types2, 0, 0, lcs_m, lcs_n)
                signature = ((len(seq_parameter_types1) + len(seq_parameter_types2))
                             / max(len(seq_parameter_types1) * 1.0, len(seq_parameter_types2) * 2.0)
                             + len(lcs_m)
                             * 2.0
                             / (len(seq_parameter_types1) + len(seq_parameter_types2)) + 2.0) / 4.0
        else:
            seq1: list[str] = serialize(self.get_return_type())
            seq2: list[str] = serialize(other.get_return_type())
            lcs_m: list[int] = []
            lcs_n: list[int] = []
            do_lcs(seq1, seq2, 0, 0, lcs_m, lcs_n)
            similarity_return_type: float = len(lcs_m) * 2.0 / (len(seq1) + len(seq2))
            seq1 = serialize(full_name1)
            seq2 = serialize(full_name2)
            lcs_m = []
            lcs_n = []
            do_lcs(seq1, seq2, 0, 0, lcs_m, lcs_n)
            similarity_full_name: float = len(lcs_m) * 2.0 / (len(seq1) + len(seq2))
            signature = (similarity_return_type + 2.0 * similarity_full_name) / 3.0
        return signature

    @staticmethod
    def map_all(methods_m: set[ChangeMethod],
                methods_n: set[ChangeMethod],
                mapped_methods_m: set[ChangeMethod],
                mapped_methods_n: set[ChangeMethod],
                in_mapped_packages: bool) -> list[float]:
        size: list[float] = \
            [0, (len(methods_m) + len(methods_n) + len(mapped_methods_m) + len(mapped_methods_n)) / 2.0]
        #  map methods with same simple names and numbers of parameters
        methods_with_name_m: dict[str, set[ChangeMethod]] = {}
        methods_with_name_n: dict[str, set[ChangeMethod]] = {}
        for change_method_m in methods_m:
            name: str = change_method_m.get_name()
            change_method_set: set[ChangeMethod] = methods_with_name_m.get(name)
            if change_method_set is None:
                change_method_set = set()
            change_method_set.add(change_method_m)
            methods_with_name_m[name] = change_method_set
        for change_method_n in methods_n:
            name: str = change_method_n.get_name()
            change_method_set: set[ChangeMethod] = methods_with_name_n.get(name)
            if change_method_set is None:
                change_method_set = set()
            change_method_set.add(change_method_n)
            methods_with_name_n[name] = change_method_set
        intersection_names: set[str] = set(methods_with_name_m.keys()).intersection(set(methods_with_name_n.keys()))
        for name in intersection_names:
            temporary_mapped_methods_m: set[ChangeMethod] = set()
            temporary_mapped_methods_n: set[ChangeMethod] = set()
            ChangeMethod.map(methods_with_name_m.get(name),
                             methods_with_name_n.get(name),
                             temporary_mapped_methods_m,
                             temporary_mapped_methods_n,
                             in_mapped_packages)
            mapped_methods_m.update(temporary_mapped_methods_m)
            mapped_methods_n.update(temporary_mapped_methods_n)
            methods_m -= temporary_mapped_methods_m
            methods_n -= temporary_mapped_methods_n
            size[0] += len(temporary_mapped_methods_m)

        # map methods with same simple names
        methods_with_name_m.clear()
        methods_with_name_n.clear()
        for change_method in methods_m:
            name: str = change_method.get_simple_name()
            if name == change_method.get_change_package().get_simple_name():
                name = 'package'  # TODO
            change_method_set: set[ChangeMethod] = methods_with_name_m.get(name, None)
            if change_method_set is None:
                change_method_set = set()
            change_method_set.add(change_method)
            methods_with_name_m[name] = change_method_set
        for change_method in methods_n:
            name: str = change_method.get_simple_name()
            if name == change_method.get_change_package().get_simple_name():
                name = 'package'  # TODO
            change_method_set: set[ChangeMethod] = methods_with_name_n.get(name, None)
            if change_method_set is None:
                change_method_set = set()
            change_method_set.add(change_method)
            methods_with_name_n[name] = change_method_set
        intersection_names = set(methods_with_name_m.keys()).intersection(set(methods_with_name_n.keys()))
        for name in intersection_names:
            temporary_mapped_methods_m: set[ChangeMethod] = set()
            temporary_mapped_methods_n: set[ChangeMethod] = set()
            ChangeMethod.map(methods_with_name_m.get(name),
                             methods_with_name_n.get(name),
                             temporary_mapped_methods_m,
                             temporary_mapped_methods_n,
                             in_mapped_packages)
            mapped_methods_m.update(temporary_mapped_methods_m)
            mapped_methods_n.update(temporary_mapped_methods_n)
            methods_m -= temporary_mapped_methods_m
            methods_n -= temporary_mapped_methods_n
            size[0] += len(temporary_mapped_methods_m)
        # map other methods
        temporary_mapped_methods_m: set[ChangeMethod] = set()
        temporary_mapped_methods_n: set[ChangeMethod] = set()
        ChangeMethod.map(methods_m,
                         methods_n,
                         temporary_mapped_methods_m,
                         temporary_mapped_methods_n,
                         in_mapped_packages)
        mapped_methods_m.update(temporary_mapped_methods_m)
        mapped_methods_n.update(temporary_mapped_methods_n)
        methods_m -= temporary_mapped_methods_m
        methods_n -= temporary_mapped_methods_n
        size[0] += len(temporary_mapped_methods_m)

        return size

    def derive_changes(self):
        change_method_n: ChangeMethod = self.__mapped_method
        if match(self.__declaration, change_method_n.__declaration):
            return
        treed_mapper: TreedMapper = TreedMapper(self.__declaration, change_method_n.__declaration)
        treed_mapper.map(False)
        if treed_mapper.has_non_name_unmap():
            self.set_change_type(Type.MODIFIED)
            change_method_n.set_change_type(Type.MODIFIED)

    @override
    def clean_for_stats(self):
        super().clean_for_stats()
        self.__annotation = None
        self.__change_package = None
        self.__declaration = None
        self.__literals.clear()
        self.__literals = None
        if self.__local_var_locs is not None:
            self.__local_var_locs.clear()
            self.__local_var_locs = None
        self.__mapped_method = None

    def print_changes(self):
        # TODO?: printstream
        if self.get_change_type() != Type.UNCHANGED:
            mapped_method_string: str = 'None'
            if self.__mapped_method is not None:
                mapped_method_string = self.__mapped_method.get_full_name()
            print('\t\t\tMethod: {} ---> {}'.format(self.get_full_name(), mapped_method_string))

    def __str__(self):
        return self.get_qualifier_name()

    def get_change_graph(self, repository, commit):
        pdg1: PDGGraph = PDGGraph(self.__declaration,
                                  PDGBuildingContext(repository, commit, self.get_change_file().get_path(), False))
        pdg1.build_change_graph(0)
        pdg2: PDGGraph = PDGGraph(self.__mapped_method.__declaration, PDGBuildingContext(repository, commit,
                                                                                         self.__mapped_method.get_change_file().get_path(),
                                                                                         False))
        pdg2.build_change_graph(1)
        pdg2.build_change_graph(pdg1)
        return ChangeGraph(pdg2)


class ChangeProject:
    __fixing_revisions: dict[str, list[int]]  # static
    __interesting_ast_node_type_ids: set[int] = set()  # static
    __interesting_ast_node_type_names: set[str] = set()  # static
    density_bins: list[int] = [
        2, 4, 8, 16, 32, 64, 128
    ]
    size_bins: list[int]

    # TODO: missing static { ... }

    __id: int = -1
    __name: str
    token_indexes: dict[str, int]
    index_tokens: dict[int, str]
    __running_time: int
    number_of_all_revisions: int = 0
    revisions: list[ChangeRevision]

    @multimethod
    def __init__(self, id: int, name: str):
        self.__id = id
        self.__name = name

    @multimethod
    def __init__(self, path: str, id: int, name: str):
        self.__id = id
        self.__name = name
        prefix: str = '{}/{}-'.format(path, name)
        # TODO
        # self.index_tokens
        # self.token_indexes

    def get_id(self) -> int:
        return self.__id

    def set_id(self, id: int):
        self.__id = id

    def get_name(self) -> str:
        return self.__name

    def set_name(self, name: str):
        self.__name = name

    def get_number_of_all_revisions(self) -> int:
        return self.number_of_all_revisions

    def get_revisions(self) -> list[ChangeRevision]:
        return self.revisions

    def get_token_indexes(self) -> dict[str, int]:
        return self.token_indexes

    def set_token_indexes(self, token_indexes: dict[str, int]):
        self.token_indexes = token_indexes

    def get_index_tokens(self) -> dict[int, str]:
        return self.index_tokens

    def set_index_tokens(self, index_tokens: dict[int, str]):
        self.index_tokens = index_tokens

    def get_running_time(self) -> int:
        return self.__running_time

    def set_running_time(self, running_time):
        self.__running_time = running_time

    @staticmethod
    def read_fixing_revisions(file_path: str):
        raise NotImplementedError('this method is not used in CPatMiner')


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


class ChangeSourceFile:
    __lines_of_code: int = 0
    __path: str

    def __init__(self, path: str, lines_of_code: int):
        self.__lines_of_code = lines_of_code
        self.__path = path

    def get_path(self) -> str:
        return self.__path

    def get_lines_of_code(self) -> int:
        return self.__lines_of_code
