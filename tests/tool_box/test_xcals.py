import datetime

import pytest

from xcals import api


def test_today():
    today_str = api.today()
    assert isinstance(today_str, str)
    assert len(today_str) == 10

    today_obj = api.today(as_obj=True)
    assert isinstance(today_obj, datetime.date)
    assert str(today_obj) == today_str


def test_now():
    now_str = api.now()
    assert isinstance(now_str, str)
    assert len(now_str) == 19

    now_obj = api.now(as_obj=True)
    assert isinstance(now_obj, datetime.datetime)


def test_is_tradeday():
    # 假设 2023-01-01 是元旦假期，不是交易日
    # 假设 2023-01-03 是交易日
    # 需要确保测试环境有数据。目前 blazestore 应该已经有了数据。
    # 由于我们无法预知具体数据内容，这里测试逻辑需要健壮一点。

    # 找一个肯定存在的交易日
    trading_days = api.get_tradingdays(beg_date="2023-01-01", end_date="2023-01-31")
    if not trading_days:
        pytest.skip("No trading days found in 2023-01, check data file.")

    valid_day = trading_days[0]
    assert api.is_tradeday(valid_day) is True

    # 找一个肯定不存在的日期 (周末)
    # 2023-01-01 是周日
    assert api.is_tradeday("2023-01-01") is False


def test_shift_tradeday():
    # 测试偏移
    # 2023-01-03 (二) -> 2023-01-04 (三)
    # 假设这两个都是交易日
    days = api.get_tradingdays(beg_date="2023-01-01", end_date="2023-01-10")
    if len(days) < 3:
        pytest.skip("Not enough trading days to test shift.")

    d0 = days[0]
    d1 = days[1]
    d2 = days[2]

    assert api.shift_tradeday(d0, 1) == d1
    assert api.shift_tradeday(d1, 1) == d2
    assert api.shift_tradeday(d2, -1) == d1
    assert api.shift_tradeday(d0, 0) == d0


def test_get_tradingdays():
    days = api.get_tradingdays(beg_date="2023-01-01", end_date="2023-01-10")
    assert isinstance(days, list)
    assert all(isinstance(d, str) for d in days)

    days_obj = api.get_tradingdays(
        beg_date="2023-01-01", end_date="2023-01-10", to_str=False
    )
    assert isinstance(days_obj, list)
    assert all(isinstance(d, datetime.date) for d in days_obj)
