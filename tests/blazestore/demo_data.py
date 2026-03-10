import sys

sys.path.append("../../")

import datacenter as dc

test_date = "2023-04-10"
beg_date = "2023-04-01"
end_date = "2023-04-10"


def test_read_kline_day():
    data = dc.md.read_kline_day(test_date, dc.Instrument.STOCK).head().collect()
    assert data.shape[0] > 0


def test_read_kline_minute():
    data = dc.md.read_kline_minute(test_date, dc.Instrument.STOCK).head().collect()
    assert data.shape[0] > 0


def test_read_kline_batch():
    data = (
        dc.md.read_data_batch(
            beg_date, end_date, dc.Instrument.STOCK, dc.DataType.KLINE_DAY
        )
        .head()
        .collect()
    )
    assert data.shape[0] > 0
