"""
表游标模块

提供对本地表的便捷访问，封装核心功能为面向对象接口。
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .core import (
    check_table,
    copy_table,
    delete_table,
    get_actual_mtime,
    get_local_store,
    get_table_info,
    has,
    optimize_table,
    put,
    rename_table,
    sql,
    tb_path,
)


class TableCursor:
    """
    表游标类，提供对本地表的便捷访问。

    通过表名创建游标，提供信息查询、数据读写、表管理等功能。
    自动处理跨平台路径问题。

    Args:
        tb_name: 表名

    Examples:
        >>> cursor = TableCursor("my_table")
        >>> if cursor.exists():
        ...     df = cursor.read()
        ...     cursor.optimize()
    """

    def __init__(self, tb_name: str) -> None:
        self.tb_name = tb_name

    def exists(self) -> bool:
        """
        判断表是否存在。

        Returns:
            bool: 表是否存在

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> cursor.exists()
            True
        """
        return has(self.tb_name)

    def info(self) -> dict:
        """
        获取表信息。

        Returns:
            dict: 表信息字典

        Raises:
            PathError: 表不存在

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> info = cursor.info()
            >>> print(info["columns"])
        """
        return get_table_info(self.tb_name)

    def path(self) -> Path:
        """
        获取表路径。

        Returns:
            Path: 表的完整路径（自动适配操作系统）

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> print(cursor.path())
        """
        return tb_path(self.tb_name)

    def mtime(self) -> str:
        """
        获取表的实际修改时间。

        Returns:
            str: ISO 格式的时间戳

        Raises:
            PathError: 表不存在

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> print(cursor.mtime())
        """
        return get_actual_mtime(self.tb_name)

    def read(self) -> pl.DataFrame:
        """
        读取表数据。

        Returns:
            pl.DataFrame: 表数据

        Raises:
            PathError: 表不存在
            FileOperationError: 文件读取失败

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> df = cursor.read()
        """
        return get_local_store().read(self.tb_name)

    def sql(self, query: str, lazy: bool = True) -> pl.DataFrame | pl.LazyFrame:
        """
        执行 SQL 查询。

        Args:
            query: SQL 查询字符串
            lazy: 是否返回 LazyFrame（True）或 DataFrame（False）

        Returns:
            pl.DataFrame | pl.LazyFrame: 查询结果

        Raises:
            QueryError: SQL 执行失败
            PathError: 表不存在

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> df = cursor.sql("SELECT * FROM my_table WHERE a > 1")
            >>> df = cursor.sql("SELECT * FROM my_table", lazy=False)
        """
        return sql(query, abs_path=False, lazy=lazy)

    def delete(self) -> None:
        """
        删除表。

        Raises:
            PathError: 表不存在
            FileOperationError: 删除失败

        Examples:
            >>> cursor = TableCursor("old_table")
            >>> cursor.delete()
        """
        delete_table(self.tb_name)

    def rename(self, new_name: str) -> None:
        """
        重命名表。

        Args:
            new_name: 新表名

        Raises:
            PathError: 表不存在或新表名已存在
            FileOperationError: 重命名失败

        Examples:
            >>> cursor = TableCursor("old_table")
            >>> cursor.rename("new_table")
        """
        rename_table(self.tb_name, new_name)
        self.tb_name = new_name

    def copy(self, new_name: str) -> None:
        """
        复制表。

        Args:
            new_name: 目标表名

        Raises:
            PathError: 源表不存在或目标表已存在
            FileOperationError: 复制失败

        Examples:
            >>> cursor = TableCursor("users")
            >>> cursor.copy("users_backup")
        """
        copy_table(self.tb_name, new_name)

    def optimize(self) -> None:
        """
        优化表（合并小文件）。

        Raises:
            PathError: 表不存在
            FileOperationError: 优化失败

        Examples:
            >>> cursor = TableCursor("fragmented_table")
            >>> cursor.optimize()
        """
        optimize_table(self.tb_name)

    def check(self) -> bool:
        """
        检查表完整性。

        Returns:
            bool: 表是否完整

        Raises:
            PathError: 表不存在

        Examples:
            >>> cursor = TableCursor("my_table")
            >>> if cursor.check():
            ...     print("表完整")
        """
        return check_table(self.tb_name)

    def write(self, df: pl.DataFrame, partitions: list[str] | None = None) -> None:
        """
        写入数据到表。

        Args:
            df: 要写入的 DataFrame
            partitions: 分区列列表

        Raises:
            FileOperationError: 写入失败

        Examples:
            >>> import polars as pl
            >>> cursor = TableCursor("my_table")
            >>> df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
            >>> cursor.write(df)
            >>> cursor.write(df, partitions=["b"])
        """
        put(df, self.tb_name, partitions=partitions)


def cursor(tb_name: str) -> TableCursor:
    """
    创建表游标。

    Args:
        tb_name: 表名

    Returns:
        TableCursor: 表游标对象

    Examples:
        >>> cursor = cursor("my_table")
        >>> if cursor.exists():
        ...     df = cursor.read()
    """
    return TableCursor(tb_name)
