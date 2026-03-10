from __future__ import annotations

import datetime
from typing import Literal, overload

import polars as pl

from .base import Calendar

# --- Polars Expression Generators ---


def to_date(date: str) -> pl.Expr:
    """
    生成将字符串转换为日期的 Polars 表达式。

    Args:
        date: 日期字符串 (YYYY-MM-DD)。

    Returns:
        pl.Expr: Polars 表达式。
    """
    return pl.lit(date).str.to_date()


def to_datetime(date: str, time: str) -> pl.Expr:
    """
    生成将日期和时间字符串合并转换为 datetime 的 Polars 表达式。

    Args:
        date: 日期字符串 (YYYY-MM-DD)。
        time: 时间字符串 (HH:MM:SS)。

    Returns:
        pl.Expr: Polars 表达式。
    """
    return (pl.lit(date) + " " + pl.lit(time)).str.to_datetime(
        time_unit="ms", time_zone="Asia/Shanghai"
    )


def to_time(time: str) -> pl.Expr:
    """
    生成将字符串转换为时间的 Polars 表达式。

    Args:
        time: 时间字符串 (HH:MM:SS)。

    Returns:
        pl.Expr: Polars 表达式。
    """
    return pl.lit(time).str.to_time()


# --- Global Calendar Instance ---

CALENDAR = Calendar()


# --- Trading Day Utilities ---


def get_tradingdays(
    beg_date: str | None = None,
    end_date: str | None = None,
    to_str: bool = True,
) -> list[str] | list[datetime.date]:
    """
    获取指定范围内的交易日列表。

    Args:
        beg_date: 开始日期 (YYYY-MM-DD)，默认为 None (最早)
        end_date: 结束日期 (YYYY-MM-DD)，默认为 None (最晚)
        to_str: 是否返回字符串列表。True 返回 List[str], False 返回 List[datetime.date]
    """
    df = CALENDAR.get_tradingdays(beg_date, end_date)
    if to_str:
        return df["date"].cast(pl.Utf8).to_list()
    else:
        return df["date"].to_list()


@overload
def today(as_obj: Literal[False] = False) -> str: ...


@overload
def today(as_obj: Literal[True]) -> datetime.date: ...


def today(as_obj: bool = False) -> str | datetime.date:
    """
    获取当前日期。

    Args:
        as_obj: 是否返回 datetime.date 对象。默认为 False (返回字符串)。

    Returns:
        str | datetime.date: 当前日期。
    """
    now_dt = datetime.datetime.now()
    return now_dt.date() if as_obj else now_dt.strftime("%Y-%m-%d")


@overload
def now(as_obj: Literal[False] = False) -> str: ...


@overload
def now(as_obj: Literal[True]) -> datetime.datetime: ...


def now(as_obj: bool = False) -> str | datetime.datetime:
    """
    获取当前时间。

    Args:
        as_obj: 是否返回 datetime.datetime 对象。默认为 False (返回字符串 "YYYY-MM-DD HH:MM:SS")。

    Returns:
        str | datetime.datetime: 当前时间。
    """
    dt = datetime.datetime.now()
    return dt if as_obj else dt.strftime("%Y-%m-%d %H:%M:%S")


def shift_tradeday(date: str, num: int = 1) -> str:
    """
    偏移交易日。

    Args:
        date: 基准日期 (YYYY-MM-DD)
        num: 偏移量。正数向后偏移，负数向前偏移。0 返回原日期。
             如果 date 不是交易日：
             - num > 0: 从 date 之后的第一个交易日开始计算偏移
             - num < 0: 从 date 之前的第一个交易日开始计算偏移
    """
    return CALENDAR.shift_tradeday(date, num)


def is_tradeday(date: str) -> bool:
    """判断是否为交易日"""
    return CALENDAR.is_tradeday(date)


def update():
    """更新交易日历数据"""
    CALENDAR.update()


def get_previous_report_dates(
    date: str | datetime.date, n: int = 1, season: int = None, to_str: bool = True
) -> list[str] | list[datetime.date]:
    """
    获取指定日期之前的 n 个报告期。

    Args:
        date: 当前日期
        n: 报告期个数
        season: 季度 (1, 2, 3, 4) 或 None。
               None 表示连续报告期。
               1-4 表示只获取对应季度的报告期 (如 season=1 只获取 3月31日)。
        to_str: 是否返回字符串列表
    """
    if isinstance(date, str):
        d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, datetime.datetime):
        d = date.date()
    else:
        d = date

    y = d.year
    candidates = [
        datetime.date(y, 3, 31),
        datetime.date(y, 6, 30),
        datetime.date(y, 9, 30),
        datetime.date(y, 12, 31),
    ]

    anchor = None
    for cand in reversed(candidates):
        if cand <= d:
            anchor = cand
            break

    if anchor is None:
        anchor = datetime.date(y - 1, 12, 31)

    result = []
    current = anchor

    loops = 0
    while len(result) < n:
        loops += 1
        if loops > 10000:  # Safety break
            break

        # Check season
        if season is not None:
            target_month = season * 3
            if current.month == target_month:
                result.append(current)
        else:
            result.append(current)

        # Move previous
        curr_m = current.month
        curr_y = current.year

        if curr_m == 3:
            current = datetime.date(curr_y - 1, 12, 31)
        elif curr_m == 6:
            current = datetime.date(curr_y, 3, 31)
        elif curr_m == 9:
            current = datetime.date(curr_y, 6, 30)
        elif curr_m == 12:
            current = datetime.date(curr_y, 9, 30)

    result.reverse()

    if to_str:
        return [r.strftime("%Y-%m-%d") for r in result]
    return result


def get_last_tradingday(date: str) -> str:
    """获取指定日期之前(含)最近的一个交易日"""
    return CALENDAR.get_recent_tradeday(date)


def generate_time_list(
    date: str,
    interval: str,
    beg_time: str = "09:30:00",
    end_time: str = "15:00:00",
) -> pl.DataFrame:
    """
    生成指定日期的交易时间序列 DataFrame。
    排除中午休市时间 (11:30:00 - 13:00:00)。

    :param date: 日期 (str, "YYYY-MM-DD")
    :param interval: 时间间隔 (str, e.g. "1m", "3s", "100ms")
    :param beg_time: 开始时间 (str, "HH:MM:SS")
    :param end_time: 结束时间 (str, "HH:MM:SS")
    :return: pl.DataFrame with columns ["datetime", "time"]
    """
    # Parse timestamps
    start_dt = datetime.datetime.strptime(f"{date} {beg_time}", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")

    # Define lunch break boundaries (using time objects for faster comparison)
    lunch_start = datetime.time(11, 30, 0)
    lunch_end = datetime.time(13, 0, 0)

    # Generate range and process in Polars
    # Using lazy execution chain where possible, though datetime_range eager=True returns Series
    return (
        pl.datetime_range(
            start=start_dt,
            end=end_dt,
            interval=interval,
            time_unit="ms",
            time_zone="Asia/Shanghai",
            eager=True,
        )
        .alias("datetime")
        .to_frame()
        .filter(
            (pl.col("datetime").dt.time() <= lunch_start)
            | (pl.col("datetime").dt.time() >= lunch_end)
        )
        .with_columns(time=pl.col("datetime").dt.strftime("%H:%M:%S"))
    )


# def get_last_report_date()
