"""
BlazeStore - 本地Parquet存储和数据库集成

提供本地Parquet文件存储、MySQL和ClickHouse数据库集成功能。

Examples:
    >>> from blazestore import LocalStore, get_settings
    >>> store = LocalStore()
    >>> store.put(df, "stocks")
    >>> store.put(df, "stocks/2024.parquet")
    >>> store.put(df, "stocks", partitions=["date"])
    >>> df = store.read("stocks").collect()
"""

from .api import (
    has,
    list_tables,
    put,
    read,
    sql,
    tb_path,
)
from .clients import (
    read_ck,
    read_mysql,
)
from .config import get_settings
from .local import LocalStore

__all__ = [
    "read_ck",
    "read_mysql",
    "LocalStore",
    "get_settings",
    "sql",
    "has",
    "list_tables",
    "put",
    "read",
    "tb_path",
]
