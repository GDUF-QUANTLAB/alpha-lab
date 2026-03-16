"""
本地存储管理类

提供本地Parquet文件的完整管理功能，支持非分区表和Hive分区表。
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from .config import get_settings
from .exceptions import FileOperationError, PathError

DB_PATH = get_settings().get("paths.store")


class LocalStore:
    """
    本地存储管理类。

    提供本地Parquet文件的完整管理功能，支持非分区表和Hive分区表。
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """
        初始化本地存储。

        Args:
            base_path: 基础路径，默认为配置中的store路径
        """
        self.base_path = base_path or Path(DB_PATH)

    def tb_path(self, tb_name: str) -> Path:
        """
        获取表的完整路径。

        Args:
            tb_name: 表名

        Returns:
            Path: 表的完整路径
        """
        return self.base_path / tb_name

    def metadata_path(self, tb_name: str) -> Path:
        """
        获取元数据文件的路径。

        Args:
            tb_name: 表名

        Returns:
            Path: 元数据文件路径
        """
        return self.tb_path(tb_name) / ".metadata.json"

    def _is_partitioned_table(self, tb_name: str) -> bool:
        """
        检测表是否为分区表。

        Args:
            tb_name: 表名

        Returns:
            bool: 是否为分区表
        """
        tbpath = self.tb_path(tb_name)
        if not tbpath.exists():
            return False

        for item in tbpath.iterdir():
            if item.is_dir() and "=" in item.name and not item.name.startswith("."):
                return True
        return False

    def _get_partition_columns(self, tb_name: str) -> list[str]:
        """
        提取分区列。

        Args:
            tb_name: 表名

        Returns:
            list[str]: 分区列列表
        """
        if not self._is_partitioned_table(tb_name):
            return []

        tbpath = self.tb_path(tb_name)
        partition_cols = set()

        for item in tbpath.iterdir():
            if item.is_dir() and "=" in item.name and not item.name.startswith("."):
                col_name = item.name.split("=")[0]
                partition_cols.add(col_name)

        return list(partition_cols)

    def put(
        self,
        df: pl.DataFrame,
        tb_name: str,
        partitions: list[str] | None = None,
    ) -> None:
        """
        将DataFrame写入本地存储。

        Args:
            df: 要写入的DataFrame
            tb_name: 表名
            partitions: 分区列名列表

        Raises:
            FileOperationError: 文件写入失败
        """
        try:
            tbpath = self.tb_path(tb_name)
            if not tbpath.exists():
                tbpath.mkdir(parents=True, exist_ok=True)

            if partitions is not None:
                df.write_parquet(tbpath, partition_by=partitions)
            else:
                df.write_parquet(tbpath / "data.parquet")

            self._update_metadata(tb_name, df, partitions)
        except Exception as e:
            raise FileOperationError(f"Failed to write table {tb_name}: {e}", e) from e

    def has(self, tb_name: str) -> bool:
        """
        判断表是否存在。

        Args:
            tb_name: 表名

        Returns:
            bool: 表是否存在
        """
        return self.tb_path(tb_name).exists()

    def read(self, tb_name: str) -> pl.DataFrame:
        """
        读取表数据。

        Args:
            tb_name: 表名

        Returns:
            pl.DataFrame: 表数据

        Raises:
            PathError: 表不存在
            FileOperationError: 文件读取失败
        """
        try:
            tbpath = self.tb_path(tb_name)
            if not tbpath.exists():
                raise PathError(f"Table {tb_name} does not exist")

            parquet_files = list(tbpath.rglob("*.parquet"))
            if not parquet_files:
                raise FileOperationError(f"No parquet files found in table {tb_name}")

            return pl.read_parquet(tbpath / "**/*.parquet")
        except Exception as e:
            if isinstance(e, (PathError, FileOperationError)):
                raise
            raise FileOperationError(f"Failed to read table {tb_name}: {e}", e) from e

    def list_tables(self) -> list[str]:
        """
        列出所有表。

        Returns:
            list[str]: 表名列表
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
        获取表的详细信息。

        Args:
            tb_name: 表名

        Returns:
            dict[str, Any]: 表信息字典

        Raises:
            PathError: 表不存在
        """
        if not self.has(tb_name):
            raise PathError(f"Table {tb_name} does not exist")

        metadata = self._load_metadata(tb_name)
        if metadata:
            return metadata

        tbpath = self.tb_path(tb_name)
        df = self.read(tb_name)

        is_partitioned = self._is_partitioned_table(tb_name)
        partitions = self._get_partition_columns(tb_name) if is_partitioned else None

        info = {
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

        info["version"] = self._compute_version(info)
        return info

    def delete_table(self, tb_name: str) -> None:
        """
        删除表。

        Args:
            tb_name: 表名

        Raises:
            PathError: 表不存在
            FileOperationError: 删除失败
        """
        try:
            tbpath = self.tb_path(tb_name)
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
            old_name: 旧表名
            new_name: 新表名

        Raises:
            PathError: 表不存在或新表名已存在
            FileOperationError: 重命名失败
        """
        try:
            old_path = self.tb_path(old_name)
            new_path = self.tb_path(new_name)

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
            src_name: 源表名
            dst_name: 目标表名

        Raises:
            PathError: 源表不存在或目标表已存在
            FileOperationError: 复制失败
        """
        try:
            src_path = self.tb_path(src_name)
            dst_path = self.tb_path(dst_name)

            if not src_path.exists():
                raise PathError(f"Table {src_name} does not exist")
            if dst_path.exists():
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

        Args:
            tb_name: 表名

        Raises:
            PathError: 表不存在
            FileOperationError: 优化失败
        """
        try:
            if not self.has(tb_name):
                raise PathError(f"Table {tb_name} does not exist")

            metadata = self._load_metadata(tb_name)
            partitions = metadata.get("partitions") if metadata else None

            df = self.read(tb_name)
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
            tb_name: 表名

        Returns:
            bool: 表是否完整

        Raises:
            PathError: 表不存在
        """
        try:
            if not self.has(tb_name):
                raise PathError(f"Table {tb_name} does not exist")

            self.read(tb_name)
            return True
        except Exception:
            return False

    def _update_metadata(
        self, tb_name: str, df: pl.DataFrame, partitions: list[str] | None
    ) -> None:
        """
        更新表元数据。

        Args:
            tb_name: 表名
            df: DataFrame
            partitions: 分区列名列表
        """
        tbpath = self.tb_path(tb_name)
        metadata_path = self.metadata_path(tb_name)

        is_partitioned = partitions is not None
        info = {
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

        info["version"] = self._compute_version(info)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

    def _load_metadata(self, tb_name: str) -> dict[str, Any] | None:
        """
        加载表元数据。

        Args:
            tb_name: 表名

        Returns:
            dict[str, Any] | None: 元数据字典，如果不存在返回None
        """
        metadata_path = self.metadata_path(tb_name)
        if not metadata_path.exists():
            return None

        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)

    def _compute_version(self, info: dict[str, Any]) -> str:
        """
        计算数据版本（基于元数据）。

        Args:
            info: 元数据字典

        Returns:
            str: 版本号
        """
        rows = info.get("rows", 0)
        col_count = len(info.get("columns", []))
        updated_at = info.get("updated_at", datetime.now().isoformat())

        timestamp = updated_at.replace("-", "").replace(":", "").replace("T", "")[:14]
        return f"{rows}_{col_count}_{timestamp}"
