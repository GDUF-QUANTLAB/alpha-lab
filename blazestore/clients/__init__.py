"""
数据库客户端模块

提供MySQL和ClickHouse数据库客户端以及便捷的读写函数。
"""

from .clickhouse import ClickHouseClient
from .mysql import MySQLClient

__all__ = [
    "MySQLClient",
    "ClickHouseClient",
    "read_mysql",
    "read_ck",
]


def read_mysql(query: str, db_conf: str = "databases.mysql"):
    """
    从MySQL数据库读取数据。

    Args:
        query: 要执行的SQL查询
        db_conf: 设置中的配置键（例如 "databases.mysql"）

    Returns:
        pl.DataFrame: 查询结果

    Raises:
        ConfigError: 数据库配置缺失
        ConnectionError: 数据库连接失败
        QueryError: 查询执行失败

    Examples:
        >>> read_mysql("SELECT * FROM users WHERE id = 1")
        shape: (1, 3)
        ┌────┬─────────┬──────────┐
        │ id ┆ name    ┆ email    │
        │ --- ┆ ---     ┆ ---      │
        │ i64 ┆ str     ┆ str      │
        ╞════╪═════════╪══════════╡
        │ 1  ┆ Alice   ┆ a@e.com  │
        └────┴─────────┴──────────┘
        >>> read_mysql("SELECT * FROM products", db_conf="databases.mysql_readonly")
    """
    client = MySQLClient(db_conf)
    return client.read(query)


def write_mysql(df, tb_name: str, db_conf: str = "databases.mysql") -> None:
    """
    将DataFrame写入MySQL数据库。

    Args:
        df: 要写入的DataFrame
        tb_name: 目标表名
        db_conf: 设置中的配置键（例如 "databases.mysql"）

    Raises:
        ConfigError: 数据库配置缺失
        ConnectionError: 数据库连接失败
        WriteError: 数据写入失败

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        >>> write_mysql(df, "users")
        >>> write_mysql(df, "users_backup", db_conf="databases.mysql_writeonly")
    """
    client = MySQLClient(db_conf)
    client.write(df, tb_name)


def read_ck(query: str, db_conf: str = "databases.ck"):
    """
    从ClickHouse集群读取数据。

    Args:
        query: 要执行的SQL查询
        db_conf: 设置中的配置键（例如 "databases.ck"）

    Returns:
        pl.DataFrame: 查询结果

    Raises:
        ConfigError: 数据库配置缺失
        ConnectionError: 数据库连接失败
        QueryError: 查询执行失败

    Examples:
        >>> read_ck("SELECT * FROM stocks WHERE date >= '2023-01-01'")
        shape: (100, 5)
        ┌────────────┬───────┬────────┬────────┬────────┐
        │ date       ┆ symbol ┆ open   ┆ high   ┆ low    │
        │ ---        ┆ ---   ┆ ---    ┆ ---    ┆ ---    │
        │ date       ┆ str   ┆ f64    ┆ f64    ┆ f64    │
        ╞════════════╪═══════╪════════╪════════╪════════╡
        │ 2023-01-03 ┆ AAPL  ┆ 130.0  ┆ 132.0  ┆ 129.0  │
        │ 2023-01-04 ┆ AAPL  ┆ 132.0  ┆ 134.0  ┆ 131.0  │
        └────────────┴───────┴────────┴────────┴────────┘
        >>> read_ck("SELECT count() FROM events", db_conf="databases.ck_analytics")
    """
    client = ClickHouseClient(db_conf)
    return client.read(query)
