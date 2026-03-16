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
