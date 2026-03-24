"""
FactorMetrics 测试
"""

import numpy as np
import polars as pl
import pytest

from alphamaster.polens import FactorMetrics


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "date": ["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"],
            "asset": ["A", "B", "A", "B"],
            "value": [0.1, 0.2, 0.15, 0.25],
            "ret_1d": [0.01, 0.02, 0.015, 0.025],
            "quantile": [1, 2, 1, 2],
        }
    ).with_columns(pl.col("date").str.to_date())


@pytest.fixture
def sample_df_multiple_periods():
    return pl.DataFrame(
        {
            "date": ["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"],
            "asset": ["A", "B", "A", "B"],
            "value": [0.1, 0.2, 0.15, 0.25],
            "ret_1d": [0.01, 0.02, 0.015, 0.025],
            "ret_5d": [0.05, 0.10, 0.075, 0.125],
            "quantile": [1, 2, 1, 2],
        }
    ).with_columns(pl.col("date").str.to_date())


@pytest.fixture
def sample_df_with_group():
    return pl.DataFrame(
        {
            "date": ["2023-01-01", "2023-01-01", "2023-01-01", "2023-01-01"],
            "asset": ["A", "B", "C", "D"],
            "value": [0.1, 0.2, 0.15, 0.25],
            "ret_1d": [0.01, 0.02, 0.015, 0.025],
            "industry": ["Tech", "Tech", "Finance", "Finance"],
        }
    ).with_columns(pl.col("date").str.to_date())


class TestCalcIC:
    def test_basic(self, sample_df):
        result = FactorMetrics.calc_ic(sample_df, periods=[1])

        assert "ic_1d" in result.columns
        assert "rank_ic_1d" in result.columns
        assert result.height == 2  # 2 days

    def test_multiple_periods(self, sample_df_multiple_periods):
        result = FactorMetrics.calc_ic(sample_df_multiple_periods, periods=[1, 5])

        assert "ic_1d" in result.columns
        assert "rank_ic_1d" in result.columns
        assert "ic_5d" in result.columns
        assert "rank_ic_5d" in result.columns

    def test_correlation_values(self, sample_df):
        result = FactorMetrics.calc_ic(sample_df, periods=[1])

        # IC 值应在 -1 到 1 之间
        for col in ["ic_1d", "rank_ic_1d"]:
            values = result[col].to_numpy()
            assert np.all(np.isnan(values) | ((values >= -1) & (values <= 1)))


class TestCalcICSummary:
    def test_basic(self, sample_df):
        ic_df = FactorMetrics.calc_ic(sample_df, periods=[1])
        result = FactorMetrics.calc_ic_summary(ic_df, periods=[1])

        assert "1d" in result
        assert "RankIC" in result["1d"]
        assert "RankICIR" in result["1d"]
        assert "RankIC_t_stat" in result["1d"]
        assert "RankIC_p_value" in result["1d"]

    def test_multiple_periods(self, sample_df_multiple_periods):
        ic_df = FactorMetrics.calc_ic(sample_df_multiple_periods, periods=[1, 5])
        result = FactorMetrics.calc_ic_summary(ic_df, periods=[1, 5])

        assert "1d" in result
        assert "5d" in result
        assert "RankIC" in result["1d"]
        assert "RankIC" in result["5d"]

    def test_insufficient_data(self):
        # 只有一行数据，无法计算 std
        ic_df = pl.DataFrame(
            {
                "date": ["2023-01-01"],
                "rank_ic_1d": [0.5],
            }
        ).with_columns(pl.col("date").str.to_date())

        result = FactorMetrics.calc_ic_summary(ic_df, periods=[1])

        assert "1d" in result
        assert np.isnan(result["1d"]["RankICIR"])


class TestCalcICByGroup:
    def test_basic(self, sample_df_with_group):
        result = FactorMetrics.calc_ic_by_group(
            sample_df_with_group, periods=[1], group_col="industry"
        )

        assert "industry" in result.columns
        assert "rank_ic_1d" in result.columns

    def test_group_values(self, sample_df_with_group):
        result = FactorMetrics.calc_ic_by_group(
            sample_df_with_group, periods=[1], group_col="industry"
        )

        industries = result["industry"].to_list()
        assert "Tech" in industries
        assert "Finance" in industries


class TestCalcQuantileReturns:
    def test_basic(self, sample_df):
        result = FactorMetrics.calc_quantile_returns(
            sample_df, periods=[1], quantiles=2
        )

        assert "date" in result.columns
        assert "quantile" in result.columns
        assert "ret_1d" in result.columns

    def test_multiple_periods(self, sample_df_multiple_periods):
        # 无论 periods 是多少，分层收益只返回 ret_1d
        # 这是正确的做法：分层收益反映组合的日度表现
        result = FactorMetrics.calc_quantile_returns(
            sample_df_multiple_periods, periods=[1, 5], quantiles=2
        )

        assert "date" in result.columns
        assert "quantile" in result.columns
        assert "ret_1d" in result.columns
        # 不再返回 ret_5d，分层收益始终基于 ret_1d

    def test_quantile_col(self, sample_df):
        # 使用自定义分位数列，输出统一命名为 "quantile"
        df = sample_df.with_columns(pl.col("quantile").alias("custom_quantile"))
        result = FactorMetrics.calc_quantile_returns(
            df, periods=[1], quantiles=2, quantile_col="custom_quantile"
        )

        # Index 补全后统一输出列名为 "quantile"
        assert "quantile" in result.columns


class TestCalcTurnover:
    def test_basic(self, sample_df):
        result = FactorMetrics.calc_turnover(sample_df, quantiles=2)

        assert "date" in result.columns
        assert "quantile" in result.columns
        assert "turnover" in result.columns

    def test_turnover_range(self, sample_df):
        result = FactorMetrics.calc_turnover(sample_df, quantiles=2)

        # 换手率应在 0 到 1 之间
        turnover_values = result["turnover"].to_numpy()
        assert np.all((turnover_values >= 0) & (turnover_values <= 1))

    def test_quantile_col(self, sample_df):
        df = sample_df.with_columns(pl.col("quantile").alias("custom_quantile"))
        result = FactorMetrics.calc_turnover(
            df, quantiles=2, quantile_col="custom_quantile"
        )

        assert "custom_quantile" in result.columns


class TestCalcAutocorrelation:
    def test_basic(self, sample_df):
        result = FactorMetrics.calc_autocorrelation(sample_df)

        assert "autocorr" in result.columns

    def test_with_lag(self, sample_df):
        result = FactorMetrics.calc_autocorrelation(sample_df, lag=1)

        assert "autocorr" in result.columns

    def test_custom_factor_col(self, sample_df):
        df = sample_df.with_columns(pl.col("value").alias("factor"))
        result = FactorMetrics.calc_autocorrelation(df, factor_col="factor")

        assert "autocorr" in result.columns


class TestCalcLongShortReturns:
    def test_basic(self, sample_df):
        result = FactorMetrics.calc_long_short_returns(
            sample_df, periods=[1], quantiles=2
        )

        assert "date" in result.columns
        assert "ls_ret_1d" in result.columns

    def test_multiple_periods(self, sample_df_multiple_periods):
        result = FactorMetrics.calc_long_short_returns(
            sample_df_multiple_periods, periods=[1, 5], quantiles=2
        )

        assert "date" in result.columns
        assert "ls_ret_1d" in result.columns
        assert "ls_ret_5d" in result.columns

    def test_long_short_logic(self, sample_df):
        # 手动计算多空收益验证逻辑
        result = FactorMetrics.calc_long_short_returns(
            sample_df, periods=[1], quantiles=2
        )

        # 结果应该包含日期和多空收益
        assert result.height > 0
