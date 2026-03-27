from __future__ import annotations

from enum import Enum


# ===== Enums =====
class Instrument(Enum):
    STOCK = "stock"
    INDEX = "index"
    FUTURES = "futures"
    CONBD = "convertible_bonds"


class DataType(Enum):
    TICK = "tick"
    KLINE_DAY = "kline_day"
    KLINE_MINUTE = "kline_minute"
    ST = "specialtrade"
    SECUMAIN = "secumain"
    STATUS = "status"
    SHARES = "shares"
    INDUSTRY = "industry"
    ADJFAC = "adj_factor"
    IDX_COMP_W = "index_component_weight"
    CAPITAL = "capital"
    ACCOUNTING = "accounting"
