import polars as pl
import polars_ds as pds

from ..context import FactorContext
from ..core import FIELD


def TS_MEAN(cb: FactorContext, date, window: int) -> pl.Expr:
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(pl.col(c).mean() for c in cb.dep_names)
    )


def TS_STD(cb: FactorContext, date, window: int) -> pl.Expr:
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(pl.col(c).std() for c in cb.dep_names)
    )


def TS_ZSCORE(cb: FactorContext, date, window: int) -> pl.Expr:
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(
            (
                (pl.col(c).sort_by(FIELD.DATETIME).last() - pl.col(c).mean())
                / pl.col(c).std()
            )
            for c in cb.dep_names
        )
    )


def TS_SHARPE(cb: FactorContext, date, window: int) -> pl.DataFrame:
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(pl.col(c).mean() / pl.col(c).std() for c in cb.dep_names)
    )


def TS_CORR(cb: FactorContext, date, window: int) -> pl.Expr:
    import warnings

    if len(cb.dep_names) > 2:
        warnings.warn(
            f"TS_CORR received {len(cb.dep_names)} dependencies, using first 2: {cb.dep_names[:2]}",
            UserWarning,
            stacklevel=2,
        )
    left, right = (
        pl.col(cb.dep_names[0]).cast(float),
        pl.col(cb.dep_names[1]).cast(float),
    )
    return (
        cb.load_window(date, window)
        .drop_nulls()
        .drop_nans()
        .filter(pl.col(FIELD.DATETIME).n_unique().over("asset") >= 5)
        .group_by("asset")
        .agg(pl.corr(left, right))
    )


def TS_MEAN_WEIGHTED(cb: FactorContext, date, window: int) -> pl.Expr:
    left, right = (
        pl.col(cb.dep_names[0]).cast(float),
        pl.col(cb.dep_names[1]).cast(float),
    )
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(value=pds.weighted_mean(var=left, weights=right.fill_null(0).abs()))
    )


def TS_RANGE(cb: FactorContext, date, window: int) -> pl.Expr:
    return (
        cb.load_window(date, window)
        .group_by("asset")
        .agg(pl.col(c).max() - pl.col(c).min() for c in cb.dep_names)
    )
