import os.path
import libadalang as lal

from src.change import ChangeAnalyzer


class MainChangeAnalyzer:
    context = None

    def __init__(self):
        context = lal.AnalysisContext()

    @staticmethod
    def analyze(path, name):
        if not os.path.isdir(path):
            return
        if os.path.exists(os.path.join(path, '.git')):
            change_analyzer = ChangeAnalyzer(name, -1, path)
            change_analyzer.build_git_connector()
            change_analyzer.analyze_git()
            print('is a git directory')
        print(path)
        print('Analyze')

    @staticmethod
    def repositories():
        # TODO: read repositories from file.
        return ['AdaCore/libadalang', 'AdaCore/gnatstudio']


if __name__ == '__main__':
    analyzer = MainChangeAnalyzer()
    analyzer.analyze('C:/build/itecembed', 'itecembed')
