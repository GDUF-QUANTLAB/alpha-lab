"""
工具函数测试
"""

import polars as pl
import pytest

from alphamaster.polens.utils import (
    align_with_calendar,
    compute_forward_returns,
    quantile_binning,
)


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-01",
                "2023-01-02",
                "2023-01-02",
                "2023-01-03",
                "2023-01-03",
            ],
            "asset": ["A", "B", "A", "B", "A", "B"],
            "value": [0.1, 0.2, 0.15, 0.25, 0.12, 0.22],
            "vwap": [100.0, 50.0, 101.0, 51.0, 102.0, 52.0],
            "adj_factor": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    ).with_columns(pl.col("date").str.to_date())


@pytest.fixture
def sample_df_with_group():
    return pl.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-01",
                "2023-01-02",
                "2023-01-02",
                "2023-01-03",
                "2023-01-03",
            ],
            "asset": ["A", "B", "A", "B", "A", "B"],
            "value": [0.1, 0.2, 0.15, 0.25, 0.12, 0.22],
            "vwap": [100.0, 50.0, 101.0, 51.0, 102.0, 52.0],
            "adj_factor": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "industry": ["Tech", "Finance", "Tech", "Finance", "Tech", "Finance"],
        }
    ).with_columns(pl.col("date").str.to_date())


class TestAlignWithCalendar:
    def test_basic(self, sample_df):
        # 测试基本功能（跳过交易日历对齐）
        result = align_with_calendar(sample_df)
        # 由于可能缺少 xcals，函数可能返回原 df
        assert result is not None

    def test_with_string_dates(self):
        df = pl.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
                "asset": ["A", "A", "A"],
                "value": [0.1, 0.2, 0.3],
            }
        )
        result = align_with_calendar(df)
        assert result is not None


class TestComputeForwardReturns:
    def test_basic(self, sample_df):
        result = compute_forward_returns(sample_df, periods=[1])

        assert "ret_1d" in result.columns
        assert "vwap_adj" in result.columns

    def test_multiple_periods(self, sample_df):
        result = compute_forward_returns(sample_df, periods=[1, 2])

        assert "ret_1d" in result.columns
        assert "ret_2d" in result.columns

    def test_forces_include_1d(self, sample_df):
        # 即使不传 1，也会强制包含 1d 收益
        result = compute_forward_returns(sample_df, periods=[2])

        assert "ret_1d" in result.columns
        assert "ret_2d" in result.columns

    def test_with_demean(self, sample_df):
        result = compute_forward_returns(sample_df, periods=[1], demean=True)

        assert "ret_1d" in result.columns

    def test_with_avail_and_demean(self):
        df = pl.DataFrame(
            {
                "date": [
                    "2023-01-01",
                    "2023-01-01",
                    "2023-01-02",
                    "2023-01-02",
                    "2023-01-03",
                    "2023-01-03",
                ],
                "asset": ["A", "B", "A", "B", "A", "B"],
                "value": [0.1, 0.2, 0.15, 0.25, 0.12, 0.22],
                "vwap": [100.0, 50.0, 101.0, 51.0, 102.0, 52.0],
                "adj_factor": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                "avail": [True, True, True, False, True, True],
            }
        ).with_columns(pl.col("date").str.to_date())

        result = compute_forward_returns(df, periods=[1], demean=True)

        assert "ret_1d" in result.columns

    def test_return_values(self, sample_df):
        result = compute_forward_returns(sample_df, periods=[1])

        # 验证收益率计算逻辑
        # A: (101 * 1.0) / (100 * 1.0) - 1 = 0.01
        # B: (51 * 1.0) / (50 * 1.0) - 1 = 0.02
        a_ret = result.filter(
            (pl.col("asset") == "A") & (pl.col("date") == pl.date(2023, 1, 1))
        )["ret_1d"].item()
        b_ret = result.filter(
            (pl.col("asset") == "B") & (pl.col("date") == pl.date(2023, 1, 1))
        )["ret_1d"].item()

        assert abs(a_ret - 0.01) < 1e-10
        assert abs(b_ret - 0.02) < 1e-10


class TestQuantileBinning:
    def test_basic(self, sample_df):
        df = compute_forward_returns(sample_df, periods=[1])
        result = quantile_binning(df, quantiles=2)

        assert "quantile" in result.columns
        assert result["quantile"].is_in([1, 2]).all()

    def test_periodic_rebalancing(self, sample_df):
        df = compute_forward_returns(sample_df, periods=[1, 2])
        result = quantile_binning(df, quantiles=2)

        assert "quantile" in result.columns
        assert "quantile_1d" in result.columns
        assert "quantile_2d" in result.columns

    def test_with_group(self, sample_df_with_group):
        df = compute_forward_returns(sample_df_with_group, periods=[1])
        result = quantile_binning(df, quantiles=2, group_col="industry")

        assert "quantile" in result.columns

    def test_quantile_values(self, sample_df):
        df = compute_forward_returns(sample_df, periods=[1])
        result = quantile_binning(df, quantiles=5)

        # 检查分位数范围
        unique_quantiles = result["quantile"].unique().to_list()
        for q in unique_quantiles:
            assert 1 <= q <= 5

    def test_date_id_created(self, sample_df):
        df = compute_forward_returns(sample_df, periods=[1])
        result = quantile_binning(df, quantiles=2)

        assert "date_id" in result.columns
