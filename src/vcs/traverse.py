import os
import uuid
import pickle
import multiprocessing
import time
import json
import subprocess
import datetime

import libadalang as lal

from log import logger
from pathlib import Path
from pydriller import Repository
from pydriller.domain.commit import ModificationType

import settings
import changegraph


class GitAnalyzer:
    GIT_REPOSITORIES_DIR = settings.get('git_repositories_dir')
    GIT_REPOSITORIES = settings.get('repos')
    STORAGE_DIR = settings.get('change_graphs_storage_dir')
    STORE_INTERVAL = settings.get('change_graphs_store_interval', 300)
    TRAVERSE_ASYNC = settings.get('traverse_async', True)

    MIN_DATE = None
    if settings.get('traverse_min_date', required=False):
        MIN_DATE = datetime.datetime.strptime(settings.get('traverse_min_date', required=False), '%d.%m.%Y') \
            .replace(tzinfo=datetime.timezone.utc)

    def __init__(self):
        self._data_file_dir = os.path.join(self.GIT_REPOSITORIES_DIR, '.data.json')
        self._data = {
            'in_progress': [],  # todo
            'visited': []
        }

        self._load_data_file()

    def _load_data_file(self):
        with open(self._data_file_dir, 'a+') as f:
            f.seek(0)
            data = f.read()

        if data:
            try:
                self._data = json.loads(data)
            except:
                logger.warning('Unable to load existing git repo data file')

    def _save_data_file(self):
        with open(self._data_file_dir, 'w+') as f:
            json.dump(self._data, f, indent=4)

    def build_change_graphs(self, parse_only_tests=False):
        repo_names = [
            name for name in os.listdir(self.GIT_REPOSITORIES_DIR)
            if not name.startswith('_') and not name.startswith('.') and name not in self._data['visited']]

        if not repo_names:
            logger.warning('No available repositories were found')
            return

        logger.warning(f'Found {len(repo_names)} repositories, starting a build process')

        if GitAnalyzer.TRAVERSE_ASYNC:
            with multiprocessing.Pool(processes=multiprocessing.cpu_count(), maxtasksperchild=1000) as pool:
                self._mine_changes(repo_names, pool=pool, parse_only_tests=parse_only_tests)
        else:
            self._mine_changes(repo_names, parse_only_tests=parse_only_tests)

    def _mine_changes(self, repo_names, pool=None, parse_only_tests=False):
        for repo_num, repo_name in enumerate(repo_names):
            logger.warning(f'Looking at repo {repo_name} [{repo_num + 1}/{len(repo_names)}]')

            self._data['visited'].append(repo_name)
            self._save_data_file()

            start = time.time()
            commits = self._extract_commits(repo_name)

            if pool and len(commits) > 0:
                try:
                    pool.starmap(self._build_and_store_change_graphs, zip(commits, [parse_only_tests] * len(commits)))
                except:
                    logger.error(f'Pool.map failed for repo {repo_name}', exc_info=True)
            else:
                for commit in commits:
                    self._build_and_store_change_graphs(commit, parse_only_tests)

            logger.warning(f'Done building change graphs for repo={repo_name} [{repo_num + 1}/{len(repo_names)}]',
                           start_time=start)

    def _extract_commits(self, repo_name):
        start = time.time()

        repo_path = os.path.join(self.GIT_REPOSITORIES_DIR, repo_name)
        repo_url = self._get_repo_url(repo_path)
        repo = Repository(repo_path, only_no_merge=True)

        commits = []
        for commit in repo.traverse_commits():
            if not commit.parents:
                continue

            if self.MIN_DATE and commit.committer_date < self.MIN_DATE:
                continue

            cut = {
                'author': {
                    'email': commit.author.email,
                    'name': commit.author.name
                } if commit.author else None,
                'num': len(commits) + 1,
                'hash': commit.hash,
                'dtm': commit.committer_date,
                'msg': commit.msg,
                'modifications': [],
                'repo': {
                    'name': repo_name,
                    'path': repo_path,
                    'url': repo_url
                }
            }

            for mod in commit.modified_files:
                try:
                    cut['modifications'].append({
                        'type': mod.change_type,

                        'old_src': mod.source_code_before,
                        'old_path': mod.old_path,

                        'new_src': mod.source_code,
                        'new_path': mod.new_path,

                        'repo_name': repo_name
                    })
                except ValueError:
                    logger.warning(f'Could not find commit {mod}')

            commits.append(cut)

        logger.log(logger.WARNING, 'Commits extracted', start_time=start)
        return commits

    @staticmethod
    def _get_repo_url(repo_path):
        args = ['git', 'config', '--get', 'remote.origin.url']
        result = subprocess.run(args, stdout=subprocess.PIPE, cwd=repo_path).stdout.decode('utf-8')
        return result.strip()

    @staticmethod
    def _store_change_graphs(graphs):
        pickled_graphs = []
        for graph in graphs:
            if graph.repo_info and graph.repo_info.repo_name:
                changegraph.export_graph_image(graph, os.path.join(GitAnalyzer.STORAGE_DIR,
                                                                   graph.repo_info.repo_name,
                                                                   f'{str(uuid.uuid4())}.dot'))
            try:
                pickled = pickle.dumps(graph, protocol=5)
                pickled_graphs.append(pickled)
            except RecursionError:
                logger.error(f'Unable to pickle graph, file_path={graph.repo_info.old_method.file_path}, '
                             f'method={graph.repo_info.old_method.full_name}', exc_info=True)

        filename = uuid.uuid4().hex
        logger.info(f'Trying to store graphs to {filename}', show_pid=True)
        with open(os.path.join(GitAnalyzer.STORAGE_DIR, f'{filename}.pickle'), 'w+b') as f:
            pickle.dump(pickled_graphs, f)
        logger.info(f'Storing graphs to {filename} finished', show_pid=True)

    @staticmethod
    def _build_and_store_change_graphs(commit, parse_only_tests=False):
        change_graphs = []
        commit_msg = commit['msg'].replace('\n', '; ')
        logger.info(f'Looking at commit #{commit["hash"]}, msg: "{commit_msg}"', show_pid=True)

        for mod in commit['modifications']:
            if mod['type'] != ModificationType.MODIFY:
                continue

            if not all([mod['old_path'].endswith('.adb'), mod['new_path'].endswith('.adb')]):
                continue

            if parse_only_tests:
                if mod['old_path'].find('test') == -1 and mod['new_path'].find('test') == -1:
                    continue

            old_method_to_new = GitAnalyzer._get_methods_mapping(
                GitAnalyzer._extract_methods(mod['old_path'], mod['old_src'], mod['repo_name']),
                GitAnalyzer._extract_methods(mod['new_path'], mod['new_src'], mod['repo_name'])
            )

            for old_method, new_method in old_method_to_new.items():
                old_method_src = old_method.get_source()
                new_method_src = new_method.get_source()

                if not all([old_method_src, new_method_src]) or old_method_src.strip() == new_method_src.strip():
                    continue

                line_count = max(old_method_src.count('\n'), new_method_src.count('\n'))
                if line_count > settings.get('traverse_file_max_line_count'):
                    logger.info(f'Ignored files due to line limit: {mod["old_path"]} -> {mod["new_src"]}')
                    continue

                repo_info = RepoInfo(
                    commit['repo']['name'],
                    commit['repo']['path'],
                    commit['repo']['url'],
                    commit['hash'],
                    commit['dtm'],
                    mod['old_path'],
                    mod['new_path'],
                    old_method,
                    new_method,
                    author_email=commit['author']['email'] if commit.get('author') else None,
                    author_name=commit['author']['name'] if commit.get('author') else None
                )

                try:
                    cg = changegraph.build_from_trees(old_method.ast, new_method.ast, repo_info=repo_info)
                except:
                    logger.log(logger.ERROR,
                               f'Unable to build a change graph for '
                               f'repo={commit["repo"]["path"]}, '
                               f'commit=#{commit["hash"]}, '
                               f'method={old_method.full_name}, '
                               f'line={old_method.ast.sloc_range}', exc_info=True, show_pid=True)
                    continue

                change_graphs.append(cg)

                if len(change_graphs) >= GitAnalyzer.STORE_INTERVAL:
                    GitAnalyzer._store_change_graphs(change_graphs)
                    change_graphs.clear()

        if change_graphs:
            GitAnalyzer._store_change_graphs(change_graphs)
            change_graphs.clear()

    @staticmethod
    def _extract_methods(file_path, src, repo_name):
        project_path = os.path.join(GitAnalyzer.GIT_REPOSITORIES_DIR, repo_name)

        # if os.path.exists(os.path.join(project_path, GitAnalyzer.GIT_REPOSITORIES[repo_name])):
        #     unit_provider = lal.GPRProject(os.path.join(project_path, GitAnalyzer.GIT_REPOSITORIES[repo_name])).create_unit_provider()
        #     context = lal.AnalysisContext(unit_provider=unit_provider)
        # else:
        context = lal.AnalysisContext()

        unit = context.get_from_buffer(os.path.join(project_path, file_path), src)
        methods: list[lal.SubpBody] = unit.root.findall(lambda n: isinstance(n, lal.SubpBody))
        return [Method(file_path, m.f_subp_spec.f_subp_name.text, m, src) for m in methods]

    @staticmethod
    def _set_unique_names(methods):
        method_name_to_cnt = {}
        for method in methods:
            cnt = method_name_to_cnt.setdefault(method.full_name, 0) + 1
            method_name_to_cnt[method.full_name] = cnt

            if cnt > 1:
                method.full_name += f'#{cnt}'

    @staticmethod
    def _get_methods_mapping(old_methods, new_methods):
        GitAnalyzer._set_unique_names(old_methods)
        GitAnalyzer._set_unique_names(new_methods)

        old_method_to_new = {}
        for old_method in old_methods:
            for new_method in new_methods:
                if old_method.full_name == new_method.full_name:
                    old_method_to_new[old_method] = new_method
        return old_method_to_new


class Method:
    def __init__(self, path, name, ast, src):
        self.file_path = path
        self.ast = ast
        self.source = ast.text
        self.src = src.strip()

        self.name = name
        self.full_name = name

    def extend_path(self, prefix, separator='.'):
        self.full_name = f'{prefix}{separator}{self.full_name}'

    def get_source(self):
        return self.source

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['ast']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


class RepoInfo:
    def __init__(self, repo_name, repo_path, repo_url, commit_hash, commit_dtm,
                 old_file_path, new_file_path, old_method, new_method,
                 author_email=None, author_name=None):
        self.repo_name = repo_name
        self.repo_path = repo_path
        self.repo_url = repo_url

        self.commit_hash = commit_hash
        self.commit_dtm = commit_dtm

        self.old_file_path = old_file_path
        self.new_file_path = new_file_path

        self.old_method = old_method
        self.new_method = new_method

        self.author_email = author_email
        self.author_name = author_name