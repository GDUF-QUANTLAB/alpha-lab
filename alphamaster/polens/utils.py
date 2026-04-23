"""工具函数模块。

提供交易日历对齐、收益率计算、分位数分箱等辅助功能。
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl
else:
    import polars as pl


def align_with_calendar(df: pl.DataFrame) -> pl.DataFrame:
    """与交易日历对齐，防止 shift 操作跳过非交易日。

    如果 xcals 不可用，则返回原 DataFrame。

    Args:
        df: 包含 date, asset 的 DataFrame

    Returns:
        对齐后的 DataFrame
    """
    try:
        import xcals
    except ImportError:
        warnings.warn(
            "xcals 不可用，交易日历对齐已跳过。这可能导致 shift 操作跳过非交易日。",
            UserWarning,
            stacklevel=2,
        )
        return df

    # 检查 date 列类型
    is_date_string = df.schema["date"] == pl.Utf8

    min_date = df["date"].min()
    max_date = df["date"].max()

    # 转换为字符串
    if not is_date_string:
        min_date_str = str(min_date)
        max_date_str = str(max_date)
    else:
        min_date_str = min_date
        max_date_str = max_date

    # 获取交易日历
    all_dates = xcals.get_tradingdays(min_date_str, max_date_str, to_str=is_date_string)
    calendar_df = pl.DataFrame({"date": all_dates})

    # 如果 xcals 返回字符串但原始数据是 Date 类型
    if not is_date_string and calendar_df.schema["date"] == pl.Utf8:
        calendar_df = calendar_df.with_columns(pl.col("date").str.to_date())

    # 创建骨架
    assets = df.select("asset").unique()
    skeleton = assets.join(calendar_df, how="cross")

    # 左连接原始数据
    aligned = skeleton.join(df, on=["asset", "date"], how="left")

    # 过滤掉因子值为空的行（这些是为了对齐添加的）
    return aligned.filter(pl.col("value").is_not_null())


def compute_forward_returns(
    df: pl.DataFrame,
    periods: list[int],
    *,
    demean: bool = False,
) -> pl.DataFrame:
    """计算远期收益率。

    计算逻辑: ret_n = vwap_adj(t+n) / vwap_adj(t) - 1
    强制包含 1d 收益，用于累积计算。

    Args:
        df: 包含 vwap, adj_factor 的 DataFrame
        periods: 收益计算周期列表
        demean: 是否计算超额收益（减去当日均值）

    Returns:
        包含 ret_{{n}}d 列的 DataFrame
    """
    # 1. 计算复权价格
    df = df.with_columns((pl.col("vwap") * pl.col("adj_factor")).alias("vwap_adj"))

    # 2. 强制包含 1d 收益
    calc_periods = set(periods)
    calc_periods.add(1)

    # 3. 计算远期收益
    return_exprs: list[pl.Expr] = []
    for n in calc_periods:
        return_exprs.append(
            (
                pl.col("vwap_adj").shift(-n).over("asset", order_by="date")
                / pl.col("vwap_adj")
                - 1
            ).alias(f"ret_{n}d")
        )

    df = df.sort("date").with_columns(return_exprs)

    # 4. 去均值
    if demean:
        demean_exprs: list[pl.Expr] = []
        has_avail = "avail" in df.columns

        for n in calc_periods:
            col_name = f"ret_{n}d"

            if has_avail:
                daily_mean = (
                    pl.col(col_name)
                    .filter(pl.col("avail").cast(pl.Boolean))
                    .mean()
                    .over("date")
                )
            else:
                daily_mean = pl.col(col_name).mean().over("date")

            demean_exprs.append((pl.col(col_name) - daily_mean).alias(col_name))

        df = df.with_columns(demean_exprs)

    return df


def quantile_binning(
    df: pl.DataFrame,
    quantiles: int = 5,
    group_col: str | None = None,
) -> pl.DataFrame:
    """分位数分箱，支持定期调仓。

    为每个周期 n 创建 quantile_{{n}}d 列：
    - n=1: 每日调仓，直接使用 quantile
    - n>1: 定期调仓，每 n 个交易日重新分箱

    Args:
        df: 包含 value 列的 DataFrame
        quantiles: 分位数数量
        group_col: 分组列名（用于分组分箱）

    Returns:
        包含 quantile 和 quantile_{{n}}d 列的 DataFrame
    """
    # 生成 date_id 用于判断调仓日
    df = df.sort("date").with_columns(pl.col("date").rank("dense").alias("date_id"))

    # 每日分箱
    if group_col is None:
        q_daily = (
            pl.col("value")
            .rank(method="ordinal")
            .qcut(
                quantiles,
                labels=[str(i) for i in range(1, quantiles + 1)],
                allow_duplicates=True,
            )
            .over("date")
            .cast(pl.Utf8)
            .cast(pl.Int32)
        )
    else:
        q_daily = (
            pl.col("value")
            .rank(method="ordinal")
            .qcut(
                quantiles,
                labels=[str(i) for i in range(1, quantiles + 1)],
                allow_duplicates=True,
            )
            .over(["date", group_col])
            .cast(pl.Utf8)
            .cast(pl.Int32)
        )

    df = df.with_columns(q_daily.alias("quantile"))

    # 为不同周期创建分箱列
    periods = [
        int(col.split("_")[1][:-1])
        for col in df.columns
        if col.startswith("ret_") and col.endswith("d")
    ]

    for n in periods:
        if n == 1:
            df = df.with_columns(pl.col("quantile").alias(f"quantile_{n}d"))
        else:
            df = df.with_columns(
                pl.when((pl.col("date_id") - 1) % n == 0)
                .then(pl.col("quantile"))
                .otherwise(None)
                .forward_fill()
                .over("asset", order_by="date")
                .alias(f"quantile_{n}d")
            )

    return df
