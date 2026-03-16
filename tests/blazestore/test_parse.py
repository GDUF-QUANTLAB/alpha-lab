"""
BlazeStore SQL解析模块测试
"""


from blazestore import parse


def test_format_sql_removes_comments():
    """测试SQL格式化移除注释"""
    sql = "SELECT * FROM table -- comment"
    result = parse.format_sql(sql)
    assert "-- comment" not in result
    assert "SELECT" in result
    assert "FROM" in result
    assert "table" in result


def test_format_sql_removes_block_comments():
    """测试SQL格式化移除块注释"""
    sql = "SELECT /* comment */ * FROM table"
    result = parse.format_sql(sql)
    assert "/* comment */" not in result
    assert "SELECT" in result
    assert "FROM" in result
    assert "table" in result


def test_format_sql_reindents():
    """测试SQL格式化重新缩进"""
    sql = "SELECT * FROM table WHERE id=1"
    result = parse.format_sql(sql)
    assert "SELECT" in result
    assert "FROM" in result
    assert "WHERE" in result


def test_extract_temp_tables():
    """测试提取临时表名"""
    with_clause = "WITH temp1 AS (SELECT * FROM t1), temp2 AS (SELECT * FROM t2)"
    result = parse.extract_temp_tables(with_clause)
    assert result == ["temp1", "temp2"]


def test_extract_temp_tables_case_insensitive():
    """测试提取临时表名（不区分大小写）"""
    with_clause = "WITH Temp1 AS (SELECT * FROM t1), TEMP2 AS (SELECT * FROM t2)"
    result = parse.extract_temp_tables(with_clause)
    assert result == ["Temp1", "TEMP2"]


def test_extract_temp_tables_empty():
    """测试提取临时表名（空）"""
    with_clause = "SELECT * FROM table"
    result = parse.extract_temp_tables(with_clause)
    assert result == []


def test_extract_table_names_from_sql_simple():
    """测试从简单SQL中提取表名"""
    sql = "SELECT * FROM users"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result


def test_extract_table_names_from_sql_with_join():
    """测试从带JOIN的SQL中提取表名"""
    sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result
    assert "orders" in result


def test_extract_table_names_from_sql_with_schema():
    """测试从带schema的SQL中提取表名"""
    sql = "SELECT * FROM database.users"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result
    assert "database" not in result


def test_extract_table_names_from_sql_with_quotes():
    """测试从带引号的SQL中提取表名"""
    sql = 'SELECT * FROM "users" JOIN `orders` ON users.id = orders.id'
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result
    assert "orders" in result


def test_extract_table_names_from_sql_with_with_clause():
    """测试从带WITH子句的SQL中提取表名"""
    sql = "WITH temp AS (SELECT * FROM t1) SELECT * FROM temp JOIN t2 ON temp.id = t2.id"
    result = parse.extract_table_names_from_sql(sql)
    assert "t2" in result
    assert "t1" in result
    assert "temp" in result


def test_extract_table_names_from_sql_complex():
    """测试从复杂SQL中提取表名"""
    sql = """
    WITH temp1 AS (SELECT * FROM t1),
         temp2 AS (SELECT * FROM t2)
    SELECT * FROM temp1
    JOIN t3 ON temp1.id = t3.id
    JOIN t4 ON temp1.id = t4.id
    """
    result = parse.extract_table_names_from_sql(sql)
    assert "t3" in result
    assert "t4" in result
    assert "temp1" in result
    assert "t1" in result
    assert "t2" in result


def test_extract_table_names_from_sql_with_substring():
    """测试从带SUBSTRING函数的SQL中提取表名"""
    sql = "SELECT SUBSTRING(name, 1, 10) FROM users"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result


def test_extract_table_names_from_sql_with_extract():
    """测试从带EXTRACT函数的SQL中提取表名"""
    sql = "SELECT EXTRACT(YEAR FROM date) FROM users"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result


def test_extract_table_names_from_sql_multiple_statements():
    """测试从多语句SQL中提取表名"""
    sql = "SELECT * FROM users; SELECT * FROM orders"
    result = parse.extract_table_names_from_sql(sql)
    assert "users" in result
    assert "orders" in result


def test_extract_table_names_from_sql_returns_set():
    """测试返回类型为set"""
    sql = "SELECT * FROM users"
    result = parse.extract_table_names_from_sql(sql)
    assert isinstance(result, set)


def test_extract_table_names_from_sql_with_with_returns_list():
    """测试带WITH子句时返回类型为list"""
    sql = "WITH temp AS (SELECT * FROM t1) SELECT * FROM temp JOIN t2 ON temp.id = t2.id"
    result = parse.extract_table_names_from_sql(sql)
    assert isinstance(result, (set, list))
