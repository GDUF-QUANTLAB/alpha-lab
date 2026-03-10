from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..enums import DataType, Instrument


# ===== Config Class =====
@dataclass
class UpdateConfig:
    query_fn: Callable | None
    remote: str | None
    local: str


# ===== Configuration Map =====
DATA_CONFIG = {
    # DAY
    (Instrument.STOCK, DataType.KLINE_DAY): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_day/stock",
    ),
    (Instrument.INDEX, DataType.KLINE_DAY): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_day/index",
    ),
    (Instrument.FUTURES, DataType.KLINE_DAY): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_day/futures",
    ),
    (Instrument.CONBD, DataType.KLINE_DAY): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_day/conbd",
    ),
    # MINUTE
    (Instrument.STOCK, DataType.KLINE_MINUTE): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_minute/stock",
    ),
    (Instrument.INDEX, DataType.KLINE_MINUTE): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_minute/index",
    ),
    (Instrument.FUTURES, DataType.KLINE_MINUTE): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_minute/futures",
    ),
    (Instrument.CONBD, DataType.KLINE_MINUTE): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/kline_minute/conbd",
    ),
    # TICK
    (Instrument.STOCK, DataType.TICK): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/tick/stock",
    ),
    (Instrument.FUTURES, DataType.TICK): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/tick/futures",
    ),
    (Instrument.CONBD, DataType.TICK): UpdateConfig(
        query_fn=None,
        remote=None,
        local="mc/tick/conbd",
    ),
}


# ===== Data Class =====
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
        return self.config.query_fn

    @property
    def remote(self) -> str:
        return self.config.remote

    @property
    def local(self) -> str:
        return self.config.local

    def sql_str(self, date: str) -> str:
        return self.config.query_fn(date, self.remote)


def get_data(instrument: Instrument, datatype: DataType) -> Data:
    return Data(instrument, datatype)
