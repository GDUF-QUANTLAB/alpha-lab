from __future__ import annotations

import polars as pl

import blazestore as bs

from .table import DataType, Instrument, get_data


def read_tick(date: str, instrument: Instrument) -> pl.LazyFrame:
    """
    Reads tick data for a specific instrument and date.

    Args:
        date: Date string in YYYY-MM-DD format.
        instrument: Financial instrument type.

    Returns:
        pl.LazyFrame: A LazyFrame containing tick data.
    """
    d = get_data(instrument, datatype=DataType.TICK)
    local_tb_name = d.local
    result = (
        bs.sql(f"select * from {local_tb_name} where date = '{date}'")
        .with_columns(pl.col("datetime").dt.convert_time_zone("Asia/Shanghai"))
        .with_columns(time=pl.col("datetime").dt.time())
    )
    return result


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
    d = get_data(instrument, datatype=DataType.KLINE_DAY)
    local_tb_name = d.local
    result = bs.sql(f"select * from {local_tb_name} where date = '{date}'")
    if result.select("date").collect().shape[0] == 0:
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
    d = get_data(instrument, datatype=DataType.KLINE_MINUTE)
    local_tb_name = d.local
    result = (
        bs.sql(f"select * from {local_tb_name} where date = '{date}'")
        .with_columns(pl.col("datetime").dt.convert_time_zone("Asia/Shanghai"))
        .with_columns(time=pl.col("datetime").dt.time())
    )
    if result.select("date").collect().shape[0] == 0:
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
        pl.LazyFrame: A LazyFrame containing the requested data.

    Raises:
        ValueError: If no data is found for the specified date.
    """
    d = get_data(instrument, datatype=datatype)
    local_tb_name = d.local
    result = bs.sql(f"select * from {local_tb_name} where date = '{date}'")
    if result.select("date").collect().shape[0] == 0:
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
        pl.LazyFrame: A LazyFrame containing the requested data.

    Raises:
        ValueError: If data is missing for some trading days in the range.
    """
    d = get_data(instrument, datatype=datatype)
    local_tb_name = d.local
    result = bs.sql(
        f"select * from {local_tb_name} where date between '{beg_date}' and '{end_date}'"
    )

    return result


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
            pl.col("amount").alias("cum_amount"),
            pl.col("volume").alias("cum_volume"),
            pl.col("num_trades").alias("cum_num_trades"),
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
    d = get_data(Instrument.STOCK, datatype=DataType.KLINE_DAY)
    local_tb_name = d.local
    result = bs.sql(f"select * from {local_tb_name}")
    return result


def stk_kline_minute() -> pl.LazyFrame:
    """Reads all stock minute K-line data."""
    d = get_data(Instrument.STOCK, datatype=DataType.KLINE_MINUTE)
    local_tb_name = d.local
    result = bs.sql(f"select * from {local_tb_name}")
    return result


def stk_tick() -> pl.LazyFrame:
    """Reads all stock tick data."""
    d = get_data(Instrument.STOCK, datatype=DataType.TICK)
    local_tb_name = d.local
    result = bs.sql(f"select * from {local_tb_name}")
    return result
