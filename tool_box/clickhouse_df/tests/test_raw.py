import sys
import unittest
from pathlib import Path

# 将 tool-box 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from clickhouse_df import raw


class TestRawSqlValidation(unittest.TestCase):
    def test_semicolon_rejected(self):
        bad_sql = "SELECT 1;"
        with self.assertRaises(ValueError):
            raw._validate_sql_no_trailing_semicolon(bad_sql)
        # 尾部分号后还有空格/换行也应被拒绝
        bad_sql_with_space = "SELECT 1;   \n"
        with self.assertRaises(ValueError):
            raw._validate_sql_no_trailing_semicolon(bad_sql_with_space)

    def test_no_semicolon_ok(self):
        ok_sql = "SELECT 1"
        self.assertEqual(raw._validate_sql_no_trailing_semicolon(ok_sql), ok_sql)
        ok_sql_with_space = "SELECT 1   "
        self.assertEqual(
            raw._validate_sql_no_trailing_semicolon(ok_sql_with_space),
            ok_sql_with_space,
        )


if __name__ == "__main__":
    unittest.main()
