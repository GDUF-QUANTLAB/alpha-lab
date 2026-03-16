"""
BlazeStore核心模块测试
"""

import tempfile
from pathlib import Path

import polars as pl
import pytest

from blazestore import core


@pytest.fixture
def temp_store_path():
    """创建临时存储路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_store(temp_store_path):
    """创建临时存储实例"""
    from blazestore.local import LocalStore

    store = LocalStore(temp_store_path)
    core.set_local_store(store)
    return store


@pytest.fixture
def sample_df():
    """创建示例DataFrame"""
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 40, 45],
        }
    )


def test_tb_path(temp_store):
    """测试表路径生成"""
    path = temp_store.tb_path("my_table")
    assert path == temp_store.base_path / "my_table"

    path = temp_store.tb_path("data/stocks")
    assert path == temp_store.base_path / "data" / "stocks"


def test_put_and_has(temp_store, sample_df):
    """测试数据写入和表存在性检查"""
    table_name = "test_table"

    assert not temp_store.has(table_name)

    temp_store.put(sample_df, table_name)
    assert temp_store.has(table_name)

    table_path = temp_store.tb_path(table_name)
    assert (table_path / "data.parquet").exists()

    loaded_df = pl.read_parquet(table_path / "data.parquet")
    assert loaded_df.equals(sample_df)


def test_put_with_absolute_path(temp_store_path, sample_df):
    """测试使用绝对路径写入"""
    table_path = temp_store_path / "absolute_table"
    core.put(sample_df, str(table_path), abs_path=True)

    assert (table_path / "data.parquet").exists()

    loaded_df = pl.read_parquet(table_path / "data.parquet")
    assert loaded_df.equals(sample_df)


def test_sql_query(temp_store, sample_df):
    """测试SQL查询"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)

    query = f"SELECT * FROM {table_name} WHERE age > 30"
    result = core.sql(query, lazy=False)

    assert isinstance(result, pl.DataFrame)
    assert len(result) == 3
    assert list(result["name"]) == ["Charlie", "David", "Eve"]


def test_sql_lazy_query(temp_store, sample_df):
    """测试懒加载SQL查询"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)

    query = f"SELECT * FROM {table_name}"
    result = core.sql(query, lazy=True)

    assert isinstance(result, pl.LazyFrame)
    collected = result.collect()
    assert len(collected) == 5


def test_sql_with_absolute_path(temp_store_path, sample_df):
    """测试使用绝对路径的SQL查询"""
    table_path = temp_store_path / "test_table"
    core.put(sample_df, str(table_path), abs_path=True)

    query = f"SELECT * FROM {str(table_path)} WHERE age < 30"
    result = core.sql(query, abs_path=True, lazy=False)

    assert len(result) == 1
    assert result["name"][0] == "Alice"


def test_sql_multiple_tables(temp_store):
    """测试多表SQL查询"""
    df1 = pl.DataFrame({"id": [1, 2], "value": [10, 20]})
    df2 = pl.DataFrame({"id": [1, 2], "name": ["A", "B"]})

    temp_store.put(df1, "table1")
    temp_store.put(df2, "table2")

    query = "SELECT t1.id, t1.value, t2.name FROM table1 AS t1 JOIN table2 AS t2 ON t1.id = t2.id"
    result = core.sql(query, lazy=False)

    assert len(result) == 2
    assert list(result["id"]) == [1, 2]


def test_list_tables(temp_store, sample_df):
    """测试列出所有表"""
    assert len(temp_store.list_tables()) == 0

    temp_store.put(sample_df, "table1")
    temp_store.put(sample_df, "table2")

    tables = temp_store.list_tables()
    assert len(tables) == 2
    assert "table1" in tables
    assert "table2" in tables


def test_get_table_info(temp_store, sample_df):
    """测试获取表信息"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)

    info = temp_store.get_table_info(table_name)

    assert info["name"] == table_name
    assert info["type"] == "simple"
    assert len(info["columns"]) == 3
    assert info["rows"] == 5
    assert "version" in info


def test_delete_table(temp_store, sample_df):
    """测试删除表"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)
    assert temp_store.has(table_name)

    temp_store.delete_table(table_name)
    assert not temp_store.has(table_name)


def test_rename_table(temp_store, sample_df):
    """测试重命名表"""
    old_name = "old_table"
    new_name = "new_table"

    temp_store.put(sample_df, old_name)
    assert temp_store.has(old_name)
    assert not temp_store.has(new_name)

    temp_store.rename_table(old_name, new_name)
    assert not temp_store.has(old_name)
    assert temp_store.has(new_name)


def test_copy_table(temp_store, sample_df):
    """测试复制表"""
    src_name = "src_table"
    dst_name = "dst_table"

    temp_store.put(sample_df, src_name)
    assert temp_store.has(src_name)
    assert not temp_store.has(dst_name)

    temp_store.copy_table(src_name, dst_name)
    assert temp_store.has(src_name)
    assert temp_store.has(dst_name)


def test_optimize_table(temp_store, sample_df):
    """测试优化表"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)

    temp_store.optimize_table(table_name)
    assert temp_store.has(table_name)


def test_check_table(temp_store, sample_df):
    """测试检查表完整性"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)

    assert temp_store.check_table(table_name) is True
