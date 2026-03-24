"""因子分析指标计算模块。

提供 IC、分层收益、换手率等核心指标的计算。
所有方法均为静态方法，无状态设计。
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats


class FactorMetrics:
    """因子分析核心指标计算工具类。

    所有方法均为静态方法，不保存任何状态。

    Example:
        >>> ic_df = FactorMetrics.calc_ic(df, periods=[1, 5, 10])
        >>> summary = FactorMetrics.calc_ic_summary(ic_df, periods=[1, 5, 10])
    """

    @staticmethod
    def calc_ic(df: pl.DataFrame, periods: list[int]) -> pl.DataFrame:
        """计算每日 IC (Information Coefficient)。

        同时计算 Pearson IC 和 Spearman Rank IC。

        Args:
            df: 包含 value 和 ret_{{n}}d 列的 DataFrame
            periods: 期限列表

        Returns:
            每日 IC 数据，列名为 date, ic_{{n}}d, rank_ic_{{n}}d
        """
        exprs = []
        for n in periods:
            ret_col = f"ret_{n}d"
            # Pearson IC
            exprs.append(pl.corr("value", ret_col).alias(f"ic_{n}d"))
            # Rank IC (Spearman)
            exprs.append(
                pl.corr("value", ret_col, method="spearman").alias(f"rank_ic_{n}d")
            )

        return df.group_by("date").agg(exprs).sort("date")

    @staticmethod
    def calc_ic_summary(
        ic_df: pl.DataFrame, periods: list[int]
    ) -> dict[str, dict[str, float]]:
        """计算 IC 的统计指标。

        计算 RankIC 的均值、标准差、ICIR、t统计量和p值。

        Args:
            ic_df: calc_ic 的输出结果
            periods: 期限列表

        Returns:
            格式: {{"nd": {{"RankIC": float, "RankICIR": float, ...}}, ...}}
        """
        summary: dict[str, dict[str, float]] = {}
        for n in periods:
            col = f"rank_ic_{n}d"
            # 填充 NaN/Null
            data = ic_df[col].fill_nan(0).fill_null(0).to_numpy()

            if len(data) < 2:
                summary[f"{n}d"] = {
                    "RankIC": float(np.nan),
                    "RankICIR": float(np.nan),
                    "RankIC_t_stat": float(np.nan),
                    "RankIC_p_value": float(np.nan),
                }
                continue

            mean_ic = float(np.mean(data))
            std_ic = float(np.std(data, ddof=1))
            icir = mean_ic / std_ic if std_ic > 1e-9 else float(np.nan)

            # T-test
            t_stat, p_val = stats.ttest_1samp(data, 0)

            summary[f"{n}d"] = {
                "RankIC": mean_ic,
                "RankICIR": icir,
                "RankIC_t_stat": float(t_stat),
                "RankIC_p_value": float(p_val),
            }

        return summary

    @staticmethod
    def calc_ic_by_group(
        df: pl.DataFrame, periods: list[int], group_col: str
    ) -> pl.DataFrame:
        """计算分组 IC (例如分行业 IC)。

        使用 Index 补全确保所有日期×分组组合存在（缺失值填 0）。

        Args:
            df: 包含 value, ret_{{n}}d 和 group_col 的 DataFrame
            periods: 期限列表
            group_col: 分组列名 (例如 "industry")

        Returns:
            各组的平均 RankIC
        """
        exprs = []
        for n in periods:
            ret_col = f"ret_{n}d"
            exprs.append(
                pl.corr("value", ret_col, method="spearman").alias(f"rank_ic_{n}d")
            )

        # 计算每日每组的 IC
        daily_group_ic = (
            df.filter(pl.col(group_col).is_not_null())
            .group_by(["date", group_col])
            .agg(exprs)
        )

        # Index 补全：构建完整的日期×分组 Index
        dates = daily_group_ic.select("date").drop_nulls().unique().sort("date")
        groups = daily_group_ic.select(group_col).drop_nulls().unique().sort(group_col)
        full_index = dates.join(groups, how="cross")

        # 左连接补全缺失值
        daily_group_ic = full_index.join(
            daily_group_ic, on=["date", group_col], how="left"
        )

        # 计算时间平均（缺失值填 0）
        mean_exprs = [
            pl.col(f"rank_ic_{n}d")
            .fill_nan(0)
            .fill_null(0)
            .mean()
            .alias(f"rank_ic_{n}d")
            for n in periods
        ]

        return daily_group_ic.group_by(group_col).agg(mean_exprs).sort(group_col)

    @staticmethod
    def calc_quantile_returns(
        df: pl.DataFrame,
        periods: list[int],
        quantile_col: str = "quantile",
        quantiles: int = 5,
    ) -> pl.DataFrame:
        """计算各分层的平均收益率。

        注意：无论 periods 是多少，分层收益始终基于 ret_1d 计算。
        这是因为分层收益反映的是组合的日度表现，用于累积收益计算。
        periods 参数仅用于保持接口一致性，实际不参与计算。

        使用 Index 补全确保所有日期×分位数组合存在（缺失值填 null）。

        Args:
            df: 包含 quantile 和 ret_1d 列的 DataFrame
            periods: 期限列表（仅用于接口兼容，不参与计算）
            quantile_col: 分层列名
            quantiles: 分层数量

        Returns:
            各分层每日平均收益（仅包含 ret_1d 列）
        """
        # 分层收益始终基于 ret_1d 计算
        # 这是正确的做法：分层收益反映组合的日度表现
        exprs: list[pl.Expr] = [pl.col("ret_1d").mean().alias("ret_1d")]

        # 计算实际数据的分层收益
        res = (
            df.filter(pl.col(quantile_col).is_not_null())
            .group_by(["date", quantile_col])
            .agg(exprs)
            .rename({quantile_col: "quantile"})
        )

        # Index 补全：构建完整的日期×分位数 Index
        dates = res.select("date").unique()
        q_range = pl.DataFrame(
            {"quantile": list(range(1, quantiles + 1))}, schema={"quantile": pl.Int32}
        )
        full_index = dates.join(q_range, how="cross")

        # 左连接补全缺失值
        return full_index.join(res, on=["date", "quantile"], how="left").sort(
            "date", "quantile"
        )

    @staticmethod
    def calc_turnover(
        df: pl.DataFrame, quantiles: int = 5, quantile_col: str = "quantile"
    ) -> pl.DataFrame:
        """计算换手率。

        换手率定义为：分位数发生变化的股票数 / 该层总股票数

        Args:
            df: 包含 date, asset, quantile 的 DataFrame
            quantiles: 分层数量
            quantile_col: 分层列名

        Returns:
            各分层每日换手率
        """
        # 获取前一期分位数
        df = df.with_columns(
            pl.col(quantile_col).shift(1).over("asset").alias("prev_quantile")
        )

        # 计算换手率
        return (
            df.filter(pl.col("prev_quantile").is_not_null())
            .group_by(["date", quantile_col])
            .agg(
                (
                    (pl.col("prev_quantile") != pl.col(quantile_col))
                    .sum()
                    .cast(pl.Float64)
                    / pl.len()
                ).alias("turnover")
            )
            .sort(["date", quantile_col])
        )

    @staticmethod
    def calc_autocorrelation(
        df: pl.DataFrame, factor_col: str = "value", lag: int = 1
    ) -> pl.DataFrame:
        """计算因子自相关性。

        Args:
            df: 包含 value 列的 DataFrame
            factor_col: 因子列名
            lag: 滞后期数

        Returns:
            自相关系数
        """
        return (
            df.sort(["date", "asset"])
            .with_columns(
                pl.col(factor_col).shift(lag).over("asset").alias("factor_lag")
            )
            .select(pl.corr(pl.col(factor_col), pl.col("factor_lag")).alias("autocorr"))
        )
