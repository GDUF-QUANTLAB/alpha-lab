"""
BlazeStore自定义异常类
"""

from __future__ import annotations


class BlazeStoreError(Exception):
    """
    BlazeStore基础异常类。

    所有BlazeStore异常的基类，提供统一的错误处理接口。
    """

    def __init__(
        self, message: str, original_exception: Exception | None = None
    ) -> None:
        """
        初始化异常。

        Args:
            message: 错误消息
            original_exception: 原始异常（如果有）
        """
        super().__init__(message)
        self.original_exception = original_exception


class ConfigError(BlazeStoreError):
    """
    配置错误。

    当配置文件缺失、配置项缺失或配置格式错误时抛出。
    """

    pass


class DatabaseError(BlazeStoreError):
    """
    数据库错误基类。

    所有数据库相关错误的基类。
    """

    pass


class ConnectionError(DatabaseError):
    """
    连接错误。

    当数据库连接失败时抛出。
    """

    pass


class QueryError(DatabaseError):
    """
    查询错误。

    当SQL查询执行失败时抛出。
    """

    pass


class WriteError(DatabaseError):
    """
    写入错误。

    当数据写入失败时抛出。
    """

    pass


class StorageError(BlazeStoreError):
    """
    存储错误基类。

    所有存储相关错误的基类。
    """

    pass


class FileOperationError(StorageError):
    """
    文件操作错误。

    当文件读写操作失败时抛出。
    """

    pass


class PathError(StorageError):
    """
    路径错误。

    当路径不存在或无效时抛出。
    """

    pass


class PartitionError(StorageError):
    """
    分区错误。

    当分区操作失败时抛出。
    """

    pass
