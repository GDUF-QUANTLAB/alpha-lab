import os
import random
from subprocess import PIPE, Popen


def get_cmd_list(settings: dict):
    host, port = random.choice(settings["urls"]).split(":")
    return [
        os.path.expanduser("~/./clickhouse"),
        "client",
        "--host",
        host,
        "--port",
        port,
        "--user",
        settings["user"],
        "--database",
        "cquote",
        "--password",
        settings["password"],
        "--query",
    ]


def _validate_sql_no_trailing_semicolon(sql: str) -> str:
    """
    校验 SQL 末尾不允许包含分号（;），忽略尾部空格及换行；
    返回原始 SQL（不修改内容）
    """
    s = sql.rstrip()
    if s.endswith(";"):
        raise ValueError("SQL 末尾不允许分号 ';'，请移除后再执行")
    return sql


def raw_ck_download(sql, output_file, settings: dict):
    """
    执行原始 SQL，将结果写入指定 Parquet 文件
    要求：传入的 sql 末尾不能以分号结束
    """
    _validate_sql_no_trailing_semicolon(sql)
    sql = f"""
    SELECT * FROM ({sql})
    INTO OUTFILE '{output_file}' TRUNCATE
    FORMAT Parquet
    """
    cmd_list = get_cmd_list(settings)
    cmd_list.append(sql)
    p = Popen(cmd_list, stdin=PIPE, stdout=PIPE)
    for line in p.stdout:
        _ = line.decode()
