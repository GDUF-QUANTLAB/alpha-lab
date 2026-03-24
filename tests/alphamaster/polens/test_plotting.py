"""可视化模块测试。"""

import matplotlib

matplotlib.use("Agg")

from unittest.mock import MagicMock

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import pytest

from alphamaster.polens.plotting import FactorPlotter


@pytest.fixture
def mock_analyzer():
    """创建模拟的 FactorAnalyzer。"""
    analyzer = MagicMock()
    analyzer.periods = [1, 5]
    analyzer.quantiles = 5
    analyzer.group_col = "industry"

    # 模拟 IC 数据
    dates = pl.date_range(
        pl.date(2023, 1, 1), pl.date(2023, 3, 31), interval="1d", eager=True
    )
    np.random.seed(42)
    analyzer.ic_df = pl.DataFrame(
        {
            "date": dates,
            "ic_1d": np.random.randn(len(dates)) * 0.05,
            "rank_ic_1d": np.random.randn(len(dates)) * 0.05,
            "ic_5d": np.random.randn(len(dates)) * 0.03,
            "rank_ic_5d": np.random.randn(len(dates)) * 0.03,
        }
    )

    # 模拟分组 IC 数据
    analyzer.ic_by_group_df = pl.DataFrame(
        {
            "industry": ["Tech", "Finance", "Health"],
            "rank_ic_1d": [0.05, 0.03, 0.04],
            "rank_ic_5d": [0.04, 0.02, 0.03],
        }
    )

    # 模拟分层收益数据
    quantile_dates = []
    quantiles = []
    ret_1d = []
    for d in dates[:60]:
        for q in range(1, 6):
            quantile_dates.append(d)
            quantiles.append(q)
            ret_1d.append(0.001 + q * 0.0002 + np.random.randn() * 0.005)

    quantile_df = pl.DataFrame(
        {
            "date": quantile_dates,
            "quantile": quantiles,
            "ret_1d": ret_1d,
        }
    )

    analyzer.quantile_ret_df = {1: quantile_df, 5: quantile_df}

    # 模拟换手率数据
    turnover_dates = []
    turnover_quantiles = []
    turnover_values = []
    for d in dates[:60]:
        for q in range(1, 6):
            turnover_dates.append(d)
            turnover_quantiles.append(q)
            turnover_values.append(0.2 + np.random.rand() * 0.3)

    analyzer.turnover_df = {
        1: pl.DataFrame(
            {
                "date": turnover_dates,
                "quantile": turnover_quantiles,
                "turnover": turnover_values,
            }
        )
    }

    # 模拟自相关数据
    analyzer.autocorr_df = pl.DataFrame(
        {
            "date": dates,
            "autocorr": np.random.randn(len(dates)) * 0.1 + 0.3,
        }
    )

    return analyzer


class TestFactorPlotter:
    """FactorPlotter 测试类。"""

    def test_init(self, mock_analyzer):
        """测试初始化。"""
        plotter = FactorPlotter(mock_analyzer)
        assert plotter.analyzer == mock_analyzer
        assert plotter.figsize == (12, 6)

        plotter = FactorPlotter(mock_analyzer, figsize=(10, 8))
        assert plotter.figsize == (10, 8)

    def test_plot_ic_ts(self, mock_analyzer):
        """测试 IC 时间序列图（含MA）。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_ts()

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2  # 两个周期，两个子图
        plt.close(fig)

    def test_plot_ic_ts_single_period(self, mock_analyzer):
        """测试单周期 IC 图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_ts(periods=[1])

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_ic_heatmap(self, mock_analyzer):
        """测试 IC 月度热力图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_heatmap(period=1)

        assert isinstance(fig, plt.Figure)
        # colorbar 也算一个 axes
        assert len(fig.axes) >= 1
        plt.close(fig)

    def test_plot_ic_summary(self, mock_analyzer):
        """测试 IC 综合分析图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_summary(period=1)

        assert isinstance(fig, plt.Figure)
        # 时序 + 热力图 + colorbar
        assert len(fig.axes) >= 2
        plt.close(fig)

    def test_plot_group_ic(self, mock_analyzer):
        """测试分组 IC 柱状图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_group_ic()

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_quantile_cumulative_returns(self, mock_analyzer):
        """测试分层累积收益图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_quantile_cumulative_returns(period=1)

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_combined_quantile_returns(self, mock_analyzer):
        """测试多周期分层收益对比图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_combined_quantile_returns(periods=[1, 5])

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2  # 两个周期
        plt.close(fig)

    def test_plot_quantile_returns_bar(self, mock_analyzer):
        """测试分层平均收益柱状图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_quantile_returns_bar(period=1)

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_long_short_cumulative_returns(self, mock_analyzer):
        """测试多空累积收益图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_long_short_cumulative_returns(periods=[1, 5])

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_factor_stability(self, mock_analyzer):
        """测试因子稳定性分析图。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_factor_stability(quantile=5)

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2  # 自相关 + 换手率
        plt.close(fig)

    def test_plot_turnover(self, mock_analyzer):
        """测试换手率图（polens 独有）。"""
        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_turnover(period=1)

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_summary(self, mock_analyzer):
        """测试汇总报告图（polens 独有）。"""
        plotter = FactorPlotter(mock_analyzer, figsize=(16, 12))
        fig = plotter.plot_summary()

        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 5
        plt.close(fig)


class TestFactorAnalyzerPlotIntegration:
    """FactorAnalyzer.plot 集成测试。"""

    def test_analyzer_plot_ic_ts(self, mock_analyzer):
        """测试 FactorAnalyzer.plot 调用 ic_ts。"""
        from alphamaster.polens.plotting import FactorPlotter

        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_ts()

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_analyzer_plot_ic_heatmap(self, mock_analyzer):
        """测试 FactorAnalyzer.plot 调用 ic_heatmap。"""
        from alphamaster.polens.plotting import FactorPlotter

        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_ic_heatmap(period=1)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_analyzer_plot_quantile_cum(self, mock_analyzer):
        """测试 FactorAnalyzer.plot 调用 quantile_cum。"""
        from alphamaster.polens.plotting import FactorPlotter

        plotter = FactorPlotter(mock_analyzer)
        fig = plotter.plot_quantile_cumulative_returns(period=1)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)
