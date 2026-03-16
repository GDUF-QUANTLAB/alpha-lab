"""
BlazeStore数据库客户端测试
"""

import pytest

from blazestore.clients import read_ck, read_mysql, write_mysql
from blazestore.exceptions import ConfigError


def test_read_mysql_missing_config():
    """测试MySQL读取配置缺失"""
    with pytest.raises(ConfigError, match="Missing required keys"):
        read_mysql("SELECT * FROM test", db_conf="nonexistent.config")


def test_write_mysql_missing_config():
    """测试MySQL写入配置缺失"""
    import polars as pl

    df = pl.DataFrame({"id": [1]})
    with pytest.raises(ConfigError, match="Missing required keys"):
        write_mysql(df, "test_table", db_conf="nonexistent.config")


def test_read_ck_missing_config():
    """测试ClickHouse读取配置缺失"""
    with pytest.raises(ConfigError, match="Missing required keys"):
        read_ck("SELECT * FROM test", db_conf="nonexistent.config")
