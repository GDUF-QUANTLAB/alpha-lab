"""
BlazeStore接口协议定义
"""

from __future__ import annotations

import polars as pl


class DatabaseReader:
    """
    数据库读取器协议。

    定义数据库读取的标准接口，支持SQL查询和数据读取。
    """

    def read(self, query: str) -> pl.DataFrame:
        """
        执行SQL查询并返回结果。

        Args:
            query: SQL查询字符串

        Returns:
            pl.DataFrame: 查询结果

        Raises:
            ConnectionError: 数据库连接失败
            QueryError: 查询执行失败
        """
        ...


class DatabaseWriter:
    """
    数据库写入器协议。

    定义数据库写入的标准接口，支持数据写入。
    """

    def write(self, df: pl.DataFrame, table_name: str) -> None:
        """
        将DataFrame写入数据库表。

        Args:
            df: 要写入的DataFrame
            table_name: 目标表名

        Raises:
            ConnectionError: 数据库连接失败
            WriteError: 数据写入失败
        """
        ...
