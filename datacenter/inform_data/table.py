from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..enums import DataType, Instrument


# ===== Config Class =====
@dataclass
class UpdateConfig:
    sql: str | None
    remote: str | None
    local: str


DATA_CONFIG = {
    (Instrument.STOCK, DataType.SECUMAIN): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/secumain",
    ),
    (Instrument.STOCK, DataType.STATUS): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_liststatus",
    ),
    (Instrument.STOCK, DataType.ST): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_specialtrade",
    ),
    (Instrument.STOCK, DataType.SHARES): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_sharestru",
    ),
    (Instrument.STOCK, DataType.INDUSTRY): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/industry",
    ),
    (Instrument.STOCK, DataType.ADJFAC): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/adj_factor",
    ),
    (Instrument.STOCK, DataType.EX_RATING): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/c_ex_stock_rating",
    ),
    (Instrument.STOCK, DataType.IDX_COMP_W): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/components_weight",
    ),
    (Instrument.STOCK, DataType.CAPITAL): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_capital",
    ),
    (Instrument.STOCK, DataType.MAINSHLIST): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_mainshlistnew",
    ),
    (Instrument.STOCK, DataType.FINANCIAL_INDEX): UpdateConfig(
        sql=None,
        remote=None,
        local="jydata/lc_qfinancialindexnew",
    ),
}


class Data:
    def __init__(self, instrument: Instrument, datatype: DataType):
        self.instrument = instrument
        self.datatype = datatype
        self.config = DATA_CONFIG.get((instrument, datatype))
        if not self.config:
            raise ValueError(f"No config found for {instrument}, {datatype}")

    def __str__(self):
        return f"{self.instrument.value}_{self.datatype.value}"

    def __repr__(self):
        return self.__str__()

    @property
    def sql(self) -> Callable:
        return self.config.sql

    @property
    def remote(self) -> str:
        return self.config.remote

    @property
    def local(self) -> str:
        return self.config.local

    def sql_str(self, date: str) -> str:
        return self.config.sql


def get_data(instrument: Instrument, datatype: DataType) -> Data:
    return Data(instrument, datatype)
