from __future__ import annotations

import re

import sqlparse


def format_sql(sql_content: str) -> str:
    """
    Normalizes SQL statements and removes comments.

    Args:
        sql_content: The input SQL string.

    Returns:
        str: The formatted SQL string.
    """
    parse_str = sqlparse.format(sql_content, reindent=True, strip_comments=True)
    return parse_str


def extract_temp_tables(with_clause: str) -> list[str]:
    """
    Extracts temporary table names from a WITH clause.

    Args:
        with_clause: The SQL WITH clause string.

    Returns:
        list[str]: A list of temporary table names.
    """
    temp_tables = re.findall(r"\b(\w+)\s*as\s*\(", with_clause, re.IGNORECASE)
    return temp_tables


def extract_table_names_from_sql(sql_query: str) -> set[str] | list[str]:
    """
    Extracts table names from a SQL query.

    Args:
        sql_query: The SQL query string.

    Returns:
        set[str] | list[str]: A collection of extracted table names.
    """
    table_names = set()
    # Parse SQL statement
    parsed = sqlparse.parse(sql_query)
    # Regex pattern to match table names
    table_name_pattern = r"\bFROM\s+([^\s\(\)\,]+)|\bJOIN\s+([^\s\(\)\,]+)"

    # Store temporary table names from WITH clause
    remove_with_name = []

    # Iterate through parsed statements
    for statement in parsed:
        # Convert to string
        statement_str = str(statement)  # .lower()

        # Remove special syntax
        statement_str = re.sub(
            r"(substring|extract)\s*\(((.|\s)*?)\)", "", statement_str
        )

        # Find matching table names
        matches = re.findall(table_name_pattern, statement_str, re.IGNORECASE)

        for match in matches:
            # Extract non-empty table name parts
            for name in match:
                if name:
                    # Keep only the last part for names with namespaces
                    table_name = name.split(".")[-1]
                    # Remove special characters from table name
                    table_name = re.sub(r'("|`|\'|;)', "", table_name)
                    table_names.add(table_name)

        # Handle special WITH clauses
        if "with" in statement_str:
            remove_with_name = extract_temp_tables(statement_str)
    # Remove temporary table names
    if remove_with_name:
        table_names = list(set(table_names) - set(remove_with_name))

    return table_names
