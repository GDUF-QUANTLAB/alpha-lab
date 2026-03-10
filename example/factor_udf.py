import sys

sys.path.append("../../")

import polars as pl

import datacenter as dc
from tool_box import xcals


# ================ 因子计算 ================
def get_nd_volatility(date, n=10):
    """
    获取 n 天内的波动率
    """
    beg_date, end_date = (
        xcals.shift_tradeday(date, -abs(n - 1)),
        date,
    )  # 注意这里用n-1,确保是20天
    kline_day = dc.md.read_data_batch(
        beg_date, end_date, dc.Instrument.STOCK, dc.DataType.KLINE_DAY
    )

    return (
        kline_day.group_by("asset")
        .agg((pl.col("close") / pl.col("prev_close")).std())
        .sort("asset")
        .collect()
    )


print(get_nd_volatility("2023-04-10"))
