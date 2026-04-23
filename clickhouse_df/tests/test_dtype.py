import sys
import unittest
from pathlib import Path

import pyarrow as pa

# 将 tool-box 加入 sys.path，便于作为包导入 clickhouse_df
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from clickhouse_df import dtype


class TestClickhouseDtypeMapping(unittest.TestCase):
    def test_datetime64_precision(self):
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("DateTime64(3)"), pa.timestamp("ms")
        )
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("DateTime64(6)"), pa.timestamp("us")
        )
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("DateTime64(9)"), pa.timestamp("ns")
        )
        # with timezone hint should ignore and map by precision
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("DateTime64(3, 'UTC')"), pa.timestamp("ms")
        )

    def test_decimal256_mapping(self):
        t1 = dtype.map_clickhouse_decimal("Decimal256(42, 10)")
        self.assertEqual(t1, pa.decimal256(42, 10))
        t2 = dtype.map_clickhouse_decimal("Decimal256(39)")
        self.assertEqual(t2, pa.decimal256(39, 0))
        t3 = dtype.map_clickhouse_decimal("Decimal128(38, 0)")
        self.assertEqual(t3, pa.decimal128(38, 0))

    def test_lowcardinality(self):
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("LowCardinality(String)"), pa.string()
        )
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("LowCardinality(UInt32)"), pa.uint32()
        )

    def test_nullable_and_array(self):
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("Nullable(DateTime64(3))"), pa.timestamp("ms")
        )
        self.assertEqual(
            dtype.map_clickhouse_to_arrow("Array(Nullable(Int32))"),
            pa.list_(pa.int32()),
        )


if __name__ == "__main__":
    unittest.main()
