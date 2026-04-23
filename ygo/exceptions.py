from __future__ import annotations

from dataclasses import dataclass


class WarnException(Exception):
    """
    Custom exception class for warnings.
    """

    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class FailTaskError:
    """
    Data class representing a failed task in a task pool.
    """

    task_name: str
    error: Exception

    def __str__(self) -> str:
        return f"""
[失败任务]: {self.task_name}
[错误信息]: \n{self.error}
"""

    def __repr__(self) -> str:
        return self.__str__()
