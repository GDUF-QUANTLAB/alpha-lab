"""
BlazeStore核心模块

提供本地Parquet文件存储、SQL查询功能。
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from .config import get_settings
from .local import LocalStore
from .parse import extract_table_names_from_sql

DB_PATH = get_settings().get("paths.store")
_local_store = LocalStore()


def set_local_store(store: LocalStore) -> None:
    """
    设置本地存储实例。

    Args:
        store: LocalStore实例

    Examples:
        >>> from blazestore.local import LocalStore
        >>> store = LocalStore("/tmp/custom_path")
        >>> set_local_store(store)
    """
    global _local_store
    _local_store = store


def get_local_store() -> LocalStore:
    """
    获取当前本地存储实例。

    Returns:
        LocalStore: 当前LocalStore实例

    Examples:
        >>> store = get_local_store()
        >>> store.list_tables()
    """
    return _local_store


# ======================== Local Database ========================


def tb_path(tb_name: str) -> Path:
    """
    获取表名的完整本地路径。

    Args:
        tb_name: 表名，路径风格：a/b/c

    Returns:
        Path: 完整的本地绝对路径 $DB_PATH/a/b/c

    Examples:
        >>> tb_path("my_table")
        Path('/home/user/BlazeStore/my_table')
        >>> tb_path("data/stocks")
        Path('/home/user/BlazeStore/data/stocks')
    """
    return _local_store.tb_path(tb_name)


def put(
    df: pl.DataFrame,
    tb_name: str,
    partitions: list[str] | None = None,
    abs_path: bool = False,
) -> None:
    """
    将DataFrame写入指定的表目录，支持分区存储。

    该函数将给定的DataFrame（df）写入本地文件系统，基于提供的表名（tb_name）。
    如果指定了分区，数据将根据这些分区列进行分割和存储。
    此外，abs_path参数可以指定tb_name是否应被视为绝对路径。
    如果目录不存在，将自动创建。

    Args:
        df: 要写入的DataFrame
        tb_name: 表名，用于确定存储目录
        partitions: 用于分区的列名列表。如果未提供，则不执行分区
        abs_path: tb_name是否应被视为绝对路径。默认为False

    Raises:
        FileOperationError: 如果目录创建失败
        FileOperationError: 如果数据写入失败

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        >>> put(df, "my_table")
        >>> put(df, "partitioned_table", partitions=["b"])
        >>> put(df, "/absolute/path/to/table", abs_path=True)
    """
    if abs_path:
        store = LocalStore(Path(tb_name).parent)
        store.put(df, Path(tb_name).name, partitions=partitions)
    else:
        _local_store.put(df, tb_name, partitions=partitions)


def has(tb_name: str) -> bool:
    """
    判断给定的表名是否存在。

    Args:
        tb_name: 要检查的表名

    Returns:
        bool: 如果表存在返回True，否则返回False

    Examples:
        >>> has("my_table")
        True
        >>> has("non_existent_table")
        False
    """
    return _local_store.has(tb_name)


def sql(
    query: str, abs_path: bool = False, lazy: bool = True
) -> pl.DataFrame | pl.LazyFrame:
    """
    对本地Parquet文件执行SQL查询。

    该函数将SQL查询中的表名转换为Parquet文件路径，并使用Polars SQL引擎执行查询。

    Args:
        query: SQL查询字符串
        abs_path: 是否使用绝对路径作为表路径。默认为False
        lazy: 是否返回LazyFrame（True）或DataFrame（False）。默认为True

    Returns:
        pl.DataFrame | pl.LazyFrame: 查询结果

    Raises:
        QueryError: 如果SQL执行失败
        PathError: 如果表文件不存在

    Examples:
        >>> sql("SELECT * FROM my_table WHERE a > 1")
        shape: (2, 2)
        ┌─────┬─────┐
        │ a   ┆ b   │
        │ --- ┆ --- │
        │ i64 ┆ str │
        ╞═════╪═════╡
        │ 2   ┆ y   │
        │ 3   ┆ z   │
        └─────┴─────┘
        >>> sql("SELECT * FROM my_table", lazy=False)
        shape: (3, 2)
        ┌─────┬─────┐
        │ a   ┆ b   │
        │ --- ┆ --- │
        │ i64 ┆ str │
        ╞═════╪═════╡
        │ 1   ┆ x   │
        │ 2   ┆ y   │
        │ 3   ┆ z   │
        └─────┴─────┘
    """
    tbs = extract_table_names_from_sql(query)
    convertor = {}
    for tb in tbs:
        if abs_path:
            db_path = tb
        else:
            db_path = str(tb_path(tb))
        format_tb = f"read_parquet('{db_path}/**/*.parquet')"
        convertor[tb] = format_tb
    pattern = re.compile("|".join(re.escape(k) for k in convertor.keys()))
    new_query = pattern.sub(lambda m: convertor[m.group(0)], query)
    if not lazy:
        return pl.sql(new_query).collect()
    return pl.sql(new_query)


# ======================== Local Store Management ========================


def list_tables() -> list[str]:
    """
    列出所有表。

    Returns:
        list[str]: 表名列表

    Examples:
        >>> list_tables()
        ['users', 'orders', 'products']
    """
    return _local_store.list_tables()


def get_table_info(tb_name: str) -> dict:
    """
    获取表的详细信息。

    Args:
        tb_name: 表名

    Returns:
        dict: 表信息字典

    Raises:
        PathError: 表不存在

    Examples:
        >>> get_table_info("users")
        {
            'name': 'users',
            'type': 'simple',
            'columns': ['id', 'name', 'email'],
            'dtypes': {'id': 'Int64', 'name': 'Utf8', 'email': 'Utf8'},
            'rows': 1000,
            'partitions': None,
            'version': '1000_3_20240316123456',
            'created_at': '2024-03-16T12:00:00',
            'updated_at': '2024-03-16T12:34:56'
        }
    """
    return _local_store.get_table_info(tb_name)


def delete_table(tb_name: str) -> None:
    """
    删除表。

    Args:
        tb_name: 表名

    Raises:
        PathError: 表不存在
        FileOperationError: 删除失败

    Examples:
        >>> delete_table("old_table")
    """
    _local_store.delete_table(tb_name)


def rename_table(old_name: str, new_name: str) -> None:
    """
    重命名表。

    Args:
        old_name: 旧表名
        new_name: 新表名

    Raises:
        PathError: 表不存在或新表名已存在
        FileOperationError: 重命名失败

    Examples:
        >>> rename_table("old_table", "new_table")
    """
    _local_store.rename_table(old_name, new_name)


def copy_table(src_name: str, dst_name: str) -> None:
    """
    复制表。

    Args:
        src_name: 源表名
        dst_name: 目标表名

    Raises:
        PathError: 源表不存在或目标表已存在
        FileOperationError: 复制失败

    Examples:
        >>> copy_table("users", "users_backup")
    """
    _local_store.copy_table(src_name, dst_name)


def optimize_table(tb_name: str) -> None:
    """
    优化表（合并小文件）。

    Args:
        tb_name: 表名

    Raises:
        PathError: 表不存在
        FileOperationError: 优化失败

    Examples:
        >>> optimize_table("fragmented_table")
    """
    _local_store.optimize_table(tb_name)


def check_table(tb_name: str) -> bool:
    """
    检查表完整性。

    Args:
        tb_name: 表名

    Returns:
        bool: 表是否完整

    Raises:
        PathError: 表不存在

    Examples:
        >>> check_table("users")
        True
        >>> check_table("corrupted_table")
        False
    """
    return _local_store.check_table(tb_name)


def get_actual_mtime(tb_name: str) -> str:
    """
    获取表数据的实际修改时间（遍历所有 Parquet 文件）。

    不依赖 meta.json，直接扫描文件系统获取最新修改时间。
    用于验证 meta.json 的准确性或诊断数据变更。

    Args:
        tb_name: 表名

    Returns:
        str: ISO 格式的时间戳

    Raises:
        PathError: 表不存在
        FileOperationError: 表为空或无 Parquet 文件

    Examples:
        >>> get_actual_mtime("stocks")
        '2024-03-16T12:34:56.789012'

        >>> info = get_table_info("stocks")
        >>> actual_mtime = get_actual_mtime("stocks")
        >>> if info["updated_at"] < actual_mtime:
        ...     print("警告：数据可能被外部修改！")
    """
    return _local_store.get_actual_mtime(tb_name)


# ======================== Table Cursor ========================


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
        return _local_store.read_table(self.tb_name)

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
