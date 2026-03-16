"""
MySQL数据库客户端
"""

from __future__ import annotations

import urllib

import polars as pl

from ..config import get_settings
from ..exceptions import ConnectionError, QueryError, WriteError


class MySQLClient:
    """
    MySQL数据库客户端。

    提供MySQL数据库的读写功能。
    """

    def __init__(self, db_conf: str = "databases.mysql") -> None:
        """
        初始化MySQL客户端。

        Args:
            db_conf: 配置键名，默认为"databases.mysql"

        Raises:
            ConfigError: 配置缺失
        """
        self.db_conf = db_conf
        self._uri = self._build_uri()

    def _build_uri(self) -> str:
        """
        构建数据库连接URI。

        Returns:
            str: 数据库连接URI

        Raises:
            ConfigError: 配置缺失
        """
        db_setting = get_settings().get(self.db_conf, {})
        required_keys = ["user", "password", "url"]
        missing_keys = [key for key in required_keys if key not in db_setting]
        if missing_keys:
            from ..exceptions import ConfigError

            raise ConfigError(
                f"Missing required keys in database config: {missing_keys}"
            )

        user = urllib.parse.quote_plus(db_setting["user"])
        password = urllib.parse.quote_plus(db_setting["password"])
        return f"mysql://{user}:{password}@{db_setting['url']}"

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
            return pl.read_database_uri(query, self._uri)
        except Exception as e:
            if "connection" in str(e).lower():
                raise ConnectionError(f"Failed to connect to MySQL: {e}", e) from e
            raise QueryError(f"Failed to execute MySQL query: {e}", e) from e

    def write(self, df: pl.DataFrame, table_name: str) -> None:
        """
        将DataFrame写入数据库表。

        Args:
            df: 要写入的DataFrame
            table_name: 目标表名

        Raises:
            ConnectionError: 数据库连接失败
            WriteError: 数据写入失败
        """
        try:
            db_setting = get_settings().get(self.db_conf, {})
            user = urllib.parse.quote_plus(db_setting["user"])
            password = urllib.parse.quote_plus(db_setting["password"])
            write_uri = f"mysql+pymysql://{user}:{password}@{db_setting['url']}"

            df.write_database(
                table_name=f"{db_setting.get('database')}.{table_name}",
                connection=write_uri,
                if_table_exists="append",
            )
        except Exception as e:
            if "connection" in str(e).lower():
                raise ConnectionError(f"Failed to connect to MySQL: {e}", e) from e
            raise WriteError(
                f"Failed to write to MySQL table {table_name}: {e}", e
            ) from e
