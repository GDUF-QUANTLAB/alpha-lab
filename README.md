# Alpha Lab: High-Performance Alpha Mining System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Polars](https://img.shields.io/badge/Polars-Fast-orange.svg)](https://pola.rs/)

**Alpha Lab** 是一个专为量化金融研究设计的高性能数据处理与因子挖掘框架。它深度集成了现代 Python 数据技术栈（Polars, Apache Arrow, ClickHouse），旨在解决传统量化研究中数据加载慢、内存占用高、计算效率低等核心痛点。

通过采用惰性计算（Lazy Evaluation）和列式存储（Columnar Storage），Alpha Lab 能够在单机环境下高效处理 TB 级别的金融时序数据。

---

## 🌟 核心特性 (Features)

- **🚀 极致性能**: 基于 Rust 编写的 **Polars** 引擎，支持多线程并行计算、SIMD 优化及外存（Out-of-Core）处理。
- **💾 混合存储架构**:
    - **Blazestore**: 基于 Parquet 的本地数据仓库，支持自动分区管理、Hive分区结构和谓词下推，专为高频行情设计。
    - **ClickHouse**: 无缝集成 ClickHouse 数据库，适合海量截面数据的 OLAP 分析。
- **🛠 工程化工具箱 (Toolbox)**:
    - **Xcals**: 内置高精度中国市场交易日历，支持复杂的交易日推算、偏移及周期聚合。
    - **Ygo**: 针对 IO 密集型与 CPU 密集型任务优化的并发调度器，简化大规模数据清洗流程。
- **🔄 数据复用设计**: 独创的"统一视图"模式，无缝连接按天存储的行情数据（Market Data）与按表存储的基础信息（Inform Data），最大化 IO 效率。

## 📦 安装指南 (Installation)

### 环境要求
- OS: Linux / macOS / Windows (WSL推荐)
- Python: 3.9+

### 推荐安装 (使用 uv)
我们强烈推荐使用 [uv](https://github.com/astral-sh/uv) 进行极速环境构建与依赖管理：

```bash
# 1. 安装 uv
pip install uv

# 2. 快速同步环境（推荐）
# 这将自动创建虚拟环境并安装 pyproject.toml 中的所有依赖（包含开发依赖）
uv sync --all-extras

# 3. 激活环境
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 传统方式 (逐步执行)
如果您更习惯手动管理：

```bash
# 创建虚拟环境
uv venv

# 激活环境
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装项目依赖
uv pip install -e .[dev]
```

### 常规安装 (使用 pip)
```bash
pip install -e .[dev]
```

## ⚙️ 配置 (Configuration)

项目首次运行会自动在用户主目录 (`~`) 下生成必要的配置文件。

1. **交易日历配置** (`~/.xcals`)
    - 存放交易日历数据文件，确保 `xcals` 模块能正确计算交易日。

2. **Blazestore 配置** (`~/.blaze/config.toml`)
    - 配置本地数据仓库的存储路径。
    - 示例内容：
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

## 🚀 快速上手 (Quick Start)

### BlazeStore 使用示例

BlazeStore 提供本地 Parquet 存储和数据库集成的统一接口。

```python
import polars as pl
from blazestore import core

# 1. 写入数据（支持分区）
df = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-01", "2023-01-02"],
    "asset": ["000001", "000002", "000001"],
    "close": [10.5, 20.0, 10.6]
})

# 写入非分区表
core.put(df, tb_name="daily_bars")

# 写入分区表（Hive分区结构）
core.put(df, tb_name="daily_bars_partitioned", partitions=["date"])

# 2. 查询数据（SQL 风格，支持 Lazy Evaluation）
lazy_df = core.sql("SELECT * FROM daily_bars WHERE date = '2023-01-01'")

# 3. 执行计算
result = lazy_df.collect()
print(result)

# 4. 表管理
core.list_tables()  # 列出所有表
core.get_table_info("daily_bars")  # 获取表信息
core.delete_table("old_table")  # 删除表
core.rename_table("old_name", "new_name")  # 重命名表
core.copy_table("src_table", "dst_table")  # 复制表
core.optimize_table("fragmented_table")  # 优化表（合并小文件）
core.check_table("my_table")  # 检查表完整性
```

### 数据库集成

```python
from blazestore import MySQLClient, ClickHouseClient, read_mysql, write_mysql, read_ck

# 方式1：使用客户端类
mysql_client = MySQLClient()
df = mysql_client.read("SELECT * FROM users WHERE id = 1")

# 方式2：使用便捷函数
df = read_mysql("SELECT * FROM users WHERE id = 1")
write_mysql(df, "users_backup")

# ClickHouse 只读
df = read_ck("SELECT * FROM stocks WHERE date >= '2023-01-01'")
```

### 交易日历 (Xcals)

处理复杂的交易日逻辑。

```python
from tool_box.xcals import api

# 获取日期范围内的所有交易日
trading_days = api.get_tradingdays(beg_date="2023-01-01", end_date="2023-01-31")

# 计算 T+1 交易日
next_day = api.shift_tradeday("2023-01-20", 1)

# 判断是否为交易日
is_open = api.is_tradeday("2023-01-22")  # False (Sunday)
```

### 高级模式：数据清洗与复用

结合 `ygo` 并发调度与 `datacenter` 数据抽象，实现高效的数据清洗流水线。

```python
import polars as pl
from tool_box.ygo import Pool
import datacenter as dc

# 初始化并发池
pool = Pool(n_jobs=8)

# 定义任务：下载并清洗某日的行情数据
@pool.submit(job_name="clean_market_data")
def process_daily_data(date: str):
    # 逻辑层统一调用，底层自动路由到对应存储 (Parquet/DB)
    df = dc.md.read_kline_day(date, dc.Instrument.STOCK)
    cleaned_df = df.filter(pl.col("volume") > 0)
    # ... 存储逻辑
    return f"{date} done"

# 批量提交任务
for date in ["2023-01-01", "2023-01-02"]:
    process_daily_data(date=date)

# 执行并发任务
pool.do()
```

### 因子研究示例

对于因子研究员，我们提供了简洁的数据访问接口，无需了解底层存储细节。

```python
import polars as pl
import datacenter as dc
from tool_box import xcals

# 获取日期范围
start_date = "2023-01-01"
end_date = "2023-01-31"
trading_days = xcals.get_tradingdays(start_date, end_date)

# 读取股票日线数据
df = dc.md.read_data_batch(
    start_date,
    end_date,
    dc.Instrument.STOCK,
    dc.DataType.KLINE_DAY
)

# 计算因子：5日收益率
factor_df = df.with_columns(
    # 计算每日收益率
    daily_return=pl.col("close").pct_change(),
    # 计算5日收益率
    five_day_return=pl.col("close").pct_change(periods=5)
).filter(
    # 过滤掉无效数据
    pl.col("volume") > 0
)

# 展示结果
print(factor_df.head())
```

## 📂 项目结构 (Project Structure)

```text
alpha-lab/
├── tool_box/           # 核心基础设施
│   ├── xcals/          # 交易日历服务
│   ├── ygo/            # 并发任务调度器
│   └── clickhouse_df/  # ClickHouse 客户端封装
├── blazestore/         # 本地 Parquet 存储引擎
│   ├── core.py         # 本地存储 API
│   ├── local.py        # LocalStore 类实现
│   ├── clients/        # 数据库客户端
│   │   ├── mysql.py   # MySQL 客户端
│   │   └── clickhouse.py  # ClickHouse 客户端
│   ├── config.py       # 配置管理
│   ├── parse.py        # SQL 解析工具
│   └── exceptions.py    # 自定义异常
├── datacenter/         # 数据访问层 (Data Access Object)
│   ├── market_data/    # 行情数据接口
│   └── inform_data/    # 基础信息数据接口
├── tests/              # 单元测试集
├── pyproject.toml      # 项目依赖与配置
└── README.md           # 项目文档
```

## 🤝 贡献 (Contributing)

欢迎提交 Issue 和 Pull Request！在提交代码前，请确保通过以下检查：

1. **代码格式化**: 本项目使用 `ruff` 进行代码检查和格式化。
    ```bash
    # 检查代码
    ruff check .

    # 自动修复 Lint 错误
    ruff check . --fix

    # 格式化代码
    ruff format .
    ```
2. **运行测试**:
    ```bash
    pytest tests/
    ```

## 📄 许可证 (License)

本项目采用 [MIT 许可证](LICENSE) 开源。
