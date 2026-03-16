from __future__ import annotations

import polars as pl

import blazestore as bs

from ..base import get_data
from ..enums import DataType, Instrument


def read_tick(date: str, instrument: Instrument) -> pl.LazyFrame:
    """
    Reads tick data for a specific instrument and date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type.

    Returns:
        pl.LazyFrame: A LazyFrame containing tick data.
    """
    d = get_data(instrument, DataType.TICK)
    return (
        bs.sql(f"select * from {d.local} where date = '{date}'")
        .with_columns(pl.col("datetime").dt.convert_time_zone("Asia/Shanghai"))
        .with_columns(time=pl.col("datetime").dt.time())
    )


def read_kline_day(date: str, instrument: Instrument) -> pl.LazyFrame:
    """
    Reads daily K-line data for a specific instrument and date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type.

    Returns:
        pl.LazyFrame: A LazyFrame containing daily K-line data.

    Raises:
        ValueError: If no data is found for the specified date.
    """
    d = get_data(instrument, DataType.KLINE_DAY)
    result = bs.sql(f"select * from {d.local} where date = '{date}'")
    if result.select("date").collect().height == 0:
        raise ValueError(f"No daily K-line data found for {d} on {date}")
    return result


def read_kline_minute(date: str, instrument: Instrument) -> pl.LazyFrame:
    """
    Reads minute K-line data for a specific instrument and date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type.

    Returns:
        pl.LazyFrame: A LazyFrame containing minute K-line data.

    Raises:
        ValueError: If no data is found for the specified date.
    """
    d = get_data(instrument, DataType.KLINE_MINUTE)
    result = (
        bs.sql(f"select * from {d.local} where date = '{date}'")
        .with_columns(pl.col("datetime").dt.convert_time_zone("Asia/Shanghai"))
        .with_columns(time=pl.col("datetime").dt.time())
    )
    if result.select("date").collect().height == 0:
        raise ValueError(f"No minute K-line data found for {d} on {date}")
    return result


def read_data(date: str, instrument: Instrument, datatype: DataType) -> pl.LazyFrame:
    """
    Reads specific data type for a specific instrument and date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type.
        datatype: Data type to read.

    Returns:
        pl.LazyFrame: A LazyFrame containing requested data.

    Raises:
        ValueError: If no data is found for the specified date.
    """
    d = get_data(instrument, datatype)
    result = bs.sql(f"select * from {d.local} where date = '{date}'")
    if result.select("date").collect().height == 0:
        raise ValueError(f"No data found for {d} on {date}")
    return result


def read_data_batch(
    beg_date: str, end_date: str, instrument: Instrument, datatype: DataType
) -> pl.LazyFrame:
    """
    Reads specific data type for a specific instrument within a date range.

    Args:
        beg_date: Start date string in YYYY-MM-DD format.
        end_date: End date string in YYYY-MM-DD format.
        instrument: Financial instrument type.
        datatype: Data type to read.

    Returns:
        pl.LazyFrame: A LazyFrame containing requested data.
    """
    d = get_data(instrument, datatype)
    return bs.sql(
        f"select * from {d.local} where date between '{beg_date}' and '{end_date}'"
    )


def read_perfect_tick(date: str) -> pl.LazyFrame:
    """
    Reads 'perfect' tick data (with cumulative fields) for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format.

    Returns:
        pl.LazyFrame: A LazyFrame containing processed tick data.
    """
    return (
        bs.sql(f"select * from cache/pob where date = '{date}'")
        .with_columns(
            cum_amount=pl.col("amount"),
            cum_volume=pl.col("volume"),
            cum_num_trades=pl.col("num_trades"),
        )
        .with_columns(
            pl.col("amount").diff(1).over("asset", order_by="datetime").fill_null(0),
            pl.col("volume").diff(1).over("asset", order_by="datetime").fill_null(0),
            pl.col("num_trades")
            .diff(1)
            .over("asset", order_by="datetime")
            .fill_null(0),
        )
    )


def stk_kline_day() -> pl.LazyFrame:
    """Reads all stock daily K-line data."""
    d = get_data(Instrument.STOCK, DataType.KLINE_DAY)
    return bs.sql(f"select * from {d.local}")


def stk_kline_minute() -> pl.LazyFrame:
    """Reads all stock minute K-line data."""
    d = get_data(Instrument.STOCK, DataType.KLINE_MINUTE)
    return bs.sql(f"select * from {d.local}")


def stk_tick() -> pl.LazyFrame:
    """Reads all stock tick data."""
    d = get_data(Instrument.STOCK, DataType.TICK)
    return bs.sql(f"select * from {d.local}")
