"""因子分析核心模块。

本模块提供 FactorAnalyzer 类，采用 Facade 设计模式整合数据预处理、
指标计算和结果汇总功能。

数据接口协议:
    输入 DataFrame 必须包含以下列:
    - date (Date): 交易日期
    - asset (String): 资产代码
    - value (Float64): 因子值
    - vwap (Float64): 成交量加权平均价
    - adj_factor (Float64): 复权因子

    可选列:
    - group (String): 分组标签（如行业/板块）
    - avail (Boolean): 是否可用（用于过滤停牌等）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import polars as pl

from alphamaster.polens.metrics import FactorMetrics
from alphamaster.polens.utils import (
    align_with_calendar,
    compute_forward_returns,
    quantile_binning,
)


class FactorAnalyzer:
    """因子分析 Facade 类。

    串联数据预处理、指标计算流程。所有状态集中管理，支持链式调用。

    Attributes:
        raw_df: 原始输入数据
        processed_df: 预处理后的数据
        ic_df: 每日 IC 数据
        ic_by_group_df: 分组 IC 数据
        quantile_ret_df: 分层收益数据，按周期存储
        turnover_df: 换手率数据，按周期存储
        autocorr_df: 自相关性数据
        periods: 分析周期列表
        quantiles: 分位数数量
        group_col: 分组列名

    Example:
        >>> analyzer = FactorAnalyzer(df, group_col="industry")
        >>> analyzer.preprocess(periods=[1, 5, 10], quantiles=5)
        >>> analyzer.analyze()
        >>> stats = analyzer.summary_stats()
    """

    def __init__(self, df: pl.DataFrame, group_col: str | None = None) -> None:
        """初始化分析器。

        Args:
            df: 包含必需列的 DataFrame
            group_col: 分组列名（如 "industry"），用于分组分析

        Raises:
            ValueError: 输入数据缺少必需列
        """
        required_cols = {"date", "asset", "value", "vwap", "adj_factor"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"输入数据缺少必需列: {missing_cols}")

        self.raw_df = df
        self.group_col = group_col

        # 处理后的数据
        self.processed_df: pl.DataFrame | None = None

        # 分析结果
        self.ic_df: pl.DataFrame | None = None
        self.ic_by_group_df: pl.DataFrame | None = None
        self.quantile_ret_df: dict[int, pl.DataFrame] = {}
        self.turnover_df: dict[int, pl.DataFrame] = {}
        self.autocorr_df: pl.DataFrame | None = None

        # 配置
        self.periods: list[int] = [1, 5, 10]
        self.quantiles: int = 5

    def preprocess(
        self,
        periods: list[int] | None = None,
        quantiles: int = 5,
        *,
        demean: bool = False,
        align_calendar: bool = True,
    ) -> FactorAnalyzer:
        """数据预处理：计算收益率、分箱。

        处理流程:
        1. 与交易日历对齐（防止 shift 跳过非交易日）
        2. 计算远期收益率（强制包含 1d）
        3. 过滤可用性（如果存在 avail 列）
        4. 分位数分箱

        Args:
            periods: 远期收益周期列表，默认 [1, 5, 10]
            quantiles: 分位数数量，默认 5
            demean: 是否计算超额收益（减去当日均值）
            align_calendar: 是否与交易日历对齐

        Returns:
            self，支持链式调用
        """
        if periods is None:
            periods = [1, 5, 10]
        self.periods = periods
        self.quantiles = quantiles

        df = self.raw_df

        # 1. 与交易日历对齐
        if align_calendar:
            df = align_with_calendar(df)

        # 2. 计算远期收益率
        df = compute_forward_returns(df, periods=periods, demean=demean)

        # 3. 过滤可用性
        if "avail" in df.columns:
            df = df.filter(df["avail"])

        # 4. 分位数分箱
        df = quantile_binning(df, quantiles=quantiles, group_col=self.group_col)

        self.processed_df = df
        return self

    def analyze(self) -> FactorAnalyzer:
        """执行完整分析。

        分析流程:
        1. 计算 IC（Pearson 和 Spearman）
        2. 计算分组 IC（如果指定了分组列）
        3. 计算分层收益和换手率（按周期）
        4. 计算自相关性

        Returns:
            self，支持链式调用

        Raises:
            RuntimeError: 未调用 preprocess() 方法
        """
        if self.processed_df is None:
            raise RuntimeError("请先调用 preprocess() 方法")

        # 1. 计算 IC
        self.ic_df = FactorMetrics.calc_ic(self.processed_df, self.periods)

        # 2. 计算分组 IC
        if self.group_col and self.group_col in self.processed_df.columns:
            self.ic_by_group_df = FactorMetrics.calc_ic_by_group(
                self.processed_df, self.periods, self.group_col
            )

        # 3. 计算分层收益和换手率
        for n in self.periods:
            quantile_col = f"quantile_{n}d" if n > 1 else "quantile"

            # 分层收益
            self.quantile_ret_df[n] = FactorMetrics.calc_quantile_returns(
                self.processed_df,
                periods=[n],
                quantile_col=quantile_col,
                quantiles=self.quantiles,
            )

            # 换手率
            turnover_input = self.processed_df.select(
                ["date", "asset", self.processed_df[quantile_col].alias("quantile")]
            )
            self.turnover_df[n] = FactorMetrics.calc_turnover(
                turnover_input, quantiles=self.quantiles
            )

        # 4. 计算自相关性
        self.autocorr_df = FactorMetrics.calc_autocorrelation(self.processed_df)

        return self

    def summary_stats(self) -> dict[str, dict[str, float]]:
        """获取汇总统计指标。

        Returns:
            包含 RankIC, ICIR, t-stat, p-value, Turnover 的字典
            格式: {period: {metric: value, ...}, ...}

        Raises:
            RuntimeError: 未调用 analyze() 方法
        """
        if self.ic_df is None:
            raise RuntimeError("请先调用 analyze() 方法")

        stats = FactorMetrics.calc_ic_summary(self.ic_df, self.periods)

        # 添加换手率指标
        for n in self.periods:
            if n in self.turnover_df:
                to_df = self.turnover_df[n]
                max_q_turnover = (
                    to_df.filter(to_df["quantile"] == self.quantiles)
                    .select(to_df["turnover"].mean())
                    .item()
                )
                stats[f"{n}d"]["Turnover_TopQ"] = max_q_turnover

        return stats

    def plot(self, plot_type: str = "ic_ts", **kwargs) -> plt.Figure:
        """绘制分析图表。

        集成可视化功能，接口对齐 tearsheet 设计。

        Args:
            plot_type: 图表类型，可选:
                - "ic_ts": IC 时间序列（含MA）
                - "ic_heatmap": IC 月度热力图
                - "ic_summary": IC 综合分析（时序+热力图）
                - "group_ic": 分组 IC 柱状图
                - "quantile_cum": 分层累积收益
                - "quantile_combined": 多周期分层收益对比
                - "quantile_bar": 分层平均收益柱状图
                - "ls_cum": 多空累积收益
                - "stability": 因子稳定性分析
                - "turnover": 换手率（polens 独有）
                - "summary": 汇总报告（polens 独有）
            **kwargs: 传递给具体绘图方法的参数

        Returns:
            Matplotlib Figure 对象

        Raises:
            RuntimeError: 未调用 analyze() 方法
            ValueError: 不支持的图表类型

        Example:
            >>> analyzer.plot("ic_ts", periods=[1, 5, 10])
            >>> analyzer.plot("ic_heatmap", period=5)
            >>> analyzer.plot("quantile_cum", period=5)
            >>> analyzer.plot("summary")
        """
        from alphamaster.polens.plotting import FactorPlotter

        plotter = FactorPlotter(self, figsize=kwargs.pop("figsize", (12, 6)))

        # 对齐 tearsheet 的接口命名
        plot_methods = {
            # tearsheet 对齐接口
            "ic_ts": plotter.plot_ic_ts,
            "ic_heatmap": plotter.plot_ic_heatmap,
            "ic_summary": plotter.plot_ic_summary,
            "group_ic": plotter.plot_group_ic,
            "quantile_cum": plotter.plot_quantile_cumulative_returns,
            "quantile_combined": plotter.plot_combined_quantile_returns,
            "quantile_bar": plotter.plot_quantile_returns_bar,
            "ls_cum": plotter.plot_long_short_cumulative_returns,
            "stability": plotter.plot_factor_stability,
            # polens 独有接口
            "turnover": plotter.plot_turnover,
            "summary": plotter.plot_summary,
            # 向后兼容
            "ic": plotter.plot_ic_ts,
            "cum_return": plotter.plot_quantile_cumulative_returns,
            "ls": plotter.plot_long_short_cumulative_returns,
        }

        if plot_type not in plot_methods:
            raise ValueError(
                f"不支持的图表类型: {plot_type}。可选: {list(plot_methods.keys())}"
            )

        return plot_methods[plot_type](**kwargs)
