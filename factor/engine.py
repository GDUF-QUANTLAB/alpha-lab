from __future__ import annotations

import pandas as pd
import polars as pl

from tool_box import xcals

from . import store
from .context import FactorContext
from .core import FIELD, INDEX, BasicFactor, delay
from .exceptions import FunctionComputeError


def get_day_list(beg_date: str, end_date: str, n: int):
    return (
        xcals.CALENDAR.get_tradingdays()
        .with_columns(pl.col(FIELD.DATE).shift(n).alias("lag_date"))
        .filter(
            pl.col(FIELD.DATE).is_between(
                xcals.to_date(beg_date), xcals.to_date(end_date)
            )
        )
    )


def get_value_online(fac: BasicFactor, date: str) -> pl.DataFrame:
    name = fac.name
    version = fac.version
    insert_time = fac.insert_time

    if len(fac._depends) > 0:
        cb = FactorContext(*fac._depends, loader_time=fac.insert_time)
        data = delay(fac.fn)(date=date, cb=cb)
    else:
        data = delay(fac.fn)(date=date)

    if data is None:
        raise FunctionComputeError(
            f"{name} | version:{version} | date:{date} | insert_time:{insert_time}: DATA IS NONE"
        )

    if isinstance(data, (pd.DataFrame, pd.Series)):
        data = pl.from_pandas(data, include_index=True)

    if data.is_empty():
        raise FunctionComputeError(
            f"{name} | version:{version} | date:{date} | insert_time:{insert_time}: DATA IS EMPTY"
        )

    value_columns = [i for i in data.columns if i not in INDEX]

    if FIELD.DATETIME not in value_columns:
        data = data.with_columns(
            xcals.to_datetime(date, insert_time).alias(FIELD.DATETIME)
        )

    data = data.select(*INDEX, *value_columns).unique(subset=INDEX).sort(*INDEX)

    data = data.unpivot(
        on=value_columns,
        index=INDEX,
        variable_name=FIELD.FIELDNAMES,
        value_name="value",
    )

    return data


def get_value(
    fac: BasicFactor,
    date: str,
    time: str = "15:00:00",
    rt: bool = True,
    lazy: bool = True,
) -> pl.DataFrame:
    if not xcals.is_tradeday(date):
        raise ValueError(f"{date} is not a trading day")

    if (time <= fac.insert_time) & rt:
        data_date = xcals.shift_tradeday(date, -1)
    else:
        data_date = date

    data = store.read_factor_day(fac.tb_name, data_date)
    if data is None:
        data = get_value_online(fac, data_date)

    if data[FIELD.FIELDNAMES].n_unique() > 1:
        data = data.pivot(on=FIELD.FIELDNAMES, index=FIELD.ASSET, values=FIELD.VALUE)
    data = data.select(FIELD.ASSET, pl.col(FIELD.VALUE).alias(fac.name))

    data = data.with_columns(xcals.to_datetime(date, time).alias(FIELD.DATETIME))
    return data.select(*INDEX, fac.name).sort(INDEX)


def get_update_tasks(
    fac: BasicFactor,
    beg_date: str,
    end_date: str,
):
    update_list = xcals.get_tradingdays(beg_date, end_date)
    exists_date = store.read_existing_dates(fac.tb_name)
    if exists_date:
        update_list = sorted(set(update_list) - set(exists_date))

    def worker(fac, date):
        df = get_value_online(fac, date)
        store.write_factor_day(fac.tb_name, date, df)

    return [delay(worker).bind(fac=fac, date=d) for d in update_list]


def get_history(
    fac: BasicFactor,
    beg_date: str,
    end_date: str,
    time: str = "15:00:00",
    rt: bool = True,
    lazy: bool = True,
) -> pl.DataFrame:
    _beg_date = beg_date
    _end_date = end_date
    d_frame = xcals.CALENDAR.get_tradingdays().with_columns(
        insert_date=pl.col(FIELD.DATE)
    )
    if rt and (time <= fac.insert_time):
        _beg_date = xcals.shift_tradeday(beg_date, -1)
        _end_date = xcals.shift_tradeday(end_date, -1)
        d_frame = d_frame.with_columns(pl.col("insert_date").shift(1))

    df_frame = d_frame.filter(
        pl.col("date").is_between(xcals.to_date(beg_date), xcals.to_date(end_date))
    )

    df = store.read_factor_range(fac.tb_name, _beg_date, _end_date).select(
        FIELD.ASSET,
        pl.col(FIELD.DATE).alias("insert_date"),
        pl.col(FIELD.DATETIME).alias("insert_time"),
        pl.col(FIELD.VALUE).alias(fac.name),
    )

    df = df_frame.lazy().join(df, on=["insert_date"], how="left")

    if lazy:
        return df
    return df.collect()
