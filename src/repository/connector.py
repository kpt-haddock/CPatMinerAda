from abc import ABC
import re


class Connector(ABC):
    fixing_patterns: [str] = [
        "issue[\\s]+[0-9]+",
        "issues[\\s]+[0-9]+",
        "issue[\\s]+#[0-9]+",
        "issues[\\s]+#[0-9]+",
        "issue[\\s]+# [0-9]+",
        "bug",
        "fix",
        "error",
        "exception"
    ]

    @staticmethod
    def is_fixing_commit(commit_log: str) -> bool:
        if commit_log is not None:
            lower_commit_log: str = commit_log.lower()
            for fixing_pattern in Connector.fixing_patterns:
                if len(re.findall(fixing_pattern, lower_commit_log)) > 0:
                    return True
        return False


