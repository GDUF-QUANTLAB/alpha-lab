"""
价格数据加载模块

提供价格相关的数据计算和缓存功能。

Example:
    >>> from alphamaster.loader import get_all_prices
    >>> prices = get_all_prices("2023-01-01", "2023-12-31", "09:30:00", "15:00:00")
"""

from __future__ import annotations

import polars as pl

import blazestore as bs
import datacenter as dc
from tool_box import xcals, ygo


def get_vwap(date: str, beg_time: str, end_time: str) -> pl.LazyFrame:
    return (
        dc.md.read_kline_minute(date, dc.Instrument.STOCK)
        .filter(
            pl.col("time").is_between(xcals.to_time(beg_time), xcals.to_time(end_time)),
            pl.col("amount") > 0,
            pl.col("volume") > 0,
        )
        .group_by("date", "asset")
        .agg(
            vwap=pl.col("amount").cast(float).sum()
            / pl.col("volume").cast(float).sum(),
            deal_amt=pl.col("amount").cast(float).sum(),
        )
    )


def update_vwap(date: str, beg_time: str, end_time: str) -> None:
    _temp = str(f"{beg_time}_{end_time}").replace(":", "")
    pth = f"cache/vwap/{_temp}/date={date}/data.parquet"
    db = bs.LocalStore()
    if not db.has(pth):
        df = get_vwap(date, beg_time, end_time)
        db.put(df, pth)


def get_batch_vwap(
    beg_date: str, end_date: str, beg_time: str, end_time: str
) -> pl.LazyFrame:
    _temp = str(f"{beg_time}_{end_time}").replace(":", "")
    all_days = xcals.get_tradingdays(beg_date, end_date)
    exits_days = (
        bs.LocalStore()
        .read(f"cache/vwap/{_temp}")
        .select(pl.col("date").unique())
        .collect()["date"]
        .cast(str)
        .to_list()
    )
    delta = set(all_days) - set(exits_days)
    if len(delta) > 0:
        with ygo.Pool() as go:
            for d in delta:
                go.submit(update_vwap, "UpdateVWAP")(
                    date=d, beg_time=beg_time, end_time=end_time
                )
            go.do()
    return bs.LocalStore().read(f"cache/vwap/{_temp}")


def get_adj_factor(target_date: str) -> pl.DataFrame:
    return dc.jy.adj_factors(target_date).sort("asset").collect()


def update_adj_factor(date: str) -> None:
    pth = f"cache/adj_factor/date={date}/data.parquet"
    db = bs.LocalStore()
    if not db.has(pth):
        df = get_adj_factor(date)
        db.put(df, pth)


def get_batch_adj_factor(beg_date: str, end_date: str) -> pl.LazyFrame:
    all_days = xcals.get_tradingdays(beg_date, end_date)
    db = bs.LocalStore()
    db.base_path.mkdir(parents=True, exist_ok=True)
    try:
        exist_days = (
            db.read("cache/adj_factor")
            .select(pl.col("date").unique())
            .collect()["date"]
            .cast(str)
            .to_list()
        )
    except Exception:
        exist_days = []
    delta = set(all_days) - set(exist_days)
    if len(delta) > 0:
        with ygo.Pool() as go:
            for d in delta:
                go.submit(update_adj_factor, "UpdateAdjFactor")(date=d)
            go.do()
    return db.read("cache/adj_factor")


def get_all_prices(
    beg_date: str, end_date: str, beg_time: str, end_time: str
) -> pl.DataFrame:
    other_prices = dc.md.read_data_batch(
        beg_date, end_date, dc.Instrument.STOCK, dc.DataType.KLINE_DAY
    ).select(
        "date",
        "asset",
        "limit_up",
        "limit_down",
        "close",
        "prev_close",
    )

    vwap_df = get_batch_vwap(beg_date, end_date, beg_time, end_time)

    adj_factor = get_batch_adj_factor(beg_date, end_date)
    other_prices = other_prices.join(adj_factor, on=["asset", "date"], how="left")

    df = other_prices.join(vwap_df, on=["asset", "date"], how="left").collect()

    return df
