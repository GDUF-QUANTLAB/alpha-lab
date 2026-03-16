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
- **💾 高效存储**: 基于 Parquet 的本地数据仓库，支持自动分区管理、Hive分区结构和谓词下推，专为高频行情设计。
- **🛠 交易日历 (Xcals)**: 内置高精度中国市场交易日历，支持复杂的交易日推算、偏移及周期聚合。
- **🔄 数据访问层 (Datacenter)**: 独创的"统一视图"模式，无缝连接按天存储的行情数据（Market Data）与按表存储的基础信息（Inform Data），最大化 IO 效率。

## 📦 安装指南 (Installation)

### 环境要求
- OS: Linux / macOS / Windows (WSL推荐)
- Python: 3.9+

### 从 PyPI 安装（推荐）

```bash
pip install alpha-lab
```

### 从源码安装

如果需要从源码安装，我们推荐使用 [uv](https://github.com/astral-sh/uv) 进行极速环境构建与依赖管理：

```bash
# 1. 安装 uv
pip install uv

# 2. 克隆仓库
git clone https://github.com/yourusername/alpha-lab.git
cd alpha-lab

# 3. 同步环境
uv sync --all-extras

# 4. 激活环境
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 传统方式

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装项目依赖
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

## 🚀 因子研究示例

对于因子研究员，我们提供了简洁的数据访问接口，无需了解底层存储细节。

### 交易日历使用

```python
from tool_box.xcals import api

# 获取日期范围内的所有交易日
trading_days = api.get_tradingdays(beg_date="2023-01-01", end_date="2023-01-31")

# 计算 T+1 交易日
next_day = api.shift_tradeday("2023-01-20", 1)

# 判断是否为交易日
is_open = api.is_tradeday("2023-01-22")  # False (Sunday)
```

### 读取行情数据

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

### 读取基础信息

```python
import datacenter as dc

# 读取股票基本信息
stock_info = dc.id.get_stock_info()

# 读取行业分类
industry = dc.id.get_industry_classification()

# 读取指数成分
index_constituents = dc.id.get_index_constituents("000001.SH")
```

## 📄 许可证 (License)

本项目采用 [MIT 许可证](LICENSE) 开源。
