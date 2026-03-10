import sys
import unittest
from pathlib import Path

# 将 tool-box 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from clickhouse_df import client

    HAS_CH_DRIVER = True
except Exception:
    HAS_CH_DRIVER = False


@unittest.skipIf(
    not HAS_CH_DRIVER, "缺少 clickhouse_driver 或环境不可用，跳过 client 基础测试"
)
class TestClientBasics(unittest.TestCase):
    def test_close_all_no_conn(self):
        n = client.close_all()
        self.assertEqual(n, 0)

    def test_default_conn_missing(self):
        client.close_all()
        with self.assertRaises(RuntimeError):
            client.to_pandas("SELECT 1")

    def test_connect_bad_url(self):
        with self.assertRaises(ValueError):
            client.connect(["badformat"], user="u", password="p")


if __name__ == "__main__":
    unittest.main()
