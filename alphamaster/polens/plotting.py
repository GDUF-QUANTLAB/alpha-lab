"""因子分析可视化模块。

提供基于 Matplotlib 的静态图表生成功能，接口对齐 tearsheet 设计。

主要图表:
    - IC 时间序列图 (含移动平均)
    - IC 月度热力图
    - 分组 IC 柱状图
    - 分层累积收益图
    - 多空累积收益图
    - 分层平均收益柱状图
    - 因子稳定性分析图

Example:
    >>> from alphamaster.polens.plotting import FactorPlotter
    >>> plotter = FactorPlotter(analyzer)
    >>> plotter.plot_ic_ts(periods=[1, 5, 10])
    >>> plotter.plot_ic_heatmap(period=5)
    >>> plotter.plot_quantile_cumulative_returns(period=5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.gridspec import GridSpec

if TYPE_CHECKING:
    from alphamaster.polens.core import FactorAnalyzer


class FactorPlotter:
    """因子分析可视化工具类。

    基于 Matplotlib 生成静态图表，接口对齐 tearsheet 设计。

    Attributes:
        analyzer: FactorAnalyzer 实例
        figsize: 默认图表尺寸

    Example:
        >>> plotter = FactorPlotter(analyzer, figsize=(12, 6))
        >>> plotter.plot_ic_ts(periods=[1, 5, 10])
        >>> plotter.plot_ic_heatmap(period=5)
    """

    MA_WINDOW = 20
    IC_HEATMAP_VMIN = -0.1
    IC_HEATMAP_VMAX = 0.1
    IC_BAR_ALPHA = 0.5
    LINE_WIDTH_THIN = 0.5
    LINE_WIDTH_NORMAL = 1.5
    LINE_WIDTH_BOLD = 2.0

    def __init__(
        self,
        analyzer: FactorAnalyzer,
        figsize: tuple[int, int] = (12, 6),
    ) -> None:
        """初始化绘图器。

        Args:
            analyzer: FactorAnalyzer 实例（需先调用 analyze()）
            figsize: 默认图表尺寸
        """
        self.analyzer = analyzer
        self.figsize = figsize

    def plot_ic_ts(
        self,
        periods: list[int] | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制 IC 时间序列图 (含20日移动平均)。

        对齐 tearsheet: plot_ic_ts

        Args:
            periods: 要绘制的周期列表，None 表示所有周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.ic_df is None:
            raise RuntimeError("请先调用 analyze() 方法")

        periods = periods or self.analyzer.periods
        figsize = figsize or self.figsize

        n_plots = len(periods)
        fig, axes = plt.subplots(
            n_plots, 1, figsize=(figsize[0], figsize[1] * n_plots), sharex=True
        )
        if n_plots == 1:
            axes = [axes]

        for ax, n in zip(axes, periods, strict=True):
            self._plot_ic_ts_single(ax, n)

        axes[-1].set_xlabel("Date")
        fig.suptitle("Information Coefficient (IC) Time Series", y=1.02)
        plt.tight_layout()
        return fig

    def plot_ic_heatmap(
        self,
        period: int | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制月度 IC 热力图。

        对齐 tearsheet: plot_ic_heatmap

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.ic_df is None:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]
        ic_col = f"ic_{period}d"

        if ic_col not in self.analyzer.ic_df.columns:
            raise ValueError(f"周期 {period} 的 IC 数据不存在")

        # 计算月度平均 IC
        monthly_ic = (
            self.analyzer.ic_df.with_columns(
                [
                    pl.col("date").dt.year().alias("year"),
                    pl.col("date").dt.month().alias("month"),
                ]
            )
            .group_by(["year", "month"])
            .agg(pl.col(ic_col).mean())
            .sort("year", "month")
        )

        # 透视表
        pivot_df = monthly_ic.to_pandas().pivot(
            index="year", columns="month", values=ic_col
        )

        figsize = figsize or (12, 8)
        fig, ax = plt.subplots(figsize=figsize)

        im = ax.imshow(
            pivot_df.values,
            cmap="RdBu_r",
            aspect="auto",
            vmin=self.IC_HEATMAP_VMIN,
            vmax=self.IC_HEATMAP_VMAX,
        )
        ax.set_xticks(range(len(pivot_df.columns)))
        ax.set_xticklabels(pivot_df.columns)
        ax.set_yticks(range(len(pivot_df.index)))
        ax.set_yticklabels(pivot_df.index)
        ax.set_xlabel("Month")
        ax.set_ylabel("Year")
        ax.set_title(f"Monthly Mean IC Heatmap ({period} days)")

        # 添加数值标注
        for i in range(len(pivot_df.index)):
            for j in range(len(pivot_df.columns)):
                value = pivot_df.iloc[i, j]
                if not np.isnan(value):
                    ax.text(j, i, f"{value:.3f}", ha="center", va="center", fontsize=8)

        plt.colorbar(im, ax=ax)
        plt.tight_layout()
        return fig

    def plot_group_ic(
        self,
        group_col: str | None = None,
        periods: list[int] | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制分组 IC 柱状图。

        对齐 tearsheet: plot_group_mean_ic

        Args:
            group_col: 分组列名，None 使用 analyzer 的 group_col
            periods: 周期列表，None 表示所有周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.ic_by_group_df is None:
            raise RuntimeError("请先调用 analyze() 方法或设置 group_col")

        group_col = group_col or self.analyzer.group_col
        if group_col is None:
            raise ValueError("未设置分组列")

        periods = periods or self.analyzer.periods
        figsize = figsize or self.figsize

        df = self.analyzer.ic_by_group_df.to_pandas()
        groups = df[group_col].tolist()

        fig, ax = plt.subplots(figsize=figsize)

        x = np.arange(len(groups))
        width = 0.8 / len(periods)

        for i, n in enumerate(periods):
            ic_col = f"rank_ic_{n}d"
            if ic_col not in df.columns:
                continue
            values = df[ic_col].tolist()
            offset = width * (i - len(periods) / 2 + 0.5)
            ax.bar(x + offset, values, width, label=f"RankIC {n}d")

        ax.set_xlabel(group_col)
        ax.set_ylabel("Mean Rank IC")
        ax.set_title(f"Mean Rank IC by {group_col}")
        ax.set_xticks(x)
        ax.set_xticklabels(groups, rotation=45, ha="right")
        ax.legend()
        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        return fig

    def plot_quantile_cumulative_returns(
        self,
        period: int | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制各分层的累积收益曲线。

        对齐 tearsheet: plot_quantile_cumulative_returns

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if not self.analyzer.quantile_ret_df:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]
        if period not in self.analyzer.quantile_ret_df:
            raise ValueError(f"周期 {period} 不存在")

        figsize = figsize or self.figsize
        fig, ax = plt.subplots(figsize=figsize)

        self._plot_quantile_cum_single(ax, period)

        plt.tight_layout()
        return fig

    def plot_combined_quantile_returns(
        self,
        periods: list[int] | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制多周期分层累积收益对比图。

        对齐 tearsheet: plot_combined_quantile_returns

        Args:
            periods: 周期列表，None 表示所有周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if not self.analyzer.quantile_ret_df:
            raise RuntimeError("请先调用 analyze() 方法")

        periods = periods or self.analyzer.periods
        figsize = figsize or self.figsize

        n_plots = len(periods)
        fig, axes = plt.subplots(
            n_plots, 1, figsize=(figsize[0], figsize[1] * n_plots), sharex=True
        )
        if n_plots == 1:
            axes = [axes]

        for i, (ax, n) in enumerate(zip(axes, periods, strict=True)):
            if n not in self.analyzer.quantile_ret_df:
                continue
            is_last = i == len(periods) - 1
            self._plot_quantile_cum_single(
                ax,
                n,
                title_suffix=f"Cumulative Returns ({n} days)",
                show_xlabel=is_last,
            )
            if i == 0:
                ax.legend(title="Quantile", loc="upper left")

        fig.suptitle("Quantile Cumulative Returns Summary", y=1.02)
        plt.tight_layout()
        return fig

    def plot_quantile_returns_bar(
        self,
        period: int | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制分层平均收益柱状图。

        对齐 tearsheet: plot_quantile_returns_bar

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if not self.analyzer.quantile_ret_df:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]
        if period not in self.analyzer.quantile_ret_df:
            raise ValueError(f"周期 {period} 不存在")

        df = self.analyzer.quantile_ret_df[period].to_pandas()
        figsize = figsize or self.figsize

        # 计算各层平均收益和标准误
        mean_ret = df.groupby("quantile")["ret_1d"].agg(["mean", "std", "count"])
        mean_ret["std_error"] = mean_ret["std"] / np.sqrt(mean_ret["count"])
        mean_ret["mean_bps"] = mean_ret["mean"] * 10000  # 转换为基点
        mean_ret["std_error_bps"] = mean_ret["std_error"] * 10000

        fig, ax = plt.subplots(figsize=figsize)

        quantiles = mean_ret.index.tolist()
        means = mean_ret["mean_bps"].tolist()
        errors = mean_ret["std_error_bps"].tolist()

        colors = ["red" if v > 0 else "green" for v in means]

        bars = ax.bar(
            quantiles,
            means,
            yerr=errors,
            capsize=5,
            color=colors,
            edgecolor="black",
            alpha=0.7,
        )

        # 添加数值标签
        for bar, mean in zip(bars, means, strict=True):
            height = bar.get_height()
            ax.annotate(
                f"{mean:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3 if height > 0 else -15),
                textcoords="offset points",
                ha="center",
                va="bottom" if height > 0 else "top",
                fontsize=9,
            )

        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax.set_title(f"Mean Daily Return by Quantile ({period} days lag)")
        ax.set_xlabel("Quantile")
        ax.set_ylabel("Mean Return (bps)")
        ax.set_xticks(quantiles)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        return fig

    def plot_long_short_cumulative_returns(
        self,
        periods: list[int] | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制多空累积收益图。

        对齐 tearsheet: plot_long_short_cumulative_returns

        Args:
            periods: 周期列表，None 表示所有周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if not self.analyzer.quantile_ret_df:
            raise RuntimeError("请先调用 analyze() 方法")

        periods = periods or self.analyzer.periods
        figsize = figsize or self.figsize

        fig, ax = plt.subplots(figsize=figsize)

        self._plot_ls_cum_single(ax, periods)

        plt.tight_layout()
        return fig

    def plot_factor_stability(
        self,
        quantile: int | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制因子稳定性分析图。

        对齐 tearsheet: plot_factor_stability
        包含：自相关时序、换手率时序

        Args:
            quantile: 要分析的层，None 表示最高层
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.autocorr_df is None:
            raise RuntimeError("请先调用 analyze() 方法")

        quantile = quantile or self.analyzer.quantiles

        if not self.analyzer.turnover_df or 1 not in self.analyzer.turnover_df:
            raise RuntimeError("换手率数据不存在")

        autocorr_df = self.analyzer.autocorr_df.to_pandas()
        turnover_df = self.analyzer.turnover_df[1].to_pandas()

        figsize = figsize or (12, 10)
        fig, axes = plt.subplots(2, 1, figsize=figsize)

        # 1. 自相关时序
        ax1 = axes[0]
        dates = autocorr_df["date"]
        ac_values = autocorr_df["autocorr"]
        ma_ac = ac_values.rolling(window=self.MA_WINDOW, min_periods=1).mean()

        ax1.plot(dates, ac_values, color="lightgray", alpha=0.7, label="Autocorr")
        ax1.plot(
            dates,
            ma_ac,
            color="blue",
            linewidth=self.LINE_WIDTH_BOLD,
            label="MA20 Autocorr",
        )
        ax1.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax1.set_title("Rank Autocorrelation (1 day lag)")
        ax1.set_ylabel("Autocorrelation")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 换手率时序
        ax2 = axes[1]
        q_data = turnover_df[turnover_df["quantile"] == quantile].sort_values("date")
        dates_to = q_data["date"]
        to_values = q_data["turnover"]
        ma_to = to_values.rolling(window=self.MA_WINDOW, min_periods=1).mean()

        ax2.plot(dates_to, to_values, color="lightgray", alpha=0.7, label="Turnover")
        ax2.plot(
            dates_to,
            ma_to,
            color="green",
            linewidth=self.LINE_WIDTH_BOLD,
            label="MA20 Turnover",
        )
        ax2.set_title(f"Quantile {quantile} Turnover")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Turnover")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        fig.suptitle("Factor Stability Analysis", y=1.02)
        plt.tight_layout()
        return fig

    def plot_ic_summary(
        self,
        period: int | None = None,
        figsize: tuple[int, int] = (16, 10),
    ) -> plt.Figure:
        """绘制 IC 综合分析图。

        对齐 tearsheet: plot_ic_summary
        包含：IC 时序 + 月度热力图

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.ic_df is None:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]
        ic_col = f"ic_{period}d"

        if ic_col not in self.analyzer.ic_df.columns:
            raise ValueError(f"周期 {period} 的 IC 数据不存在")

        fig = plt.figure(figsize=figsize)
        gs = GridSpec(2, 1, height_ratios=[1, 1], hspace=0.3)

        # 1. IC 时序
        ax1 = fig.add_subplot(gs[0])
        ic_df = self.analyzer.ic_df.to_pandas()
        dates = ic_df["date"]
        ic_values = ic_df[ic_col]
        ma_series = ic_values.rolling(window=self.MA_WINDOW, min_periods=1).mean()

        ax1.bar(
            dates,
            ic_values,
            alpha=self.IC_BAR_ALPHA,
            color="steelblue",
            label=f"IC {period}d",
        )
        ax1.plot(
            dates,
            ma_series,
            color="darkorange",
            linewidth=self.LINE_WIDTH_BOLD,
            label="MA20",
        )
        ax1.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax1.set_title(f"IC Time Series ({period} days)")
        ax1.set_ylabel("IC")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 月度热力图
        ax2 = fig.add_subplot(gs[1])
        monthly_ic = (
            self.analyzer.ic_df.with_columns(
                [
                    pl.col("date").dt.year().alias("year"),
                    pl.col("date").dt.month().alias("month"),
                ]
            )
            .group_by(["year", "month"])
            .agg(pl.col(ic_col).mean())
            .sort("year", "month")
        )
        pivot_df = monthly_ic.to_pandas().pivot(
            index="year", columns="month", values=ic_col
        )

        im = ax2.imshow(
            pivot_df.values,
            cmap="RdBu_r",
            aspect="auto",
            vmin=self.IC_HEATMAP_VMIN,
            vmax=self.IC_HEATMAP_VMAX,
        )
        ax2.set_xticks(range(len(pivot_df.columns)))
        ax2.set_xticklabels(pivot_df.columns)
        ax2.set_yticks(range(len(pivot_df.index)))
        ax2.set_yticklabels(pivot_df.index)
        ax2.set_xlabel("Month")
        ax2.set_ylabel("Year")
        ax2.set_title(f"Monthly IC Heatmap ({period} days)")

        for i in range(len(pivot_df.index)):
            for j in range(len(pivot_df.columns)):
                value = pivot_df.iloc[i, j]
                if not np.isnan(value):
                    ax2.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7)

        plt.colorbar(im, ax=ax2)
        fig.suptitle("IC Analysis Summary", y=0.98)
        plt.tight_layout()
        return fig

    # 保留 polens 独有的图表
    def plot_turnover(
        self,
        period: int | None = None,
        figsize: tuple[int, int] | None = None,
    ) -> plt.Figure:
        """绘制分组平均换手率柱状图 (polens 独有)。

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if not self.analyzer.turnover_df:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]
        if period not in self.analyzer.turnover_df:
            raise ValueError(f"周期 {period} 不存在")

        df = self.analyzer.turnover_df[period].to_pandas()
        figsize = figsize or self.figsize

        # 计算各层平均换手率和标准误
        turnover_stats = df.groupby("quantile")["turnover"].agg(
            ["mean", "std", "count"]
        )
        turnover_stats["std_error"] = turnover_stats["std"] / np.sqrt(
            turnover_stats["count"]
        )

        fig, ax = plt.subplots(figsize=figsize)

        quantiles = turnover_stats.index.tolist()
        means = [m * 100 for m in turnover_stats["mean"].tolist()]  # 转换为百分比
        errors = [e * 100 for e in turnover_stats["std_error"].tolist()]

        colors = plt.cm.viridis(np.linspace(0, 1, len(quantiles)))

        bars = ax.bar(
            quantiles,
            means,
            yerr=errors,
            capsize=5,
            color=colors,
            edgecolor="black",
            alpha=0.8,
        )

        # 添加数值标签
        for bar, mean in zip(bars, means, strict=True):
            height = bar.get_height()
            ax.annotate(
                f"{mean:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        ax.set_title(f"Mean Turnover by Quantile ({period}d)")
        ax.set_xlabel("Quantile")
        ax.set_ylabel("Mean Turnover (%)")
        ax.set_xticks(quantiles)
        ax.set_ylim(0, max(means) * 1.2)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        return fig

    def plot_summary(
        self,
        period: int | None = None,
        figsize: tuple[int, int] = (16, 12),
    ) -> plt.Figure:
        """绘制汇总报告图 (polens 独有)。

        复用独立接口绘制 IC 时序、IC 分布、分层收益、累积收益、多空收益。

        Args:
            period: 周期，None 表示第一个可用周期
            figsize: 图表尺寸

        Returns:
            Matplotlib Figure 对象
        """
        if self.analyzer.ic_df is None or not self.analyzer.quantile_ret_df:
            raise RuntimeError("请先调用 analyze() 方法")

        period = period or self.analyzer.periods[0]

        fig = plt.figure(figsize=figsize)
        gs = GridSpec(3, 3, hspace=0.3, wspace=0.3)

        # 1. IC 时间序列 - 复用 plot_ic_ts 逻辑
        ax1 = fig.add_subplot(gs[0, :2])
        self._plot_ic_ts_single(ax1, period)

        # 2. IC 分布 - 复用逻辑
        ax2 = fig.add_subplot(gs[0, 2])
        self._plot_ic_dist_single(ax2, period)

        # 3. 分层平均收益 (bps) - 复用 plot_quantile_returns_bar 逻辑
        ax3 = fig.add_subplot(gs[1, 0])
        self._plot_quantile_returns_bar_single(ax3, period)

        # 4. 分层累积收益 - 复用 plot_quantile_cumulative_returns 逻辑
        ax4 = fig.add_subplot(gs[1, 1:])
        self._plot_quantile_cum_single(ax4, period)

        # 5. 多空累积收益 - 复用 plot_long_short_cumulative_returns 逻辑
        ax5 = fig.add_subplot(gs[2, :])
        self._plot_ls_cum_single(ax5, [period])

        fig.suptitle(f"Factor Analysis Summary (Period: {period}d)", y=0.98)
        return fig

    def _plot_ic_ts_single(self, ax: plt.Axes, period: int) -> None:
        """在指定 Axes 上绘制单周期 IC 时间序列。"""
        ic_df = self.analyzer.ic_df.to_pandas()
        ic_col = f"ic_{period}d"

        if ic_col not in ic_df.columns:
            ax.set_title(f"IC {period}d (No Data)")
            return

        dates = ic_df["date"]
        ic_values = ic_df[ic_col]

        ax.bar(
            dates,
            ic_values,
            alpha=self.IC_BAR_ALPHA,
            color="steelblue",
            label=f"IC {period}d",
        )
        ma_series = ic_values.rolling(window=self.MA_WINDOW, min_periods=1).mean()
        ax.plot(
            dates,
            ma_series,
            color="darkorange",
            linewidth=self.LINE_WIDTH_BOLD,
            label="MA20",
        )
        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax.set_title(f"IC Time Series ({period}d)")
        ax.set_ylabel("IC")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_ic_dist_single(self, ax: plt.Axes, period: int) -> None:
        """在指定 Axes 上绘制 IC 分布。"""
        ic_df = self.analyzer.ic_df.to_pandas()
        rank_ic_col = f"rank_ic_{period}d"

        if rank_ic_col not in ic_df.columns:
            ax.set_title("IC Distribution (No Data)")
            return

        data = ic_df[rank_ic_col].dropna()
        ax.hist(data, bins=20, edgecolor="black", alpha=0.7, color="skyblue")
        ax.axvline(x=data.mean(), color="red", linestyle="--")
        ax.set_title("IC Distribution")
        ax.set_xlabel("Rank IC")

    def _plot_quantile_returns_bar_single(self, ax: plt.Axes, period: int) -> None:
        """在指定 Axes 上绘制分层平均收益柱状图。"""
        if period not in self.analyzer.quantile_ret_df:
            ax.set_title("Mean Return (No Data)")
            return

        df = self.analyzer.quantile_ret_df[period].to_pandas()
        mean_returns = df.groupby("quantile")["ret_1d"].mean() * 10000  # bps
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(mean_returns)))

        ax.bar(mean_returns.index, mean_returns.values, color=colors, edgecolor="black")
        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax.set_title("Mean Return by Quantile")
        ax.set_ylabel("Mean Return (bps)")
        ax.grid(True, alpha=0.3, axis="y")

    def _plot_quantile_cum_single(
        self,
        ax: plt.Axes,
        period: int,
        title_suffix: str | None = None,
        show_xlabel: bool = True,
    ) -> None:
        """在指定 Axes 上绘制分层累积收益。

        Args:
            ax: Matplotlib Axes 对象
            period: 周期
            title_suffix: 标题后缀，None 时使用默认格式
            show_xlabel: 是否显示 x 轴标签
        """
        if period not in self.analyzer.quantile_ret_df:
            ax.set_title("Cumulative Return (No Data)")
            return

        df = self.analyzer.quantile_ret_df[period].to_pandas()
        quantiles = sorted(df["quantile"].dropna().unique())
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(quantiles)))

        for q, color in zip(quantiles, colors, strict=True):
            q_data = df[df["quantile"] == q].sort_values("date")
            cum_returns = (1 + q_data["ret_1d"].fillna(0)).cumprod() - 1
            ax.plot(
                q_data["date"],
                cum_returns,
                label=f"Q{int(q)}",
                color=color,
                linewidth=self.LINE_WIDTH_NORMAL,
            )

        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        title = title_suffix or f"Cumulative Returns by Quantile ({period} days lag)"
        ax.set_title(title)
        if show_xlabel:
            ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Return")
        ax.legend(title="Quantile", loc="upper left")
        ax.grid(True, alpha=0.3)

    def _plot_ls_cum_single(self, ax: plt.Axes, periods: list[int]) -> None:
        """在指定 Axes 上绘制多空累积收益。"""
        colors = plt.cm.tab10(np.linspace(0, 1, len(periods)))

        for n, color in zip(periods, colors, strict=True):
            if n not in self.analyzer.quantile_ret_df:
                continue

            df = self.analyzer.quantile_ret_df[n].to_pandas()
            quantiles = sorted(df["quantile"].dropna().unique())

            if len(quantiles) < 2:
                continue

            top_q = (
                df[df["quantile"] == quantiles[-1]]
                .sort_values("date")
                .set_index("date")["ret_1d"]
            )
            bottom_q = (
                df[df["quantile"] == quantiles[0]]
                .sort_values("date")
                .set_index("date")["ret_1d"]
            )
            common_dates = top_q.index.intersection(bottom_q.index)
            ls_returns = top_q.loc[common_dates] - bottom_q.loc[common_dates]
            cum_ls_returns = (1 + ls_returns.fillna(0)).cumprod() - 1

            ax.plot(
                cum_ls_returns.index,
                cum_ls_returns.values,
                label=f"L/S {n}d",
                color=color,
                linewidth=self.LINE_WIDTH_BOLD,
            )

        ax.axhline(y=0, color="black", linestyle="--", linewidth=self.LINE_WIDTH_THIN)
        ax.set_title("Long-Short Cumulative Return")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Return")
        ax.legend()
        ax.grid(True, alpha=0.3)
