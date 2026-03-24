"""
datacenter.config 测试
"""

import pytest

from datacenter import DATA_REGISTRY, DataConfig, DataType, Instrument, get_config


def test_data_config_creation():
    """测试 DataConfig 创建"""
    config = DataConfig(local="test/path", description="Test table")

    assert config.local == "test/path"
    assert config.remote is None
    assert config.description == "Test table"
    assert config.query_fn is None


def test_data_config_with_remote():
    """测试带 remote 的 DataConfig"""
    config = DataConfig(
        local="test/path", remote="mysql://localhost:3306/db", description="Test table"
    )

    assert config.local == "test/path"
    assert config.remote == "mysql://localhost:3306/db"


def test_get_config_stock_kline_day():
    """测试获取股票日线配置"""
    config = get_config(Instrument.STOCK, DataType.KLINE_DAY)

    assert isinstance(config, DataConfig)
    assert config.local == "mc/kline_day/stock"
    assert config.description == "股票日线数据"


def test_get_config_index_kline_day():
    """测试获取指数日线配置"""
    config = get_config(Instrument.INDEX, DataType.KLINE_DAY)

    assert isinstance(config, DataConfig)
    assert config.local == "mc/kline_day/index"
    assert config.description == "指数日线数据"


def test_get_config_stock_tick():
    """测试获取股票 Tick 配置"""
    config = get_config(Instrument.STOCK, DataType.TICK)

    assert isinstance(config, DataConfig)
    assert config.local == "mc/tick/stock"
    assert config.description == "股票快照数据"


def test_get_config_inform_data():
    """测试获取基础信息配置"""
    config = get_config(Instrument.STOCK, DataType.SECUMAIN)

    assert isinstance(config, DataConfig)
    assert config.local == "jydata/secumain"
    assert config.description == "股票基本信息"


def test_get_config_invalid():
    """测试无效配置"""
    with pytest.raises(ValueError, match="No config found"):
        get_config(Instrument.INDEX, DataType.SECUMAIN)


def test_data_registry_structure():
    """测试注册表结构"""
    assert isinstance(DATA_REGISTRY, dict)

    key = (Instrument.STOCK, DataType.KLINE_DAY)
    assert key in DATA_REGISTRY

    config = DATA_REGISTRY[key]
    assert isinstance(config, DataConfig)


def test_get_config_all_market_data():
    """测试所有市场数据配置"""
    instruments = [
        Instrument.STOCK,
        Instrument.INDEX,
        Instrument.FUTURES,
        Instrument.CONBD,
    ]
    datatypes = [DataType.KLINE_DAY, DataType.KLINE_MINUTE, DataType.TICK]

    for inst in instruments:
        for dt in datatypes:
            if dt == DataType.TICK and inst not in [
                Instrument.STOCK,
                Instrument.FUTURES,
                Instrument.CONBD,
            ]:
                continue
            config = get_config(inst, dt)
            assert isinstance(config, DataConfig)
            assert config.local.startswith("mc/")


def test_get_config_all_inform_data():
    """测试所有基础信息配置"""
    inform_datatypes = [
        DataType.SECUMAIN,
        DataType.STATUS,
        DataType.ST,
        DataType.SHARES,
        DataType.INDUSTRY,
        DataType.ADJFAC,
        DataType.EX_RATING,
        DataType.IDX_COMP_W,
        DataType.CAPITAL,
        DataType.MAINSHLIST,
        DataType.FINANCIAL_INDEX,
    ]

    for dt in inform_datatypes:
        config = get_config(Instrument.STOCK, dt)
        assert isinstance(config, DataConfig)
        assert config.local.startswith("jydata/")
