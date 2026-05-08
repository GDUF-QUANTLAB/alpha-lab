# Factor 使用文档

`factor` 是 alpha-lab 的因子定义、依赖加载、计算更新和持久化模块。当前推荐的使用主线是：

1. 用 `Factor` 定义基础因子。
2. 用 `Cubase` 批量加载一组因子，并声明每个依赖的查询配置。
3. 用 `factor.ops` 直接作为复合因子的 `fn`，或在自定义函数里调用 `cb.load()` / `cb.load_window()`。

## 核心对象

### Factor

`Factor` 是用户定义因子的入口。基础因子的 `fn` 接收 `date`，返回包含 `asset` 和一个或多个数值列的 DataFrame。

```python
import polars as pl

from factor import Factor


def close_price(date: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "asset": ["000001.SZ", "000002.SZ"],
            "value": [10.2, 18.5],
        }
    )


close = Factor(fn=close_price, name="close", insert_time="15:00:00")
```

返回结果至少需要包含 `asset`。如果没有 `datetime`，计算引擎会根据 `date` 和 `insert_time` 补齐；如果返回多个数值列，引擎会将它们转成长表并写入存储。

### Cubase

`Cubase` 是因子批量加载器。它在初始化时绑定一组因子，并保存每个因子的查询配置。

```python
from factor import Cubase

cubase = Cubase(
    [
        {"factor": close, "lag": 1},
        {"factor": volume, "lag": 0},
    ]
)

day_data = cubase.load(date="2023-01-03", loader_time="15:00:00")
window_data = cubase.load_window("2023-01-03", window=5, loader_time="15:00:00")
```

返回数据是宽表：

```text
asset | datetime | close | volume
```

`lag` 只改变实际取数日期。返回结果里的 `datetime` 始终对齐查询目标日期，便于横截面 join、窗口聚合和下游算子使用。

### FactorContext

`FactorContext` 是计算期兼容代理。因子函数里拿到的 `cb` 目前仍是 `FactorContext`，但真实加载能力来自内部的 `Cubase`。

```python
def custom_factor(date: str, cb) -> pl.DataFrame:
    data = cb.load(date)
    return data.select("asset", value=pl.col("close") / pl.col("volume"))
```

用户代码应使用 `cb.load(...)` 和 `cb.load_window(...)`，不要依赖 `_depends` 这类内部属性。

## 直接使用 ops 作为 fn

`fn` 不一定要自己写函数。对于常见运算，可以直接使用 `factor.ops` 中的函数。

### 单因子运算

```python
from factor import Factor
from factor.ops import LOG, ZFOLD

log_close = Factor(close, fn=LOG, name="log_close", insert_time="15:00:00")
zfold_close = Factor(close, fn=ZFOLD, name="zfold_close", insert_time="15:00:00")
```

这些函数会在计算时通过 `cb.load(date)` 读取依赖因子。

### 多因子运算

```python
from factor import Factor
from factor.ops import ADD, DIV, PCT

amount = Factor(close, volume, fn=ADD, name="amount_proxy", insert_time="15:00:00")
turnover_rate = Factor(amount, shares, fn=DIV, name="turnover_rate", insert_time="15:00:00")
close_pct = Factor(close, prev_close, fn=PCT, name="close_pct", insert_time="15:00:00")
```

多因子 ops 按依赖顺序读取 `cb.dep_names`。例如 `DIV` 使用第一个依赖作为分子，第二个依赖作为分母。

### 时序运算

时序 ops 使用 `cb.load_window(date, window)` 查询窗口数据。

```python
from factor import Factor
from factor.ops import TS_MEAN, TS_STD, TS_ZSCORE

ma20 = Factor(close, fn=TS_MEAN, name="ma20", insert_time="15:00:00")(window=20)
std20 = Factor(close, fn=TS_STD, name="std20", insert_time="15:00:00")(window=20)
zscore20 = Factor(close, fn=TS_ZSCORE, name="zscore20", insert_time="15:00:00")(
    window=20
)
```

如果需要显式控制依赖配置，先构造 `Cubase`：

```python
from factor import Cubase, Factor
from factor.ops import TS_CORR

cubase = Cubase(
    [
        {"factor": close, "lag": 0},
        {"factor": volume, "lag": 1},
    ]
)

price_volume_corr = Factor(
    cubase,
    fn=TS_CORR,
    name="price_volume_corr",
    insert_time="15:00:00",
)(window=20)
```

## 自定义复合因子

当内置 ops 不够用时，再写自定义函数。

```python
import polars as pl

from factor import Cubase, Factor

cubase = Cubase(
    [
        {"factor": close, "lag": 0},
        {"factor": volume, "lag": 0},
    ]
)


def price_volume_score(date: str, cb) -> pl.DataFrame:
    data = cb.load(date)
    return data.select(
        "asset",
        value=pl.col("close").rank() + pl.col("volume").rank(),
    )


score = Factor(
    cubase,
    fn=price_volume_score,
    name="price_volume_score",
    insert_time="15:00:00",
)
```

自定义函数返回的列同样需要包含 `asset`，并输出一个或多个数值列。

## 更新与读取

用 `update_factors()` 按依赖图分层更新因子。系统会先更新无依赖因子，再更新依赖它们的复合因子。

```python
from factor import get_history, get_value, update_factors

update_factors([close, ma20, price_volume_corr], "2023-01-01", "2023-01-31")

today = get_value(ma20, date="2023-01-31", time="15:00:00", rt=False)
history = get_history(ma20, "2023-01-01", "2023-01-31", lazy=False)
```

`get_value()` 返回单日宽表，`get_history()` 返回历史数据。因子数据按 `name/version/date` 写入本地存储。

## 当前 API 边界

- `Factor` 是用户定义因子的入口。
- `Cubase` 是依赖因子的批量加载器和查询中间层。
- `FactorContext` 是兼容代理，暂时保留给现有 ops 和用户函数使用。
- `BasicFactor` 是内部基类，不建议用户直接实例化。
- `_depends` 是内部兼容视图，不作为用户 API 使用。

## 目录结构

```text
factor/
├── __init__.py          # 公共 API 导出
├── api.py               # Factor 用户入口
├── context.py           # FactorContext 兼容代理
├── core.py              # Cubase, BasicFactor, DelayedFunction
├── engine.py            # get_value, get_history, get_update_tasks
├── exceptions.py        # 异常类
├── graph.py             # topological_sort, get_execution_plan
├── ops/
│   ├── __init__.py
│   ├── basic.py         # LOG, ADD, DIV, PCT 等横截面运算
│   └── time_series.py   # TS_MEAN, TS_STD, TS_CORR 等窗口运算
└── store.py             # blazestore 持久化
```
