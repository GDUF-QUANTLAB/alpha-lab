"""
BlazeStore表游标模块测试
"""

import tempfile
from pathlib import Path

import polars as pl
import pytest

from blazestore import core
from blazestore.cursor import TableCursor
from blazestore.cursor import cursor as create_cursor


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


@pytest.fixture
def sample_table(temp_store, sample_df):
    """创建示例表"""
    table_name = "test_table"
    temp_store.put(sample_df, table_name)
    return table_name


def test_cursor_creation(temp_store):
    """测试创建游标"""
    tbl = TableCursor("my_table")
    assert tbl.tb_name == "my_table"


def test_cursor_function(temp_store):
    """测试cursor函数"""
    tbl = create_cursor("my_table")
    assert isinstance(tbl, TableCursor)
    assert tbl.tb_name == "my_table"


def test_cursor_exists(temp_store, sample_table):
    """测试游标exists方法"""
    tbl = TableCursor(sample_table)
    assert tbl.exists() is True

    tbl2 = TableCursor("non_existent_table")
    assert tbl2.exists() is False


def test_cursor_info(temp_store, sample_table, sample_df):
    """测试游标info方法"""
    tbl = TableCursor(sample_table)
    info = tbl.info()

    assert info["name"] == sample_table
    assert info["type"] == "simple"
    assert len(info["columns"]) == 3
    assert info["rows"] == 5


def test_cursor_path(temp_store, sample_table):
    """测试游标path方法"""
    tbl = TableCursor(sample_table)
    path = tbl.path()

    assert isinstance(path, Path)
    assert path.name == sample_table


def test_cursor_mtime(temp_store, sample_table):
    """测试游标mtime方法"""
    tbl = TableCursor(sample_table)
    mtime = tbl.mtime()

    assert isinstance(mtime, str)
    assert len(mtime) > 0


def test_cursor_read(temp_store, sample_table, sample_df):
    """测试游标read方法"""
    tbl = TableCursor(sample_table)
    df = tbl.read().collect()

    assert isinstance(df, pl.DataFrame)
    assert len(df) == 5
    assert list(df.columns) == ["id", "name", "age"]


def test_cursor_sql(temp_store, sample_table):
    """测试游标sql方法"""
    tbl = TableCursor(sample_table)
    result = tbl.sql("SELECT * FROM test_table WHERE age > 30", lazy=False)

    assert isinstance(result, pl.DataFrame)
    assert len(result) == 3
    assert list(result["name"]) == ["Charlie", "David", "Eve"]


def test_cursor_sql_lazy(temp_store, sample_table):
    """测试游标sql方法（懒加载）"""
    tbl = TableCursor(sample_table)
    result = tbl.sql("SELECT * FROM test_table", lazy=True)

    assert isinstance(result, pl.LazyFrame)
    collected = result.collect()
    assert len(collected) == 5


def test_cursor_write(temp_store, sample_df):
    """测试游标write方法"""
    table_name = "new_table"
    tbl = TableCursor(table_name)

    assert not tbl.exists()

    tbl.write(sample_df)
    assert tbl.exists()

    df = tbl.read().collect()
    assert len(df) == 5


def test_cursor_write_with_partitions(temp_store, sample_df):
    """测试游标write方法（分区）"""
    table_name = "partitioned_table"
    tbl = TableCursor(table_name)

    tbl.write(sample_df, partitions=["name"])
    assert tbl.exists()

    df = tbl.read().collect()
    assert len(df) == 5


def test_cursor_delete(temp_store, sample_table):
    """测试游标delete方法"""
    tbl = TableCursor(sample_table)
    assert tbl.exists()

    tbl.delete()
    assert not tbl.exists()


def test_cursor_rename(temp_store, sample_table):
    """测试游标rename方法"""
    old_name = sample_table
    new_name = "renamed_table"

    tbl = TableCursor(old_name)
    assert tbl.exists()
    assert tbl.tb_name == old_name

    tbl.rename(new_name)
    assert tbl.tb_name == new_name

    tbl2 = TableCursor(old_name)
    assert not tbl2.exists()

    tbl3 = TableCursor(new_name)
    assert tbl3.exists()


def test_cursor_copy(temp_store, sample_table):
    """测试游标copy方法"""
    src_name = sample_table
    dst_name = "copied_table"

    tbl = TableCursor(src_name)
    assert tbl.exists()

    tbl.copy(dst_name)

    tbl2 = TableCursor(dst_name)
    assert tbl2.exists()

    src_df = tbl.read().collect()
    dst_df = tbl2.read().collect()
    assert src_df.equals(dst_df)


def test_cursor_optimize(temp_store, sample_table):
    """测试游标optimize方法"""
    tbl = TableCursor(sample_table)
    assert tbl.exists()

    tbl.optimize()
    assert tbl.exists()


def test_cursor_check(temp_store, sample_table):
    """测试游标check方法"""
    tbl = TableCursor(sample_table)
    assert tbl.exists()

    assert tbl.check() is True


def test_cursor_workflow(temp_store, sample_df):
    """测试游标完整工作流"""
    table_name = "workflow_table"
    tbl = TableCursor(table_name)

    assert not tbl.exists()

    tbl.write(sample_df)
    assert tbl.exists()

    info = tbl.info()
    assert info["rows"] == 5

    df = tbl.read().collect()
    assert len(df) == 5

    result = tbl.sql("SELECT * FROM workflow_table WHERE age > 30", lazy=False)
    assert len(result) == 3

    assert tbl.check() is True

    tbl.optimize()

    new_name = "renamed_workflow_table"
    tbl.rename(new_name)
    assert tbl.tb_name == new_name

    backup_name = "backup_workflow_table"
    tbl.copy(backup_name)

    tbl.delete()
    assert not tbl.exists()

    backup_tbl = TableCursor(backup_name)
    assert backup_tbl.exists()

    backup_tbl.delete()


def test_cursor_cross_platform_paths(temp_store_path, sample_df):
    """测试跨平台路径处理"""
    from blazestore.local import LocalStore

    store = LocalStore(temp_store_path)
    core.set_local_store(store)

    table_name = "test_table"
    store.put(sample_df, table_name)

    tbl = TableCursor(table_name)
    path = tbl.path()

    assert path.exists()
    assert isinstance(path, Path)
