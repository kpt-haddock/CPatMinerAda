from src.repository.git_connector import GitConnector
import time

print('abcdfedfadfljk'[4])

git_connector = GitConnector('C:\\build\\libadalang')

print(git_connector.get_number_of_commits())
print(git_connector.get_number_of_commits('.exe'))
git_connector.connect()
# print(len(git_connector.log()))
print(git_connector.log())

print(sum(1 for _ in git_connector.log()))

start = time.time()

for commit in git_connector.log():
    changed_files = git_connector.get_changed_files(commit, '')

end = time.time()

print(end-start)

test_array = []


def add_test_array(a):
    a.append('a')
    a.append('b')
    a.append('c')


add_test_array(test_array)


print(test_array)
