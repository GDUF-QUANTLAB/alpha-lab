"""
FactorAnalyzer 测试
"""

import polars as pl
import pytest

from alphamaster.polens import FactorAnalyzer


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


@pytest.fixture
def sample_df_with_avail():
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
            "avail": [True, True, True, False, True, True],
        }
    ).with_columns(pl.col("date").str.to_date())


class TestFactorAnalyzer:
    def test_init(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        assert analyzer.raw_df is not None
        assert analyzer.processed_df is None

    def test_init_missing_columns(self):
        df = pl.DataFrame({"date": ["2023-01-01"], "asset": ["A"]})
        with pytest.raises(ValueError):
            FactorAnalyzer(df)

    def test_preprocess(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)

        assert analyzer.processed_df is not None
        assert "ret_1d" in analyzer.processed_df.columns
        assert "quantile" in analyzer.processed_df.columns

    def test_preprocess_multiple_periods(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1, 2, 5], quantiles=5, align_calendar=False)

        assert "ret_1d" in analyzer.processed_df.columns
        assert "ret_2d" in analyzer.processed_df.columns
        assert "ret_5d" in analyzer.processed_df.columns
        assert "quantile_1d" in analyzer.processed_df.columns
        assert "quantile_2d" in analyzer.processed_df.columns
        assert "quantile_5d" in analyzer.processed_df.columns

    def test_preprocess_with_demean(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False, demean=True)

        assert analyzer.processed_df is not None
        assert "ret_1d" in analyzer.processed_df.columns

    def test_preprocess_with_avail_filter(self, sample_df_with_avail):
        analyzer = FactorAnalyzer(sample_df_with_avail)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)

        # avail=False 的行应该被过滤掉
        processed = analyzer.processed_df
        assert processed is not None

    def test_preprocess_with_group(self, sample_df_with_group):
        analyzer = FactorAnalyzer(sample_df_with_group, group_col="industry")
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)

        assert analyzer.processed_df is not None
        assert "quantile" in analyzer.processed_df.columns

    def test_analyze(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)
        analyzer.analyze()

        assert analyzer.ic_df is not None
        assert "ic_1d" in analyzer.ic_df.columns
        assert "rank_ic_1d" in analyzer.ic_df.columns

    def test_analyze_multiple_periods(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1, 2], quantiles=2, align_calendar=False)
        analyzer.analyze()

        assert analyzer.ic_df is not None
        assert "ic_1d" in analyzer.ic_df.columns
        assert "rank_ic_1d" in analyzer.ic_df.columns
        assert "ic_2d" in analyzer.ic_df.columns
        assert "rank_ic_2d" in analyzer.ic_df.columns

        # 检查 quantile_ret_df 和 turnover_df
        assert 1 in analyzer.quantile_ret_df
        assert 2 in analyzer.quantile_ret_df
        assert 1 in analyzer.turnover_df
        assert 2 in analyzer.turnover_df

    def test_analyze_with_group(self, sample_df_with_group):
        analyzer = FactorAnalyzer(sample_df_with_group, group_col="industry")
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)
        analyzer.analyze()

        assert analyzer.ic_df is not None
        assert analyzer.ic_by_group_df is not None
        assert "industry" in analyzer.ic_by_group_df.columns

    def test_summary_stats(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)
        analyzer.analyze()

        stats = analyzer.summary_stats()
        assert "1d" in stats
        assert "RankIC" in stats["1d"]
        assert "RankICIR" in stats["1d"]
        assert "RankIC_t_stat" in stats["1d"]
        assert "RankIC_p_value" in stats["1d"]
        assert "Turnover_TopQ" in stats["1d"]

    def test_summary_stats_multiple_periods(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1, 2], quantiles=2, align_calendar=False)
        analyzer.analyze()

        stats = analyzer.summary_stats()
        assert "1d" in stats
        assert "2d" in stats
        assert "RankIC" in stats["1d"]
        assert "RankIC" in stats["2d"]

    def test_chain_call(self, sample_df):
        analyzer = (
            FactorAnalyzer(sample_df)
            .preprocess(periods=[1], quantiles=2, align_calendar=False)
            .analyze()
        )

        assert analyzer.ic_df is not None
        assert analyzer.processed_df is not None

    def test_access_processed_before_preprocess(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        assert analyzer.processed_df is None

    def test_access_results_before_analysis(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)

        assert analyzer.ic_df is None
        with pytest.raises(RuntimeError):
            analyzer.summary_stats()

    def test_analyze_before_preprocess(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        with pytest.raises(RuntimeError):
            analyzer.analyze()

    def test_autocorr_df(self, sample_df):
        analyzer = FactorAnalyzer(sample_df)
        analyzer.preprocess(periods=[1], quantiles=2, align_calendar=False)
        analyzer.analyze()

        assert analyzer.autocorr_df is not None
        assert "autocorr" in analyzer.autocorr_df.columns
