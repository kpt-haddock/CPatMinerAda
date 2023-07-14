import os.path
import settings

from datetime import datetime
from change import ChangeAnalyzer
from log import logger


class MainChangeAnalyzer:

    @staticmethod
    def analyze(path, name):
        if not os.path.isdir(path):
            return
        if os.path.exists(os.path.join(path, '.git')):
            start_project_time = datetime.now()
            change_analyzer = ChangeAnalyzer(name, -1, path)
            change_analyzer.build_git_connector()
            change_analyzer.analyze_git()
            end_project_time = datetime.now()
            logger.info('Done {} in {}'.format(name, end_project_time - start_project_time))

    @staticmethod
    def repositories():
        # TODO: read repositories from file.
        return ['AdaCore/libadalang']


if __name__ == '__main__':
    analyzer = MainChangeAnalyzer()
    repositories_dir = settings.get('git_repositories_dir')
    analyzer.analyze(os.path.join(repositories_dir, 'ada-synth-lib'),
                     os.path.join(repositories_dir, 'ada-synth-lib/ada_synth_lib.gpr'))
