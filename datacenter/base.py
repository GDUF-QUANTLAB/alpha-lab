from __future__ import annotations

from abc import ABC, abstractmethod

import polars as pl

from .config import get_config
from .enums import DataType, Instrument


class DataAccessor(ABC):
    def __init__(self, instrument: Instrument, datatype: DataType):
        self.instrument = instrument
        self.datatype = datatype
        self.config = get_config(instrument, datatype)

    def __str__(self):
        return f"{self.instrument.value}_{self.datatype.value}"

    def __repr__(self):
        return self.__str__()

    @property
    def local(self) -> str:
        return self.config.local

    @property
    def remote(self) -> str | None:
        return self.config.remote

    @property
    def description(self) -> str:
        return self.config.description

    @abstractmethod
    def read(self, date: str | None = None) -> pl.LazyFrame:
        pass


class MarketDataAccessor(DataAccessor):
    def read(self, date: str) -> pl.LazyFrame:
        import blazestore as bs

        return bs.sql(f"select * from {self.local} where date = '{date}'")


class InformDataAccessor(DataAccessor):
    def read(self, date: str | None = None) -> pl.LazyFrame:
        import blazestore as bs

        if date:
            return bs.sql(f"select * from {self.local}").filter(
                pl.col("InfoPublDate").str.to_date() < pl.lit(date).str.to_date()
            )
        return bs.sql(f"select * from {self.local}")


def get_data(instrument: Instrument, datatype: DataType) -> DataAccessor:
    config = get_config(instrument, datatype)
    if config.local.startswith("mc/"):
        return MarketDataAccessor(instrument, datatype)
    return InformDataAccessor(instrument, datatype)
