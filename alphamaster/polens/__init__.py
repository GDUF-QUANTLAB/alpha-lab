"""Polens - 基于 Polars 的高性能因子分析库。

本模块提供基于 Polars DataFrame 的因子分析功能，采用 Facade 设计模式，
专注于量化金融中的核心指标计算（IC、分层收益、换手率等）。

主要组件:
    FactorAnalyzer: 因子分析主类，提供预处理-分析-汇总-可视化的一体化流程。
    FactorMetrics: 静态工具类，提供各类因子指标的计算方法。
    FactorPlotter: 可视化工具类，基于 Matplotlib 生成分析图表。

基本用法:
    >>> import polars as pl
    >>> from alphamaster.polens import FactorAnalyzer
    >>>
    >>> df = pl.DataFrame({
    ...     "date": ["2023-01-01", "2023-01-01", "2023-01-02"],
    ...     "asset": ["A", "B", "A"],
    ...     "value": [0.1, 0.2, 0.15],
    ...     "vwap": [100.0, 50.0, 101.0],
    ...     "adj_factor": [1.0, 1.0, 1.0],
    ... }).with_columns(pl.col("date").str.to_date())
    >>>
    >>> analyzer = FactorAnalyzer(df)
    >>> analyzer.preprocess(periods=[1, 5, 10], quantiles=5)
    >>> analyzer.analyze()
    >>>
    >>> # 获取分析结果
    >>> ic_df = analyzer.ic_df
    >>> summary = analyzer.summary_stats()
    >>>
    >>> # 可视化
    >>> analyzer.plot("summary")  # 汇总报告
    >>> analyzer.plot("ic")       # IC 时间序列

数据要求:
    输入 DataFrame 必须包含以下列:
    - date (Date): 交易日期
    - asset (String): 资产代码
    - value (Float64): 因子值
    - vwap (Float64): 成交量加权平均价
    - adj_factor (Float64): 复权因子

    可选列:
    - group (String): 分组标签（如行业/板块），用于分组分析
    - avail (Boolean): 是否可用（用于过滤停牌等）
"""

from __future__ import annotations

from alphamaster.polens.core import FactorAnalyzer
from alphamaster.polens.metrics import FactorMetrics
from alphamaster.polens.plotting import FactorPlotter

__all__ = ["FactorAnalyzer", "FactorMetrics", "FactorPlotter"]
