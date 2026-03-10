from __future__ import annotations

import re
import urllib
from pathlib import Path

import polars as pl

from tool_box import clickhouse_df

from .config import get_settings
from .parse import extract_table_names_from_sql

DB_PATH = get_settings().get("paths.store")


# ======================== Local Database (catdb) ========================
def tb_path(tb_name: str) -> Path:
    """
    Returns the complete local path for a given table name.

    Args:
        tb_name: Table name, path style: a/b/c

    Returns:
        pathlib.Path: Complete local absolute path $DB_PATH/a/b/c
    """
    return Path(DB_PATH, tb_name)


def put(
    df: pl.DataFrame,
    tb_name: str,
    partitions: list[str] | None = None,
    abs_path: bool = False,
):
    """
    Writes a DataFrame to the specified table directory, supporting partitioned storage.

    This function writes the given DataFrame (df) to the local file system based on the
    provided table name (tb_name). If partitions are specified, data will be split and
    stored according to these partition columns. Additionally, the abs_path parameter
    can specify whether tb_name should be treated as an absolute path. If the directory
    does not exist, it will be created automatically.

    Args:
        df: The DataFrame to write.
        tb_name: The name of the table, used to determine the storage directory.
        partitions: List of column names to use for partitioning. If not provided,
            no partitioning is performed.
        abs_path: Whether tb_name should be treated as an absolute path. Defaults to False.
    """
    if not abs_path:
        tbpath = tb_path(tb_name)
    else:
        tbpath = Path(tb_name)
    if not tbpath.exists():
        tbpath.mkdir(parents=True, exist_ok=True)
    if partitions is not None:
        df.write_parquet(tbpath, partition_by=partitions)
    else:
        df.write_parquet(tbpath / "data.parquet")


def has(tb_name: str) -> bool:
    """
    Determines if the given table name exists.

    Args:
        tb_name: The table name to check.

    Returns:
        bool: True if the table exists, False otherwise.
    """
    return tb_path(tb_name).exists()


def sql(
    query: str, abs_path: bool = False, lazy: bool = True
) -> pl.DataFrame | pl.LazyFrame:
    """
    Executes a SQL query against local Parquet files.

    Args:
        query: The SQL query string.
        abs_path: Whether to use absolute paths for table paths. Defaults to False.
        lazy: Whether to return a LazyFrame (True) or DataFrame (False). Defaults to True.

    Returns:
        pl.DataFrame | pl.LazyFrame: The query result.
    """
    tbs = extract_table_names_from_sql(query)
    convertor = {}
    for tb in tbs:
        if not abs_path:
            db_path = tb_path(tb)
        else:
            db_path = tb
        format_tb = f"read_parquet('{db_path}/**/*.parquet')"
        convertor[tb] = format_tb
    pattern = re.compile("|".join(re.escape(k) for k in convertor.keys()))
    new_query = pattern.sub(lambda m: convertor[m.group(0)], query)
    if not lazy:
        return pl.sql(new_query).collect()
    return pl.sql(new_query)


def read_mysql(query: str, db_conf: str = "databases.mysql") -> pl.DataFrame:
    """
    Reads data from a MySQL database.

    Args:
        query: The SQL query to execute.
        db_conf: The configuration key in settings (e.g., "databases.mysql").

    Returns:
        pl.DataFrame: The result of the query.

    Raises:
        RuntimeError: If database configuration is missing or query execution fails.
    """
    try:
        db_setting = get_settings().get(db_conf, {})
        required_keys = ["user", "password", "url"]
        missing_keys = [key for key in required_keys if key not in db_setting]
        if missing_keys:
            raise KeyError(f"Missing required keys in database config: {missing_keys}")

        user = urllib.parse.quote_plus(db_setting["user"])
        password = urllib.parse.quote_plus(db_setting["password"])
        uri = f"mysql://{user}:{password}@{db_setting['url']}"
        return pl.read_database_uri(query, uri)

    except KeyError as e:
        raise RuntimeError(
            "Database configuration error: missing required fields."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to execute MySQL query: {e}") from e


def write_mysql(df: pl.DataFrame, tb_name: str, db_conf: str = "databases.mysql"):
    """
    Writes a DataFrame to a MySQL database.

    Args:
        df: The DataFrame to write.
        tb_name: The name of the target table.
        db_conf: The configuration key in settings (e.g., "databases.mysql").

    Raises:
        RuntimeError: If database configuration is missing.
    """
    db_setting = get_settings().get(db_conf, {})
    required_keys = ["user", "password", "url"]
    missing_keys = [key for key in required_keys if key not in db_setting]
    if missing_keys:
        raise KeyError(f"Missing required keys in database config: {missing_keys}")

    user = urllib.parse.quote_plus(db_setting["user"])
    password = urllib.parse.quote_plus(db_setting["password"])
    uri = f"mysql+pymysql://{user}:{password}@{db_setting['url']}"
    df.write_database(
        table_name=f"{db_setting.get('database')}.{tb_name}",
        connection=uri,
        if_table_exists="append",
    )


def read_ck(query: str, db_conf: str = "databases.ck") -> pl.DataFrame:
    """
    Reads data from a ClickHouse cluster.

    Args:
        query: The SQL query to execute.
        db_conf: The configuration key in settings (e.g., "databases.ck").

    Returns:
        pl.DataFrame: The result of the query.

    Raises:
        RuntimeError: If database configuration is missing or query execution fails.
    """
    try:
        db_setting = get_settings().get(db_conf, {})
        required_keys = ["user", "password", "urls"]
        missing_keys = [key for key in required_keys if key not in db_setting]
        if missing_keys:
            raise KeyError(f"Missing required keys in database config: {missing_keys}")

        user = urllib.parse.quote_plus(db_setting["user"])
        password = urllib.parse.quote_plus(db_setting["password"])

        with clickhouse_df.connect(db_setting["urls"], user=user, password=password):
            return clickhouse_df.to_polars(query)

    except KeyError as e:
        raise RuntimeError(
            "Database configuration error: missing required fields."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to execute ClickHouse query: {e}") from e
