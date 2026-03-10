from __future__ import annotations

import polars as pl

import blazestore as bs
from tool_box import xcals

from .table import DataType, Instrument, get_data

# Common filter for A-shares
ASHARE_PREFIXES = ["6", "3", "0"]


def codes(date: str, instrument: Instrument = Instrument.STOCK) -> pl.LazyFrame:
    """
    Reads codes for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing all codes for the specified instrument on the given date.
    """
    local_tb_name = get_data(instrument, datatype=DataType.SECUMAIN).local
    return (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .filter(pl.col("ListedDate").is_not_null())
        .with_columns(pl.col("ListedDate").str.to_date())
        .filter(
            pl.col("ListedDate") <= pl.lit(date).str.to_date(),  # Date safety
        )
        .sort("ListedDate")
        .group_by("asset")
        .agg(
            pl.col("InnerCode").sort_by("ListedDate").last(),
            pl.col("SecuCode").sort_by("ListedDate").last(),
            pl.col("SecuAbbr").sort_by("ListedDate").last(),
            pl.col("SecuMarket").sort_by("ListedDate").last(),
            pl.col("ListedSector").sort_by("ListedDate").last(),
            pl.col("ListedState").sort_by("ListedDate").last(),
            pl.col("ListedDate").sort_by("ListedDate").last(),
        )
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .sort("asset")
    )


def asset(date: str) -> pl.LazyFrame:
    """
    Reads available stock codes for a specific date with filtering criteria.

    Filtering criteria:
    1. Normal listing status.
    2. Listed for at least 90 days.
    3. Normal industry classification.
    4. Normal share capital data.
    5. Not ST (Special Treatment).

    Args:
        date: Date string in YYYY-MM-DD format.

    Returns:
        pl.LazyFrame: A filtered LazyFrame of available assets.
    """
    ids = industry(date).drop_nulls().select("asset").collect()
    shs = shares(date).drop_nulls().select("asset").collect()
    cds = (
        codes(date)
        .filter(
            (pl.lit(date).str.to_date() - pl.col("ListedDate"))
            .dt.total_days()
            .cast(int)
            >= 90,
            pl.col("ListedState").cast(int) == 1,  # Normal listing status
        )
        .select("asset")
        .collect()
    )
    st = (
        special_trades(date)
        .filter(pl.col("value").fill_null(0) == 0)
        .select("asset")
        .collect()
    )
    for i in [ids, shs, st]:
        cds = cds.join(i, on="asset", how="inner")
    return cds.sort("asset").lazy()


def industry(date: str, instrument: Instrument = Instrument.STOCK) -> pl.LazyFrame:
    """
    Reads industry classification info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing industry classification info.
    """
    local_tb_name = get_data(instrument, datatype=DataType.INDUSTRY).local
    return (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .with_columns(pl.col("InfoPublDate").str.to_date())
        .filter(pl.col("InfoPublDate") < xcals.to_date(date))
        .group_by("asset")
        .agg(
            pl.col("Lv1").sort_by("InfoPublDate").last(),
            pl.col("Lv2").sort_by("InfoPublDate").last(),
            pl.col("Lv3").sort_by("InfoPublDate").last(),
        )
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .sort("asset")
    )


def shares(
    date: str,
    instrument: Instrument = Instrument.STOCK,
) -> pl.LazyFrame:
    """
    Reads floating and total shares info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing shares information.
    """
    local_tb_name = get_data(instrument, datatype=DataType.SHARES).local
    data = (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .with_columns(
            pl.col("EndDate").str.to_date(),
            pl.col("InfoPublDate").str.to_date(),
        )
        .filter(pl.col("InfoPublDate") < xcals.to_date(date))
        .sort("InfoPublDate")
    )

    return (
        data.group_by("asset")
        .agg(
            pl.col("TotalShares").sort_by("EndDate").last(),
            pl.col("AShares").sort_by("EndDate").last(),
            pl.col("AFloats").sort_by("EndDate").last(),
        )
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .sort("asset")
    )


def capital(
    date: str,
    instrument: Instrument = Instrument.STOCK,
) -> pl.LazyFrame:
    """
    Reads capital structure info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing capital structure information.
    """
    local_tb_name = get_data(instrument, datatype=DataType.CAPITAL).local
    return (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .with_columns(
            pl.col("InfoPublDate").str.to_date(),
            pl.col("ChangeDate").str.to_date(),
        )
        .filter(
            pl.col("InfoPublDate") < xcals.to_date(date),
            pl.col("ChangeDate") <= xcals.to_date(date),
        )
        .group_by("asset")
        .agg(pl.all().sort_by("InfoPublDate").last())
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .sort("asset")
    )


def special_trades(
    date: str, instrument: Instrument = Instrument.STOCK
) -> pl.LazyFrame:
    """
    Reads dividend and bonus share info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing special trade information.
    """
    local_tb_name = get_data(instrument, datatype=DataType.ST).local

    c = codes(date=date, instrument=instrument)
    d = (
        bs.sql(f"select * from {local_tb_name}")
        .with_columns(
            pl.col("InfoPublDate").str.to_date(),
            pl.col("SpecialTradeDate").str.to_date(),
        )
        .filter(pl.col("InfoPublDate") < pl.lit(date).str.to_date())
        .sort("InfoPublDate")
        .group_by("InnerCode")
        .agg(pl.all().sort_by("SpecialTradeDate").last())
    )

    return (
        c.select("asset", "InnerCode", "SecuAbbr")
        .join(d, on="InnerCode", how="left")
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .sort("asset")
        .with_columns(
            value=pl.col("SpecialTradeType")
            .is_in([1, 3, 5, 7, 8, 9, 10, 12, 13, 14, 15])
            .cast(int)
            .fill_null(0)
        )
    )


def adj_factors(
    date: str,
    instrument: Instrument = Instrument.STOCK,
) -> pl.LazyFrame:
    """
    Reads adjustment factor info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing adjustment factors.
    """
    code = codes(date, Instrument.STOCK).select("asset", "InnerCode")
    d = get_data(instrument, DataType.ADJFAC)

    return code.join(
        bs.sql(f"select * from {d.local}")
        .filter(
            pl.col("ExDiviDate").str.to_date() <= xcals.to_date(date),
        )
        .group_by(
            "InnerCode",
        )
        .agg(pl.col("AdjustingFactor").sort_by("ExDiviDate").last())
        .sort("InnerCode"),
        on="InnerCode",
    ).select("asset", pl.col("AdjustingFactor").alias("value"))


def mainshlistnew(
    date: str,
    instrument: Instrument = Instrument.STOCK,
) -> pl.LazyFrame:
    """
    Reads listing info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.

    Returns:
        pl.LazyFrame: A LazyFrame containing listing information.
    """
    local_tb_name = get_data(instrument, datatype=DataType.MAINSHLIST).local
    return (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .with_columns(
            pl.col("InfoPublDate").str.to_date(),
            pl.col("EndDate").str.to_date(),
        )
        .filter(
            pl.col("InfoPublDate") < xcals.to_date(date),
        )
        .filter(pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES))
        .filter(pl.col("InfoPublDate") == pl.col("InfoPublDate").max().over("asset"))
        .sort("asset")
    )


def financial_index(
    date: str,
    instrument: Instrument = Instrument.STOCK,
    fields: list[str] | None = None,
) -> pl.LazyFrame:
    """
    Reads financial index info for stocks/indices/futures/convertible bonds on a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type. Defaults to Instrument.STOCK.
        fields: List of fields to select. Defaults to None.

    Returns:
        pl.LazyFrame: A LazyFrame containing financial index information.
    """
    local_tb_name = get_data(instrument, datatype=DataType.FINANCIAL_INDEX).local

    return (
        bs.sql(f"select SecuCode as asset, * from {local_tb_name}")
        .with_columns(
            pl.col("InfoPublDate").str.to_date(),
            pl.col("EndDate").str.to_date(),
        )
        .filter(
            pl.col("InfoPublDate") < xcals.to_date(date),
            pl.col("asset").str.slice(0, 1).is_in(ASHARE_PREFIXES),
            pl.col("Mark").is_in([1, 2]),
        )
        .group_by("asset", "EndDate")
        .agg(pl.all().sort_by("EndDate").last())
    )
