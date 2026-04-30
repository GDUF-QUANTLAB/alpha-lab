from __future__ import annotations

import polars as pl

import blazestore as bs


def factor_date_path(tb_name: str, date: str):
    return bs.tb_path(tb_name) / f"date={date}"


def read_factor_day(tb_name: str, date: str) -> pl.DataFrame | None:
    pth = factor_date_path(tb_name, date)
    if not pth.exists():
        return None
    try:
        return pl.read_parquet(pth / "data.parquet")
    except Exception:
        import shutil

        shutil.rmtree(pth, ignore_errors=True)
        return None


def write_factor_day(tb_name: str, date: str, data: pl.DataFrame):
    return bs.put(data, f"{tb_name}/date={date}/data.parquet")


def read_factor_range(tb_name: str, beg_date: str, end_date: str, lazy: bool = True):
    return bs.sql(
        f"""
            select * from {tb_name}
            where date between '{beg_date}' and '{end_date}'
            """,
        lazy=lazy,
    )


def read_existing_dates(tb_name: str) -> list[str]:
    try:
        return (
            bs.sql(f"select * from {tb_name}")
            .group_by("date")
            .len()
            .sort("date")
            .collect()["date"]
            .cast(str)
            .to_list()
        )
    except Exception:
        return []
