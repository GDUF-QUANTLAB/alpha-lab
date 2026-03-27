"""
datacenter.enums 测试
"""

from datacenter import DataType, Instrument


def test_instrument_enum():
    """测试 Instrument 枚举"""
    assert Instrument.STOCK.value == "stock"
    assert Instrument.INDEX.value == "index"
    assert Instrument.FUTURES.value == "futures"
    assert Instrument.CONBD.value == "convertible_bonds"


def test_datatype_enum():
    """测试 DataType 枚举"""
    assert DataType.TICK.value == "tick"
    assert DataType.KLINE_DAY.value == "kline_day"
    assert DataType.KLINE_MINUTE.value == "kline_minute"
    assert DataType.SECUMAIN.value == "secumain"
    assert DataType.STATUS.value == "status"
    assert DataType.SHARES.value == "shares"
    assert DataType.INDUSTRY.value == "industry"
    assert DataType.ADJFAC.value == "adj_factor"
    assert DataType.IDX_COMP_W.value == "index_component_weight"
    assert DataType.CAPITAL.value == "capital"
    assert DataType.ACCOUNTING.value == "accounting"


def test_enum_comparison():
    """测试枚举比较"""
    assert Instrument.STOCK == Instrument.STOCK
    assert Instrument.STOCK != Instrument.INDEX
    assert DataType.KLINE_DAY == DataType.KLINE_DAY
    assert DataType.KLINE_DAY != DataType.KLINE_MINUTE


def test_enum_iteration():
    """测试枚举遍历"""
    instruments = list(Instrument)
    assert len(instruments) == 4
    assert Instrument.STOCK in instruments

    datatypes = list(DataType)
    assert len(datatypes) == 12
    assert DataType.KLINE_DAY in datatypes
