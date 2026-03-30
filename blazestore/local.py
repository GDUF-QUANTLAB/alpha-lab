"""
本地存储管理模块

提供本地Parquet文件的存储和管理功能，支持非分区表和Hive分区表。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from .config import get_settings
from .exceptions import FileOperationError, PathError


class LocalStore:
    """
    本地存储管理类。

    提供本地Parquet文件的存储和管理功能，支持非分区表和Hive分区表。

    Args:
        base_path: 存储根目录，默认从配置文件读取。

    Examples:
        >>> store = LocalStore()
        >>> store.put(df, "stocks")
        >>> store.put(df, "stocks/2024.parquet")
        >>> store.put(df, "stocks", partitions=["date"])
    """

    def __init__(self, base_path: Path | str | None = None) -> None:
        if base_path is None:
            self.base_path = Path(get_settings().get("paths.store"))
        elif isinstance(base_path, str):
            self.base_path = Path(base_path)
        else:
            self.base_path = base_path

    def _is_partitioned_table(self, tb_name: str) -> bool:
        """
        检测表是否为Hive分区表。

        Args:
            tb_name: 表名或路径。

        Returns:
            bool: 是否为分区表。
        """
        tbpath = self.base_path.joinpath(*tb_name.split("/"))
        if not tbpath.exists():
            return False

        for item in tbpath.iterdir():
            if item.is_dir() and "=" in item.name and not item.name.startswith("."):
                return True
        return False

    def _get_partition_columns(self, tb_name: str) -> list[str]:
        """
        提取分区列名。

        Args:
            tb_name: 表名或路径。

        Returns:
            list[str]: 分区列名列表。
        """
        if not self._is_partitioned_table(tb_name):
            return []

        tbpath = self.base_path.joinpath(*tb_name.split("/"))
        partition_cols = set()

        for item in tbpath.iterdir():
            if item.is_dir() and "=" in item.name and not item.name.startswith("."):
                col_name = item.name.split("=")[0]
                partition_cols.add(col_name)

        return list(partition_cols)

    def put(
        self,
        df: pl.DataFrame | pl.LazyFrame,
        path: str,
        partitions: list[str] | None = None,
    ) -> None:
        """
        写入DataFrame到本地存储，自动识别写入模式。

        三种模式：
        - path 以 .parquet 结尾 -> 直接写入指定文件
        - path 是目录 + partitions -> Hive分区写入
        - path 是目录 -> 写入 data.parquet

        Args:
            df: 要写入的DataFrame或LazyFrame。
            path: 相对路径（相对于base_path）。
            partitions: 分区列名列表（可选）。

        Raises:
            FileOperationError: 写入失败。

        Examples:
            >>> store.put(df, "stocks")
            >>> store.put(df, "stocks/2024.parquet")
            >>> store.put(df, "stocks", partitions=["date"])
        """
        if isinstance(df, pl.LazyFrame):
            df = df.collect()
        try:
            target_path = self.base_path.joinpath(*path.split("/"))

            if path.endswith(".parquet"):
                target_path.parent.mkdir(parents=True, exist_ok=True)
                df.write_parquet(target_path)
            elif partitions:
                target_path.mkdir(parents=True, exist_ok=True)
                df.write_parquet(target_path, partition_by=partitions)
            else:
                target_path.mkdir(parents=True, exist_ok=True)
                df.write_parquet(target_path / "data.parquet")
        except Exception as e:
            raise FileOperationError(f"Failed to write to {path}: {e}", e) from e

    def has(self, path: str) -> bool:
        """
        判断路径是否存在。

        Args:
            path: 相对路径。

        Returns:
            bool: 路径是否存在。

        Examples:
            >>> store.has("stocks")
            True
        """
        return self.base_path.joinpath(*path.split("/")).exists()

    def read(self, path: str) -> pl.LazyFrame:
        """
        读取Parquet文件为LazyFrame。

        自动检测Hive分区表并启用hive_partitioning。

        Args:
            path: 相对路径。

        Returns:
            pl.LazyFrame: 懒加载数据框。

        Raises:
            PathError: 路径不存在。
            FileOperationError: 读取失败。

        Examples:
            >>> df = store.read("stocks").collect()
            >>> df = store.read("stocks").filter(pl.col("price") > 100).collect()
        """
        try:
            tbpath = self.base_path.joinpath(*path.split("/"))
            if not tbpath.exists():
                raise PathError(f"Path {path} does not exist")

            is_partitioned = self._is_partitioned_table(path)
            if is_partitioned:
                return pl.scan_parquet(tbpath / "**/*.parquet", hive_partitioning=True)
            else:
                return pl.scan_parquet(tbpath / "**/*.parquet")
        except Exception as e:
            if isinstance(e, (PathError, FileOperationError)):
                raise
            raise FileOperationError(f"Failed to read {path}: {e}", e) from e

    def list_tables(self) -> list[str]:
        """
        列出所有表名。

        Returns:
            list[str]: 表名列表。

        Examples:
            >>> store.list_tables()
            ['stocks', 'orders', 'users']
        """
        if not self.base_path.exists():
            return []

        tables = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                tables.append(item.name)
        return tables

    def get_table_info(self, tb_name: str) -> dict[str, Any]:
        """
        获取表的详细信息（实时扫描）。

        Args:
            tb_name: 表名。

        Returns:
            dict: 包含name、type、columns、dtypes、rows、partitions等字段。

        Raises:
            PathError: 表不存在。

        Examples:
            >>> store.get_table_info("stocks")
            {'name': 'stocks', 'type': 'simple', 'columns': ['date', 'symbol', 'price'], ...}
        """
        if not self.has(tb_name):
            raise PathError(f"Table {tb_name} does not exist")

        tbpath = self.base_path.joinpath(*tb_name.split("/"))
        df = self.read(tb_name).collect()

        is_partitioned = self._is_partitioned_table(tb_name)
        partitions = self._get_partition_columns(tb_name) if is_partitioned else None

        return {
            "name": tb_name,
            "type": "partitioned" if is_partitioned else "simple",
            "columns": list(df.columns),
            "dtypes": {
                col: str(dtype)
                for col, dtype in zip(df.columns, df.dtypes, strict=True)
            },
            "rows": len(df),
            "partitions": partitions,
            "created_at": datetime.fromtimestamp(tbpath.stat().st_ctime).isoformat(),
            "updated_at": datetime.fromtimestamp(tbpath.stat().st_mtime).isoformat(),
        }

    def delete_table(self, tb_name: str) -> None:
        """
        删除表。

        Args:
            tb_name: 表名。

        Raises:
            PathError: 表不存在。
            FileOperationError: 删除失败。

        Examples:
            >>> store.delete_table("old_table")
        """
        try:
            tbpath = self.base_path.joinpath(*tb_name.split("/"))
            if not tbpath.exists():
                raise PathError(f"Table {tb_name} does not exist")

            shutil.rmtree(tbpath)
        except Exception as e:
            if isinstance(e, PathError):
                raise
            raise FileOperationError(f"Failed to delete table {tb_name}: {e}", e) from e

    def rename_table(self, old_name: str, new_name: str) -> None:
        """
        重命名表。

        Args:
            old_name: 旧表名。
            new_name: 新表名。

        Raises:
            PathError: 表不存在或新表名已存在。
            FileOperationError: 重命名失败。

        Examples:
            >>> store.rename_table("old_table", "new_table")
        """
        try:
            old_path = self.base_path.joinpath(*old_name.split("/"))
            new_path = self.base_path.joinpath(*new_name.split("/"))

            if not old_path.exists():
                raise PathError(f"Table {old_name} does not exist")
            if new_path.exists():
                raise PathError(f"Table {new_name} already exists")

            old_path.rename(new_path)
        except Exception as e:
            if isinstance(e, PathError):
                raise
            raise FileOperationError(
                f"Failed to rename table {old_name} to {new_name}: {e}", e
            ) from e

    def copy_table(self, src_name: str, dst_name: str) -> None:
        """
        复制表。

        Args:
            src_name: 源表名。
            dst_name: 目标表名。

        Raises:
            PathError: 源表不存在或目标表已存在。
            FileOperationError: 复制失败。

        Examples:
            >>> store.copy_table("users", "users_backup")
        """
        try:
            src_path = self.base_path.joinpath(*src_name.split("/"))
            dst_path = self.base_path.joinpath(*dst_name.split("/"))

            if not src_path.exists():
                raise PathError(f"Table {src_name} does not exist")
            if dst_path.exists() and dst_path.is_dir() and any(dst_path.iterdir()):
                raise PathError(f"Table {dst_name} already exists")

            shutil.copytree(src_path, dst_path)
        except Exception as e:
            if isinstance(e, PathError):
                raise
            raise FileOperationError(
                f"Failed to copy table {src_name} to {dst_name}: {e}", e
            ) from e

    def optimize_table(self, tb_name: str) -> None:
        """
        优化表（合并小文件）。

        自动检测分区列并保持分区结构。

        Args:
            tb_name: 表名。

        Raises:
            PathError: 表不存在。
            FileOperationError: 优化失败。

        Examples:
            >>> store.optimize_table("fragmented_table")
        """
        try:
            if not self.has(tb_name):
                raise PathError(f"Table {tb_name} does not exist")

            partitions = self._get_partition_columns(tb_name) or None
            df = self.read(tb_name).collect()
            self.put(df, tb_name, partitions=partitions)
        except Exception as e:
            if isinstance(e, PathError):
                raise
            raise FileOperationError(
                f"Failed to optimize table {tb_name}: {e}", e
            ) from e

    def check_table(self, tb_name: str) -> bool:
        """
        检查表完整性。

        Args:
            tb_name: 表名。

        Returns:
            bool: 表是否完整可读。

        Examples:
            >>> store.check_table("stocks")
            True
        """
        try:
            if not self.has(tb_name):
                raise PathError(f"Table {tb_name} does not exist")

            self.read(tb_name)
            return True
        except Exception:
            return False

    def get_actual_mtime(self, tb_name: str) -> str:
        """
        获取表数据的实际修改时间。

        遍历所有Parquet文件获取最新修改时间。

        Args:
            tb_name: 表名。

        Returns:
            str: ISO格式时间戳。

        Raises:
            PathError: 表不存在。
            FileOperationError: 无Parquet文件。

        Examples:
            >>> store.get_actual_mtime("stocks")
            '2024-03-16T12:34:56.789012'
        """
        tbpath = self.base_path.joinpath(*tb_name.split("/"))
        if not tbpath.exists():
            raise PathError(f"Table {tb_name} does not exist")

        parquet_files = list(tbpath.rglob("*.parquet"))
        if not parquet_files:
            raise FileOperationError(f"No parquet files found in table {tb_name}")

        latest_mtime = max(f.stat().st_mtime for f in parquet_files)
        return datetime.fromtimestamp(latest_mtime).isoformat()
