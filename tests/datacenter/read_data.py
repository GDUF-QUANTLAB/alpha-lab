import sys

sys.path.append("../../")

import datacenter as dc

df = dc.md.read_kline_day(dc.Instrument.STOCK, "2023-04-10").collect()

print(df)
