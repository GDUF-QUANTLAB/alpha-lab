from __future__ import annotations

import polars as pl

from tool_box import xcals

from . import store
from .core import FIELD, INDEX, BasicFactor


class FactorContext:
    def __init__(self, *dep_fac: BasicFactor, loader_time: str):
        self.dep_facs = dep_fac
        self.dep_names = [fac.name for fac in dep_fac]
        self.loader_time = loader_time

    def _reshape_fac_day(
        self,
        data: pl.DataFrame,
        fac: BasicFactor,
        date: str,
    ) -> pl.DataFrame:
        if data[FIELD.FIELDNAMES].n_unique() > 1:
            data = data.pivot(
                on=FIELD.FIELDNAMES, index=FIELD.ASSET, values=FIELD.VALUE
            )
        data = data.select(FIELD.ASSET, pl.col(FIELD.VALUE).alias(fac.name))
        data = data.with_columns(
            xcals.to_datetime(date, self.loader_time).alias(FIELD.DATETIME)
        )
        return data.select(*INDEX, fac.name).sort(INDEX)

    def _load_local_fac_batch(
        self,
        fac: BasicFactor,
        d_list: list[str],
    ) -> dict[str, pl.DataFrame]:
        if not d_list:
            return {}

        try:
            data = store.read_factor_range(
                fac.tb_name,
                d_list[0],
                d_list[-1],
                lazy=False,
            )
        except Exception:
            return {}

        if FIELD.DATE not in data.columns:
            return {}

        data = data.with_columns(_date_key=pl.col(FIELD.DATE).cast(pl.String)).filter(
            pl.col("_date_key").is_in(d_list)
        )

        if data.is_empty():
            return {}

        result = {}
        for d in d_list:
            day_df = data.filter(pl.col("_date_key") == d).drop(FIELD.DATE, "_date_key")
            if not day_df.is_empty():
                result[d] = day_df
        return result

    def load(
        self,
        date: str = None,
        beg_date: str = None,
        end_date: str = None,
    ) -> pl.DataFrame:
        if date is None and (beg_date is None or end_date is None):
            raise ValueError("date or beg_date and end_date must be provided")

        from .engine import get_value

        d_list = [date]
        if date is None:
            d_list = xcals.get_tradingdays(beg_date, end_date)

        big_df = None
        for fac in self.dep_facs:
            local_data = self._load_local_fac_batch(fac, d_list)
            fac_data = []
            for d in d_list:
                if d in local_data:
                    df = self._reshape_fac_day(local_data[d], fac, d)
                else:
                    df = get_value(
                        fac=fac,
                        date=d,
                        time=self.loader_time,
                        rt=False,
                        lazy=False,
                    )
                fac_data.append(df)
            fac_data = pl.concat(fac_data)
            if big_df is None:
                big_df = fac_data
            else:
                big_df = big_df.join(fac_data, on=INDEX, how="inner")

        return big_df.select(*INDEX, *self.dep_names).sort(INDEX)

    def load_window(
        self,
        date: str,
        window: int = 1,
    ) -> pl.DataFrame:
        if window <= 0:
            raise ValueError("window must be greater than 0")
        window = abs(window) - 1
        beg_date = xcals.shift_tradeday(date, -abs(window))
        end_date = date
        return self.load(beg_date=beg_date, end_date=end_date)
