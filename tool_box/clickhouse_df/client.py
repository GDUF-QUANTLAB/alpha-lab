from __future__ import annotations

from random import randint

import pandas as pd
import polars as pl
import pyarrow as pa
from clickhouse_driver import Client

from . import dtype
from .thread_utils import ThreadLocalVariable

_conns = ThreadLocalVariable(default_factory=lambda: [])


def connect(urls: list[str], user: str, password: str) -> Client:
    """
    连接 ClickHouse 服务器，支持集群负载均衡 (随机选择)。

    Args:
        urls: ClickHouse 地址列表，格式如 ["host1:port1", "host2:port2", ...].
        user: 用户名.
        password: 密码.

    Returns:
        Client: 有效的 clickhouse_driver.Client 实例.

    Raises:
        ValueError: 如果 urls 为空或格式错误.
    """
    if not urls:
        raise ValueError("urls 参数不能为空")
    i = randint(0, len(urls) - 1)
    url_ini = urls[i]
    try:
        host, port_s = url_ini.split(":")
        port = int(port_s)
    except Exception as e:
        raise ValueError(f"非法的 ClickHouse 地址格式: {url_ini}") from e
    conn = Client(
        host,
        port=port,
        round_robin=True,
        alt_hosts=",".join(urls),
        user=user,
        password=password,
    )
    conns = _conns.get()
    conns.append(conn)
    return conns[-1]


def to_pandas(sql: str, conn: Client | None = None) -> pd.DataFrame:
    """
    执行 SQL 并返回 pandas.DataFrame。

    Args:
        sql: SQL 查询语句.
        conn: 可选的 ClickHouse 客户端实例。如果为 None，使用当前线程的默认连接.

    Returns:
        pd.DataFrame: 查询结果.
    """
    conn = conn if conn is not None else _get_default_conn()
    return conn.query_dataframe(sql)


def to_polars(sql: str, conn: Client | None = None) -> pl.DataFrame:
    """
    执行 SQL 并返回 polars.DataFrame。

    Args:
        sql: SQL 查询语句.
        conn: 可选的 ClickHouse 客户端实例。如果为 None，使用当前线程的默认连接.

    Returns:
        pl.DataFrame: 查询结果.
    """
    conn = conn if conn is not None else _get_default_conn()
    data, columns = conn.execute(sql, columnar=True, with_column_types=True)
    if len(data) < 1:
        # Handle empty results while preserving types
        field_types = {
            name: dtype.map_clickhouse_to_arrow(type_) for name, type_ in columns
        }
        arrays = [pa.array([], type=col_type) for col_type in field_types.values()]
        arrow_table = pa.Table.from_arrays(arrays, schema=pa.schema(field_types))
        return pl.from_arrow(arrow_table)

    field_types = {
        name: dtype.map_clickhouse_to_arrow(type_) for name, type_ in columns
    }
    arrow_table = pa.Table.from_arrays(
        [
            pa.array(col, type=col_type)
            for col, col_type in zip(data, field_types.values(), strict=False)
        ],
        schema=pa.schema(field_types),
    )

    return pl.from_arrow(arrow_table)


def _get_default_conn() -> Client:
    """
    返回当前线程的最后一个连接。
    """
    conns = _conns.get()
    if not conns:
        raise RuntimeError("No active ClickHouse connection found in current thread.")
    return conns[-1]


def close_all() -> int:
    """
    关闭当前线程的所有连接。
    Returns:
        int: 关闭的连接数量.
    """
    conns = _conns.get()
    count = len(conns)
    for conn in conns:
        conn.disconnect()
    conns.clear()
    return count
