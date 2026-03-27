from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .enums import DataType, Instrument


@dataclass
class DataConfig:
    local: str
    remote: str | None = None
    query_fn: Callable | None = None
    description: str = ""


DATA_REGISTRY = {
    # Market Data - KLINE_DAY
    (Instrument.STOCK, DataType.KLINE_DAY): DataConfig(
        local="mc/kline_day/stock",
        description="股票日线数据",
    ),
    (Instrument.INDEX, DataType.KLINE_DAY): DataConfig(
        local="mc/kline_day/index",
        description="指数日线数据",
    ),
    (Instrument.FUTURES, DataType.KLINE_DAY): DataConfig(
        local="mc/kline_day/futures",
        description="期货日线数据",
    ),
    (Instrument.CONBD, DataType.KLINE_DAY): DataConfig(
        local="mc/kline_day/conbd",
        description="可转债日线数据",
    ),
    # Market Data - KLINE_MINUTE
    (Instrument.STOCK, DataType.KLINE_MINUTE): DataConfig(
        local="mc/kline_minute/stock",
        description="股票分钟线数据",
    ),
    (Instrument.INDEX, DataType.KLINE_MINUTE): DataConfig(
        local="mc/kline_minute/index",
        description="指数分钟线数据",
    ),
    (Instrument.FUTURES, DataType.KLINE_MINUTE): DataConfig(
        local="mc/kline_minute/futures",
        description="期货分钟线数据",
    ),
    (Instrument.CONBD, DataType.KLINE_MINUTE): DataConfig(
        local="mc/kline_minute/conbd",
        description="可转债分钟线数据",
    ),
    # Market Data - TICK
    (Instrument.STOCK, DataType.TICK): DataConfig(
        local="mc/tick/stock",
        description="股票快照数据",
    ),
    (Instrument.FUTURES, DataType.TICK): DataConfig(
        local="mc/tick/futures",
        description="期货快照数据",
    ),
    (Instrument.CONBD, DataType.TICK): DataConfig(
        local="mc/tick/conbd",
        description="可转债快照数据",
    ),
    # Inform Data - SECUMAIN
    (Instrument.STOCK, DataType.SECUMAIN): DataConfig(
        local="jydata/secumain",
        description="股票基本信息",
    ),
    # Inform Data - STATUS
    (Instrument.STOCK, DataType.STATUS): DataConfig(
        local="jydata/lc_liststatus",
        description="股票状态信息",
    ),
    # Inform Data - ST
    (Instrument.STOCK, DataType.ST): DataConfig(
        local="jydata/lc_specialtrade",
        description="股票特殊交易信息",
    ),
    # Inform Data - SHARES
    (Instrument.STOCK, DataType.SHARES): DataConfig(
        local="jydata/lc_sharestru",
        description="股票股本结构",
    ),
    # Inform Data - INDUSTRY
    (Instrument.STOCK, DataType.INDUSTRY): DataConfig(
        local="jydata/industry",
        description="股票行业分类",
    ),
    # Inform Data - ADJFAC
    (Instrument.STOCK, DataType.ADJFAC): DataConfig(
        local="jydata/adj_factor",
        description="股票复权因子",
    ),
    # Inform Data - IDX_COMP_W
    (Instrument.STOCK, DataType.IDX_COMP_W): DataConfig(
        local="jydata/components_weight",
        description="指数成分股权重",
    ),
    # Inform Data - CAPITAL
    (Instrument.STOCK, DataType.CAPITAL): DataConfig(
        local="jydata/lc_capital",
        description="股票资本结构",
    ),
    # Inform Data - MAIN_ACCOUNT
    (Instrument.STOCK, DataType.ACCOUNTING): DataConfig(
        local="jydata/lc_maindatanew",
        description="报告期主要会计数据",
    ),
}


def get_config(instrument: Instrument, datatype: DataType) -> DataConfig:
    config = DATA_REGISTRY.get((instrument, datatype))
    if not config:
        raise ValueError(f"No config found for {instrument}, {datatype}")
    return config
