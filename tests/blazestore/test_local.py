"""
blazestore.local 测试
"""

import tempfile
from pathlib import Path

import polars as pl
import pytest

from blazestore.exceptions import PathError
from blazestore.local import LocalStore


@pytest.fixture
def temp_store():
    """创建临时存储"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalStore(base_path=tmpdir)
        yield store


@pytest.fixture
def sample_df():
    """创建示例 DataFrame"""
    return pl.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "symbol": ["AAPL", "MSFT", "GOOG"],
            "price": [150.0, 250.0, 100.0],
            "volume": [1000, 2000, 3000],
        }
    )


def test_local_store_init(temp_store):
    """测试 LocalStore 初始化"""
    assert temp_store.base_path.exists()
    assert isinstance(temp_store.base_path, Path)


def test_local_store_init_with_path_object():
    """测试 LocalStore 使用 Path 初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        store = LocalStore(base_path=base_path)
        assert store.base_path == base_path


def test_put_simple_table(temp_store, sample_df):
    """测试写入简单表"""
    temp_store.put(sample_df, "stocks")

    assert temp_store.has("stocks")
    assert (temp_store.base_path / "stocks" / "data.parquet").exists()


def test_put_with_filename(temp_store, sample_df):
    """测试写入指定文件名"""
    temp_store.put(sample_df, "stocks/2024.parquet")

    assert temp_store.has("stocks/2024.parquet")
    assert (temp_store.base_path / "stocks" / "2024.parquet").exists()


def test_put_partitioned(temp_store, sample_df):
    """测试写入分区表"""
    temp_store.put(sample_df, "stocks_partitioned", partitions=["date"])

    assert temp_store.has("stocks_partitioned")
    assert temp_store._is_partitioned_table("stocks_partitioned")


def test_put_lazyframe(temp_store):
    """测试写入 LazyFrame"""
    lazy_df = pl.LazyFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    temp_store.put(lazy_df, "test_lazy")

    assert temp_store.has("test_lazy")


def test_has(temp_store, sample_df):
    """测试检查路径是否存在"""
    temp_store.put(sample_df, "stocks")

    assert temp_store.has("stocks") is True
    assert temp_store.has("nonexistent") is False


def test_read_simple_table(temp_store, sample_df):
    """测试读取简单表"""
    temp_store.put(sample_df, "stocks")

    df = temp_store.read("stocks").collect()

    assert len(df) == 3
    assert set(df.columns) == {"date", "symbol", "price", "volume"}


def test_read_partitioned_table(temp_store, sample_df):
    """测试读取分区表"""
    temp_store.put(sample_df, "stocks_partitioned", partitions=["date"])

    df = temp_store.read("stocks_partitioned").collect()

    assert len(df) == 3
    assert "date" in df.columns


def test_read_nonexistent_table(temp_store):
    """测试读取不存在的表"""
    with pytest.raises(PathError):
        temp_store.read("nonexistent")


def test_list_tables(temp_store, sample_df):
    """测试列出所有表"""
    temp_store.put(sample_df, "stocks")
    temp_store.put(sample_df, "orders")

    tables = temp_store.list_tables()

    assert len(tables) == 2
    assert "stocks" in tables
    assert "orders" in tables


def test_list_tables_empty(temp_store):
    """测试列出空存储的表"""
    tables = temp_store.list_tables()
    assert tables == []


def test_get_table_info(temp_store, sample_df):
    """测试获取表信息"""
    temp_store.put(sample_df, "stocks")

    info = temp_store.get_table_info("stocks")

    assert info["name"] == "stocks"
    assert info["type"] == "simple"
    assert len(info["columns"]) == 4
    assert info["rows"] == 3
    assert info["partitions"] is None


def test_get_table_info_partitioned(temp_store, sample_df):
    """测试获取分区表信息"""
    temp_store.put(sample_df, "stocks", partitions=["date"])

    info = temp_store.get_table_info("stocks")

    assert info["type"] == "partitioned"
    assert info["partitions"] == ["date"]


def test_get_table_info_nonexistent(temp_store):
    """测试获取不存在表的信息"""
    with pytest.raises(PathError):
        temp_store.get_table_info("nonexistent")


def test_delete_table(temp_store, sample_df):
    """测试删除表"""
    temp_store.put(sample_df, "stocks")

    temp_store.delete_table("stocks")

    assert temp_store.has("stocks") is False


def test_delete_table_nonexistent(temp_store):
    """测试删除不存在的表"""
    with pytest.raises(PathError):
        temp_store.delete_table("nonexistent")


def test_rename_table(temp_store, sample_df):
    """测试重命名表"""
    temp_store.put(sample_df, "old_name")

    temp_store.rename_table("old_name", "new_name")

    assert temp_store.has("old_name") is False
    assert temp_store.has("new_name") is True


def test_rename_table_nonexistent(temp_store):
    """测试重命名不存在的表"""
    with pytest.raises(PathError):
        temp_store.rename_table("nonexistent", "new_name")


def test_copy_table(temp_store, sample_df):
    """测试复制表"""
    temp_store.put(sample_df, "source")

    temp_store.copy_table("source", "destination")

    assert temp_store.has("source") is True
    assert temp_store.has("destination") is True

    source_df = temp_store.read("source").collect()
    dest_df = temp_store.read("destination").collect()

    assert len(source_df) == len(dest_df)


def test_copy_table_nonexistent(temp_store):
    """测试复制不存在的表"""
    with pytest.raises(PathError):
        temp_store.copy_table("nonexistent", "destination")


def test_optimize_table(temp_store, sample_df):
    """测试优化表"""
    temp_store.put(sample_df, "stocks", partitions=["date"])

    temp_store.optimize_table("stocks")

    assert temp_store.has("stocks")
    assert temp_store._is_partitioned_table("stocks")


def test_optimize_table_nonexistent(temp_store):
    """测试优化不存在的表"""
    with pytest.raises(PathError):
        temp_store.optimize_table("nonexistent")


def test_check_table(temp_store, sample_df):
    """测试检查表完整性"""
    temp_store.put(sample_df, "stocks")

    assert temp_store.check_table("stocks") is True
    assert temp_store.check_table("nonexistent") is False


def test_get_actual_mtime(temp_store, sample_df):
    """测试获取实际修改时间"""
    temp_store.put(sample_df, "stocks")

    mtime = temp_store.get_actual_mtime("stocks")

    assert isinstance(mtime, str)
    assert "T" in mtime


def test_get_actual_mtime_nonexistent(temp_store):
    """测试获取不存在表的修改时间"""
    with pytest.raises(PathError):
        temp_store.get_actual_mtime("nonexistent")


def test_is_partitioned_table(temp_store, sample_df):
    """测试检测分区表"""
    temp_store.put(sample_df, "simple")
    temp_store.put(sample_df, "partitioned", partitions=["date"])

    assert temp_store._is_partitioned_table("simple") is False
    assert temp_store._is_partitioned_table("partitioned") is True


def test_get_partition_columns(temp_store, sample_df):
    """测试获取分区列"""
    temp_store.put(sample_df, "partitioned", partitions=["date"])

    partitions = temp_store._get_partition_columns("partitioned")

    assert partitions == ["date"]


def test_get_partition_columns_simple(temp_store, sample_df):
    """测试获取简单表的分区列"""
    temp_store.put(sample_df, "simple")

    partitions = temp_store._get_partition_columns("simple")

    assert partitions == []
