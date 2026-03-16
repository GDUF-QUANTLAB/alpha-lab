# BlazeStore

BlazeStore 是一个高性能的本地数据仓库和数据库集成模块，专为量化金融研究设计。它基于 Parquet 文件格式，提供本地存储、SQL 查询以及 MySQL/ClickHouse 数据库集成功能。

## 核心特性

- **本地 Parquet 存储**: 基于 Polars 的高性能列式存储，支持简单表和 Hive 分区表
- **SQL 查询支持**: 通过 Polars SQL 引擎执行 SQL 查询，支持复杂的数据分析
- **数据库集成**: 无缝集成 MySQL 和 ClickHouse，提供统一的数据访问接口
- **元数据管理**: 自动维护表元数据，包括版本、分区、数据类型等信息
- **表管理功能**: 完整的 CRUD 操作，包括重命名、复制、优化和完整性检查

## 快速开始

### 配置

首次使用时，BlazeStore 会在 `~/.blaze/config.toml` 自动创建配置文件：

```toml
[paths]
store = "/home/user/BlazeStore"

[databases.mysql]
user = "your_user"
password = "your_password"
url = "localhost:3306/database_name"
database = "database_name"

[databases.ck]
user = "your_user"
password = "your_password"
urls = "localhost:8123"
```

### 本地存储

```python
import polars as pl
from blazestore import put, sql, has, list_tables

# 写入数据
df = pl.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35]
})
put(df, "users")

# 检查表是否存在
has("users")  # True

# SQL 查询
result = sql("SELECT * FROM users WHERE age > 25")

# 列出所有表
tables = list_tables()
```

### 分区表

```python
# 写入分区表
df = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-01", "2023-01-02"],
    "symbol": ["AAPL", "MSFT", "AAPL"],
    "price": [150.0, 250.0, 151.0]
})
put(df, "stocks", partitions=["date"])

# 查询分区表
result = sql("SELECT * FROM stocks WHERE date = '2023-01-01'")
```

### MySQL 集成

```python
from blazestore import read_mysql, write_mysql

# 读取 MySQL 数据
df = read_mysql("SELECT * FROM users WHERE age > 25")

# 写入 MySQL 数据
write_mysql(df, "users_backup")
```

### ClickHouse 集成

```python
from blazestore import read_ck

# 读取 ClickHouse 数据
df = read_ck("SELECT * FROM stocks WHERE date >= '2023-01-01'")
```

## API 文档

### 本地存储 API

#### 数据操作

- `put(df, tb_name, partitions=None, abs_path=False)` - 写入数据到表
- `has(tb_name)` - 检查表是否存在
- `sql(query, abs_path=False, lazy=True)` - 执行 SQL 查询

#### 表管理

- `list_tables()` - 列出所有表
- `get_table_info(tb_name)` - 获取表的详细信息
- `delete_table(tb_name)` - 删除表
- `rename_table(old_name, new_name)` - 重命名表
- `copy_table(src_name, dst_name)` - 复制表
- `optimize_table(tb_name)` - 优化表（合并小文件）
- `check_table(tb_name)` - 检查表完整性

#### 路径管理

- `tb_path(tb_name)` - 获取表的完整路径

### 数据库客户端 API

#### MySQL

- `read_mysql(query, db_conf="databases.mysql")` - 从 MySQL 读取数据
- `write_mysql(df, tb_name, db_conf="databases.mysql")` - 写入数据到 MySQL
- `MySQLClient(db_conf)` - MySQL 客户端类

#### ClickHouse

- `read_ck(query, db_conf="databases.ck")` - 从 ClickHouse 读取数据
- `ClickHouseClient(db_conf)` - ClickHouse 客户端类

### 配置管理

- `get_settings()` - 获取配置对象
- `set_local_store(store)` - 设置本地存储实例
- `get_local_store()` - 获取当前本地存储实例

## 异常处理

BlazeStore 定义了完整的异常体系：

- `ConfigError` - 配置错误
- `ConnectionError` - 数据库连接错误
- `QueryError` - 查询执行错误
- `WriteError` - 数据写入错误
- `FileOperationError` - 文件操作错误
- `PathError` - 路径错误
- `PartitionError` - 分区错误

## 高级功能

### 懒加载查询

```python
# 返回 LazyFrame，延迟执行
lazy_result = sql("SELECT * FROM large_table", lazy=True)

# 执行计算
df = lazy_result.collect()
```

### 绝对路径支持

```python
# 使用绝对路径写入
put(df, "/tmp/custom_table", abs_path=True)

# 使用绝对路径查询
result = sql("SELECT * FROM /tmp/custom_table", abs_path=True)
```

### 表优化

```python
# 合并小文件，提升查询性能
optimize_table("fragmented_table")
```

## 性能优化建议

1. **使用分区表**: 对于大数据量表，按日期或类别分区可显著提升查询性能
2. **懒加载查询**: 使用 `lazy=True` 延迟执行，优化查询计划
3. **定期优化**: 对频繁写入的表定期执行 `optimize_table` 合并小文件
4. **谓词下推**: SQL 查询中的 WHERE 条件会自动下推到 Parquet 文件读取

## 测试

运行测试：

```bash
pytest tests/blazestore/
```

## 依赖项

- polars >= 1.38.1
- pyarrow >= 23.0.0
- clickhouse-driver >= 0.2.6
- dynaconf >= 3.2.12
- sqlparse >= 0.5.5
- loguru >= 0.7.0

## 许可证

MIT License
