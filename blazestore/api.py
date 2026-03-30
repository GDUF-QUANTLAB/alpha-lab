"""
BlazeStore核心模块

提供本地Parquet文件存储、SQL查询功能。
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from .local import LocalStore
from .parse import extract_table_names_from_sql

_store = LocalStore()


def tb_path(path: str = "") -> Path:
    """
    获取存储路径。

    Args:
        path: 相对路径（可选）

    Returns:
        Path: 完整路径
    """
    if path:
        return _store.base_path.joinpath(*path.split("/"))
    return _store.base_path


def put(
    df: pl.DataFrame | pl.LazyFrame,
    path: str,
    partitions: list[str] | None = None,
) -> None:
    """
    写入数据，自动识别模式：
    - path 以 .parquet 结尾 -> 直接写入该文件
    - path 是目录 + partitions -> Hive 分区
    - path 是目录 -> 写入 data.parquet

    Args:
        df: 要写入的DataFrame
        path: 相对路径
        partitions: 分区列名列表（可选）
    """
    _store.put(df, path, partitions=partitions)


def has(path: str) -> bool:
    """判断路径是否存在"""
    return _store.has(path)


def read(path: str) -> pl.DataFrame | pl.LazyFrame:
    """读取数据"""
    return _store.read(path)


def sql(query: str, lazy: bool = True) -> pl.DataFrame | pl.LazyFrame:
    """
    对本地Parquet文件执行SQL查询。

    Args:
        query: SQL查询字符串
        lazy: 是否返回LazyFrame（默认True）
    """
    tbs = extract_table_names_from_sql(query)
    if not tbs:
        if not lazy:
            return pl.sql(query).collect()
        return pl.sql(query)

    table_names = sorted(tbs, key=len, reverse=True)
    convertor: dict[str, str] = {}
    partitioned_sources: dict[str, pl.LazyFrame] = {}

    for i, tb in enumerate(table_names):
        db_path = tb_path(tb)
        if _store._is_partitioned_table(tb):
            alias = f"__tb_{i}"
            partitioned_sources[alias] = pl.scan_parquet(
                db_path / "**/*.parquet",
                hive_partitioning=True,
            )
            convertor[tb] = alias
        else:
            convertor[tb] = f"read_parquet('{db_path}/**/*.parquet')"

    pattern = re.compile("|".join(re.escape(k) for k in table_names))
    new_query = pattern.sub(lambda m: convertor[m.group(0)], query)

    if partitioned_sources:
        return pl.SQLContext(**partitioned_sources).execute(new_query, eager=not lazy)
    if not lazy:
        return pl.sql(new_query).collect()
    return pl.sql(new_query)


def list_tables() -> list[str]:
    """列出所有表"""
    return _store.list_tables()


def get_table_info(tb_name: str) -> dict:
    """获取表信息"""
    return _store.get_table_info(tb_name)


def delete_table(tb_name: str) -> None:
    """删除表"""
    _store.delete_table(tb_name)


def rename_table(old_name: str, new_name: str) -> None:
    """重命名表"""
    _store.rename_table(old_name, new_name)


def copy_table(src_name: str, dst_name: str) -> None:
    """复制表"""
    _store.copy_table(src_name, dst_name)


def optimize_table(tb_name: str) -> None:
    """优化表（合并小文件）"""
    _store.optimize_table(tb_name)


def check_table(tb_name: str) -> bool:
    """检查表完整性"""
    return _store.check_table(tb_name)


def get_actual_mtime(tb_name: str) -> str:
    """获取表数据的实际修改时间"""
    return _store.get_actual_mtime(tb_name)
