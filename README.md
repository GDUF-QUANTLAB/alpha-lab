# Alpha Lab

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Polars](https://img.shields.io/badge/Polars-Fast-orange.svg)](https://pola.rs/)

专为因子研究员设计的数据处理与因子挖掘框架，提供交易日历、数据访问和因子分析的一体化工具。

---

## 安装

```bash
# 使用 uv 安装（推荐）
uv pip install alpha-lab

# 或使用 pip
pip install alpha-lab
```

---

## 快速开始

### 1. 读取数据

下面的数据读取示例假设本地数据源和 `datacenter` 相关配置已经就绪。

```python
import polars as pl
import datacenter as dc
import xcals

# 获取交易日列表
trading_days = xcals.get_tradingdays("2023-01-01", "2023-01-31")

# 读取股票日线数据
df = dc.md.read_data_batch(
    beg_date="2023-01-01",
    end_date="2023-01-31",
    instrument=dc.Instrument.STOCK,
    datatype=dc.DataType.KLINE_DAY,
)

# 读取基础信息
stocks = dc.jy.asset(date="2023-01-01")      # 可用股票
industry = dc.jy.industry(date="2023-01-01")  # 行业分类
adj_factors = dc.jy.adj_factors(date="2023-01-01")  # 复权因子
```

### 2. 计算因子

使用 Polars 简洁高效地计算因子：

```python
# 计算 5 日收益率因子
factor_df = df.with_columns(
    ret_5d=pl.col("close").pct_change(5)
).filter(
    pl.col("volume") > 0  # 过滤停牌
)

# 更多因子示例
factor_df = df.with_columns(
    ret_1d=pl.col("close").pct_change(1),
    ret_5d=pl.col("close").pct_change(5),
    ret_20d=pl.col("close").pct_change(20),
    volume_ratio=pl.col("volume") / pl.col("volume").rolling_mean(20),
).filter(pl.col("volume") > 0)
```

### 3. 因子分析 (Rack + Polens)

使用 Rack 整合数据，Polens 进行专业因子分析：

```python
from alphamaster.rack import Rack
from alphamaster.polens import FactorAnalyzer

# Rack: 加载行情数据并整合因子
rack = Rack()
rack.load_prices("2023-01-01", "2023-12-31")  # 加载行情
rack.set_factor(factor_df)                      # 设置因子

# Polens: 因子分析
analyzer = FactorAnalyzer(rack.get_data(), group_col="industry")
analyzer.preprocess(periods=[1, 5, 10], quantiles=5)
analyzer.analyze()

# 获取统计指标
stats = analyzer.summary_stats()
print(stats)

# 绘制分析图表
analyzer.plot("ic_ts")           # IC 时序图
analyzer.plot("quantile_cum")    # 分层累积收益
analyzer.plot("stability")       # 因子稳定性
```

> **提示**: Rack 会自动缓存行情数据，更换因子时无需重新加载。

---

## 研究员入口

| 模块 | 说明 |
|------|------|
| `xcals` | 交易日历工具 |
| `datacenter` | 数据访问层，统一获取行情和基础信息 |
| `alphamaster` | 因子研究工具，包括数据整合器 `Rack` 和因子分析模块 `polens` |

`alpha-lab` 还包含支撑数据存储、数据库访问和并发任务的内部基础设施模块。
这些模块随发行包一起交付，用于保证研究工具开箱可用，但通常不是研究员直接调用的入口。

---

## 许可证

[MIT](LICENSE)
