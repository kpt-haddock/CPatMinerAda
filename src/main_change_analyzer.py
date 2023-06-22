import os.path
import libadalang as lal

from datetime import datetime
from src.change import ChangeAnalyzer


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
            print('Done {} in {}'.format(name, end_project_time - start_project_time))

    @staticmethod
    def repositories():
        # TODO: read repositories from file.
        return ['AdaCore/libadalang']


if __name__ == '__main__':
    analyzer = MainChangeAnalyzer()
    analyzer.analyze('C:/repos/ada-synth-lib', 'C:/repos/ada-synth-lib/ada_synth_lib.gpr')
