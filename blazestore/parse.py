"""
SQL解析模块

提供SQL格式化、表名提取和临时表处理功能。
"""

from __future__ import annotations

import re

import sqlparse


def format_sql(sql_content: str) -> str:
    """
    标准化SQL语句并移除注释。

    Args:
        sql_content: 输入的SQL字符串

    Returns:
        str: 格式化后的SQL字符串

    Examples:
        >>> sql = "SELECT * FROM table -- comment"
        >>> format_sql(sql)
        'SELECT * FROM table'
        >>> sql = "SELECT  /* comment */  * FROM table"
        >>> format_sql(sql)
        'SELECT * FROM table'
    """
    parse_str = sqlparse.format(sql_content, reindent=True, strip_comments=True)
    return parse_str


def extract_temp_tables(with_clause: str) -> list[str]:
    """
    从WITH子句中提取临时表名。

    Args:
        with_clause: SQL的WITH子句字符串

    Returns:
        list[str]: 临时表名列表

    Examples:
        >>> with_clause = "WITH temp1 AS (SELECT * FROM t1), temp2 AS (SELECT * FROM t2)"
        >>> extract_temp_tables(with_clause)
        ['temp1', 'temp2']
    """
    temp_tables = re.findall(r"\b(\w+)\s*as\s*\(", with_clause, re.IGNORECASE)
    return temp_tables


def extract_table_names_from_sql(sql_query: str) -> set[str] | list[str]:
    """
    从SQL查询中提取表名。

    该函数会解析SQL语句，提取FROM和JOIN子句中的表名，
    并排除WITH子句中定义的临时表。

    Args:
        sql_query: SQL查询字符串

    Returns:
        set[str] | list[str]: 提取的表名集合或列表

    Examples:
        >>> sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        >>> extract_table_names_from_sql(sql)
        {'users', 'orders'}
        >>> sql = "WITH temp AS (SELECT * FROM t1) SELECT * FROM temp JOIN t2 ON temp.id = t2.id"
        >>> extract_table_names_from_sql(sql)
        ['t2']
    """
    table_names = set()
    parsed = sqlparse.parse(sql_query)
    table_name_pattern = r"\bFROM\s+([^\s\(\)\,]+)|\bJOIN\s+([^\s\(\)\,]+)"

    remove_with_name = []

    for statement in parsed:
        statement_str = str(statement)

        statement_str = re.sub(
            r"(substring|extract)\s*\(((.|\s)*?)\)", "", statement_str
        )

        matches = re.findall(table_name_pattern, statement_str, re.IGNORECASE)

        for match in matches:
            for name in match:
                if name:
                    table_name = name.split(".")[-1]
                    table_name = re.sub(r'("|`|\'|;)', "", table_name)
                    table_names.add(table_name)

        if "with" in statement_str:
            remove_with_name = extract_temp_tables(statement_str)

    if remove_with_name:
        table_names = list(set(table_names) - set(remove_with_name))

    return table_names
