from __future__ import annotations

import polars as pl

import xcals

from .constants import FIELD, INDEX


class Cubase:
    """
    因子批量加载器，存储因子及其查询配置。

    使用列表存储依赖，每个依赖是一个字典：
    [{"factor": BasicFactor, "lag": 1, ...}, ...]

    Example:
        cubase = Cubase([
            {"factor": dep_a, "lag": 1},
            {"factor": dep_b, "lag": 2}
        ])
    """

    def __init__(self, deps: list[dict]):
        self.deps = deps

    @property
    def factors(self) -> list:
        return [d["factor"] for d in self.deps]

    @property
    def dep_names(self) -> list[str]:
        return [d["factor"].name for d in self.deps]

    def get_lag(self, idx: int) -> int:
        return self.deps[idx].get("lag", 0)

    def get_config(self, idx: int) -> dict:
        return self.deps[idx]

    def _reshape_fac_day(
        self,
        data: pl.DataFrame,
        fac,
        target_date: str,
        loader_time: str,
    ) -> pl.DataFrame:
        if data[FIELD.FIELDNAMES].n_unique() > 1:
            data = data.pivot(
                on=FIELD.FIELDNAMES, index=FIELD.ASSET, values=FIELD.VALUE
            )
        data = data.select(FIELD.ASSET, pl.col(FIELD.VALUE).alias(fac.name))
        data = data.with_columns(
            xcals.to_datetime(target_date, loader_time).alias(FIELD.DATETIME)
        )
        return data.select(*INDEX, fac.name).sort(INDEX)

    def _load_local_fac_batch(
        self,
        fac,
        d_list: list[str],
    ) -> dict[str, pl.DataFrame]:
        if not d_list:
            return {}

        from factor import store

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
        loader_time: str = "15:00:00",
    ) -> pl.DataFrame:
        if date is None and (beg_date is None or end_date is None):
            raise ValueError("date or beg_date and end_date must be provided")

        from factor.engine import get_value

        d_list = [date]
        if date is None:
            d_list = xcals.get_tradingdays(beg_date, end_date)

        if not self.factors:
            return pl.DataFrame()

        big_df = None
        for idx, fac in enumerate(self.factors):
            lag = self.get_lag(idx)
            source_d_list = (
                [xcals.shift_tradeday(d, -lag) for d in d_list] if lag > 0 else d_list
            )

            local_data = self._load_local_fac_batch(fac, source_d_list)
            fac_data = []
            for target_d, source_d in zip(d_list, source_d_list, strict=True):
                if source_d in local_data:
                    df = self._reshape_fac_day(
                        local_data[source_d],
                        fac,
                        target_d,
                        loader_time,
                    )
                else:
                    df = get_value(
                        fac=fac,
                        date=source_d,
                        time=loader_time,
                        rt=False,
                        lazy=False,
                    )
                    df = df.with_columns(
                        xcals.to_datetime(target_d, loader_time).alias(FIELD.DATETIME)
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
        loader_time: str = "15:00:00",
    ) -> pl.DataFrame:
        if window <= 0:
            raise ValueError("window must be greater than 0")
        window = abs(window) - 1
        beg_date = xcals.shift_tradeday(date, -abs(window))
        end_date = date
        return self.load(beg_date=beg_date, end_date=end_date, loader_time=loader_time)

    def __iter__(self):
        return iter(self.deps)

    def __len__(self):
        return len(self.deps)