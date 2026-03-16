"""
BlazeStore - 本地Parquet存储和数据库集成

提供本地Parquet文件存储、SQL查询、MySQL和ClickHouse数据库集成功能。
"""

from .clients import (
    ClickHouseClient,
    MySQLClient,
    read_ck,
    read_mysql,
    write_mysql,
)
from .config import get_settings
from .core import (
    check_table,
    copy_table,
    delete_table,
    get_local_store,
    get_table_info,
    has,
    list_tables,
    optimize_table,
    put,
    rename_table,
    set_local_store,
    sql,
    tb_path,
)

__all__ = [
    # Config
    "get_settings",
    # Local Store
    "tb_path",
    "put",
    "has",
    "sql",
    "list_tables",
    "get_table_info",
    "delete_table",
    "rename_table",
    "copy_table",
    "optimize_table",
    "check_table",
    # Database Clients
    "MySQLClient",
    "ClickHouseClient",
    "read_mysql",
    "write_mysql",
    "read_ck",
    # Internal (for testing)
    "set_local_store",
    "get_local_store",
]
