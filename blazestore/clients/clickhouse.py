"""
ClickHouse数据库客户端
"""

from __future__ import annotations

import urllib

import polars as pl

from tool_box import clickhouse_df

from ..config import get_settings
from ..exceptions import ConfigError, ConnectionError, QueryError


class ClickHouseClient:
    """
    ClickHouse数据库客户端。

    提供ClickHouse数据库的读取功能。
    """

    def __init__(self, db_conf: str = "databases.ck") -> None:
        """
        初始化ClickHouse客户端。

        Args:
            db_conf: 配置键名，默认为"databases.ck"

        Raises:
            ConfigError: 配置缺失
        """
        self.db_conf = db_conf
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """
        加载数据库配置。

        Returns:
            dict: 数据库配置

        Raises:
            ConfigError: 配置缺失
        """
        db_setting = get_settings().get(self.db_conf, {})
        required_keys = ["user", "password", "urls"]
        missing_keys = [key for key in required_keys if key not in db_setting]
        if missing_keys:
            raise ConfigError(
                f"Missing required keys in database config: {missing_keys}"
            )

        return db_setting

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
        try:
            user = urllib.parse.quote_plus(self._config["user"])
            password = urllib.parse.quote_plus(self._config["password"])

            with clickhouse_df.connect(
                self._config["urls"], user=user, password=password
            ):
                return clickhouse_df.to_polars(query)
        except Exception as e:
            if "connection" in str(e).lower():
                raise ConnectionError(f"Failed to connect to ClickHouse: {e}", e) from e
            raise QueryError(f"Failed to execute ClickHouse query: {e}", e) from e
