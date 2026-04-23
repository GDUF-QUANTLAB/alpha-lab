import functools
import re
from typing import Any

import pyarrow as pa
from polars._typing import PolarsDataType
from polars.datatypes import (
    Binary,
    Boolean,
    Date,
    Datetime,
    Decimal,
    Duration,
    Float32,
    Float64,
    Int8,
    Int16,
    Int32,
    Int64,
    List,
    Null,
    String,
    Time,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
)


@functools.lru_cache(8)
def integer_dtype_from_nbits(
    bits: int,
    *,
    unsigned: bool,
    default: PolarsDataType | None = None,
) -> PolarsDataType | None:
    """
    Return matching Polars integer dtype from num bits and signed/unsigned flag.

    Examples
    --------
    >>> integer_dtype_from_nbits(8, unsigned=False)
    Int8
    >>> integer_dtype_from_nbits(32, unsigned=True)
    UInt32
    """
    dtype = {
        (8, False): Int8,
        (8, True): UInt8,
        (16, False): Int16,
        (16, True): UInt16,
        (32, False): Int32,
        (32, True): UInt32,
        (64, False): Int64,
        (64, True): UInt64,
    }.get((bits, unsigned), None)

    if dtype is None and default is not None:
        return default
    return dtype


def timeunit_from_precision(precision: int | str | None) -> str | None:
    """
    Return `time_unit` from integer precision value.

    Examples
    --------
    >>> timeunit_from_precision(3)
    'ms'
    >>> timeunit_from_precision(5)
    'us'
    >>> timeunit_from_precision(7)
    'ns'
    """
    from math import ceil

    if not precision:
        return None
    elif isinstance(precision, str):
        if precision.isdigit():
            precision = int(precision)
        elif (precision := precision.lower()) in ("s", "ms", "us", "ns"):
            return "ms" if precision == "s" else precision
    try:
        n = min(max(3, int(ceil(precision / 3)) * 3), 9)  # type: ignore[operator]
        return {3: "ms", 6: "us", 9: "ns"}.get(n)
    except TypeError:
        return None


def infer_dtype_from_database_typename(
    value: str,
    *,
    raise_unmatched: bool = True,
) -> PolarsDataType | None:
    """
    Attempt to infer Polars dtype from database cursor `type_code` string value.

    Examples
    --------
    >>> infer_dtype_from_database_typename("INT2")
    Int16
    >>> infer_dtype_from_database_typename("NVARCHAR")
    String
    >>> infer_dtype_from_database_typename("NUMERIC(10,2)")
    Decimal(precision=10, scale=2)
    >>> infer_dtype_from_database_typename("TIMESTAMP WITHOUT TZ")
    Datetime(time_unit='us', time_zone=None)
    """
    dtype: PolarsDataType | None = None

    # normalise string name/case (eg: 'IntegerType' -> 'INTEGER')
    original_value = value
    value = value.upper().replace("TYPE", "")

    # extract optional type modifier (eg: 'VARCHAR(64)' -> '64')
    if re.search(r"\([\w,: ]+\)$", value):
        modifier = value[value.find("(") + 1 : -1]
        value = value.split("(")[0]
        # Nullable type
        if value.upper() == "NULLABLE":
            return infer_dtype_from_database_typename(modifier)
    elif (
        not value.startswith(("<", ">")) and re.search(r"\[[\w,\]\[: ]+]$", value)
    ) or value.endswith(("[S]", "[MS]", "[US]", "[NS]")):
        modifier = value[value.find("[") + 1 : -1]
        value = value.split("[")[0]
    else:
        modifier = ""

    # array dtypes
    array_aliases = ("ARRAY", "LIST", "[]")
    if value.endswith(array_aliases) or value.startswith(array_aliases):
        for a in array_aliases:
            value = value.replace(a, "", 1) if value else ""

        nested: PolarsDataType | None = None
        if not value and modifier:
            nested = infer_dtype_from_database_typename(
                value=modifier,
                raise_unmatched=False,
            )
        else:
            if inner_value := infer_dtype_from_database_typename(
                value[1:-1]
                if (value[0], value[-1]) == ("<", ">")
                else re.sub(r"\W", "", re.sub(r"\WOF\W", "", value)),
                raise_unmatched=False,
            ):
                nested = inner_value
            elif modifier:
                nested = infer_dtype_from_database_typename(
                    value=modifier,
                    raise_unmatched=False,
                )
        if nested:
            dtype = List(nested)

    # float dtypes
    elif value.startswith("FLOAT") or ("DOUBLE" in value) or (value == "REAL"):
        dtype = (
            Float32
            if value == "FLOAT4"
            or (value.endswith(("16", "32")) or (modifier in ("16", "32")))
            else Float64
        )

    # integer dtypes
    elif ("INTERVAL" not in value) and (
        value.startswith(("INT", "UINT", "UNSIGNED"))
        or value.endswith(("INT", "SERIAL"))
        or ("INTEGER" in value)
        or value == "ROWID"
    ):
        sz: Any
        if "LARGE" in value or value.startswith("BIG") or value == "INT8":
            sz = 64
        elif "MEDIUM" in value or value in ("INT4", "SERIAL"):
            sz = 32
        elif "SMALL" in value or value == "INT2":
            sz = 16
        elif "TINY" in value:
            sz = 8
        else:
            sz = None

        sz = modifier if (not sz and modifier) else sz
        if not isinstance(sz, int):
            sz = int(sz) if isinstance(sz, str) and sz.isdigit() else None
        if (
            ("U" in value and "MEDIUM" not in value)
            or ("UNSIGNED" in value)
            or value == "ROWID"
        ):
            dtype = integer_dtype_from_nbits(sz, unsigned=True, default=UInt64)
        else:
            dtype = integer_dtype_from_nbits(sz, unsigned=False, default=Int64)

    # number types (note: 'number' alone is not that helpful and requires refinement)
    elif "NUMBER" in value and "CARDINAL" in value:
        dtype = UInt64

    # decimal dtypes
    elif (is_dec := ("DECIMAL" in value)) or ("NUMERIC" in value):
        if "," in modifier:
            prec, scale = modifier.split(",")
            dtype = Decimal(int(prec), int(scale))
        else:
            dtype = Decimal if is_dec else Float64

    # string dtypes
    elif (
        any(tp in value for tp in ("VARCHAR", "STRING", "TEXT", "UNICODE"))
        or value.startswith(("STR", "CHAR", "BPCHAR", "NCHAR", "UTF"))
        or value.endswith(("_UTF8", "_UTF16", "_UTF32"))
    ):
        dtype = String

    # binary dtypes
    elif value in ("BYTEA", "BYTES", "BLOB", "CLOB", "BINARY"):
        dtype = Binary

    # boolean dtypes
    elif value.startswith("BOOL"):
        dtype = Boolean

    # null dtype; odd, but valid
    elif value == "NULL":
        dtype = Null

    # temporal dtypes
    elif value.startswith(("DATETIME", "TIMESTAMP")) and not (value.endswith("[D]")):
        if any((tz in value.replace(" ", "")) for tz in ("TZ", "TIMEZONE")):
            if "WITHOUT" not in value:
                return None  # there's a timezone, but we don't know what it is
        unit = timeunit_from_precision(modifier) if modifier else "us"
        dtype = Datetime(time_unit=(unit or "us"))  # type: ignore[arg-type]
    else:
        value = re.sub(r"\d", "", value)
        if value in ("INTERVAL", "TIMEDELTA", "DURATION"):
            dtype = Duration
        elif value == "DATE":
            dtype = Date
        elif value == "TIME":
            dtype = Time

    if not dtype and raise_unmatched:
        msg = f"cannot infer dtype from {original_value!r} string value"
        raise ValueError(msg)

    return dtype


CLICKHOUSE_TO_ARROW_TYPE = {
    # 整数类型
    "Int8": pa.int8(),
    "Int16": pa.int16(),
    "Int32": pa.int32(),
    "Int64": pa.int64(),
    "UInt8": pa.uint8(),
    "UInt16": pa.uint16(),
    "UInt32": pa.uint32(),
    "UInt64": pa.uint64(),
    # 浮点类型
    "Float32": pa.float32(),
    "Float64": pa.float64(),
    # 字符串类型
    "String": pa.string(),
    "FixedString": pa.string(),  # Arrow 不区分固定长度和动态长度字符串
    # 日期和时间类型
    "Date": pa.date32(),  # ClickHouse 的 Date 是 32 位（天）
    "Date32": pa.date32(),
    "DateTime": pa.timestamp("s"),  # ClickHouse DateTime 精度为秒
    "DateTime64": pa.timestamp("ms"),  # 无精度参数时默认毫秒
    "UUID": pa.binary(16),  # UUID 是 16 字节的二进制
    # 布尔类型
    "Boolean": pa.bool_(),
    # 数组类型（嵌套类型）
    "Array(Int8)": pa.list_(pa.int8()),
    "Array(Int16)": pa.list_(pa.int16()),
    "Array(Int32)": pa.list_(pa.int32()),
    "Array(Int64)": pa.list_(pa.int64()),
    "Array(UInt8)": pa.list_(pa.uint8()),
    "Array(UInt16)": pa.list_(pa.uint16()),
    "Array(UInt32)": pa.list_(pa.uint32()),
    "Array(UInt64)": pa.list_(pa.uint64()),
    "Array(Float32)": pa.list_(pa.float32()),
    "Array(Float64)": pa.list_(pa.float64()),
    "Array(String)": pa.list_(pa.string()),
    "Array(Date)": pa.list_(pa.date32()),
    "Array(DateTime)": pa.list_(pa.timestamp("s")),
    # 嵌套类型（元组、枚举等）
    # 注意：Arrow 不直接支持 Tuple，通常需要转换为 Struct
    "Tuple": pa.struct([]),  # 需要动态定义每个字段的类型
    # 枚举类型
    "Enum8": pa.string(),  # 通常映射为字符串
    "Enum16": pa.string(),
    # Map 类型
    "Map": pa.map_(pa.string(), pa.string()),  # 默认键值对是字符串（可根据需求调整）
    # Nullable 类型（ClickHouse 的 Nullable 包装类型）
    "Nullable(Int8)": pa.int8(),
    "Nullable(Int16)": pa.int16(),
    "Nullable(Int32)": pa.int32(),
    "Nullable(Int64)": pa.int64(),
    "Nullable(UInt8)": pa.uint8(),
    "Nullable(UInt16)": pa.uint16(),
    "Nullable(UInt32)": pa.uint32(),
    "Nullable(UInt64)": pa.uint64(),
    "Nullable(Float32)": pa.float32(),
    "Nullable(Float64)": pa.float64(),
    "Nullable(String)": pa.string(),
    "Nullable(Date)": pa.date32(),
    "Nullable(DateTime)": pa.timestamp("s"),
    "Nullable(UUID)": pa.binary(16),
}


def map_clickhouse_decimal(ch_type: str) -> pa.DataType:
    """
    映射 ClickHouse 的 Decimal 类型到 Arrow 的 Decimal 类型
    :param ch_type: ClickHouse 的 Decimal 类型描述，例如 'Decimal(10, 2)' 或 'Decimal128(38)'
    :return: 对应的 Arrow Decimal 类型
    """
    # 匹配 ClickHouse 的 Decimal(p, s) 格式
    decimal_match = re.match(r"Decimal(?:32|64|128|256)?\((\d+),\s*(\d+)\)", ch_type)
    if decimal_match:
        precision, scale = map(int, decimal_match.groups())
        # 依据精度选择 128/256；Arrow 128 支持到 38 位，超过则使用 256
        if precision <= 38:
            return pa.decimal128(precision, scale)
        else:
            return pa.decimal256(precision, scale)

    # 匹配 ClickHouse 的 Decimal(p) 格式，默认 scale 为 0
    decimal_match_no_scale = re.match(r"Decimal(?:32|64|128|256)?\((\d+)\)", ch_type)
    if decimal_match_no_scale:
        precision = int(decimal_match_no_scale.group(1))
        if precision <= 38:
            return pa.decimal128(precision, 0)
        else:
            return pa.decimal256(precision, 0)

    # 如果不匹配，抛出异常
    raise ValueError(f"Unsupported ClickHouse Decimal type: {ch_type}")


def map_clickhouse_to_arrow(ch_type: str) -> pa.DataType:
    """
    动态映射 ClickHouse 类型到 Arrow 类型
    """
    # 规范化类型名称（去除多余空格）
    ch_type = ch_type.strip()

    # 基础类型直接映射
    if ch_type in CLICKHOUSE_TO_ARROW_TYPE:
        return CLICKHOUSE_TO_ARROW_TYPE[ch_type]

    # Decimal 类型处理
    if ch_type.startswith("Decimal"):
        return map_clickhouse_decimal(ch_type)

    # 动态处理 Array 类型
    if ch_type.startswith("Array("):
        inner_type = ch_type[6:-1]  # 提取 Array 内的类型
        return pa.list_(map_clickhouse_to_arrow(inner_type))

    # 动态处理 Nullable 类型
    if ch_type.startswith("Nullable("):
        inner_type = ch_type[9:-1]  # 提取 Nullable 内的类型
        return map_clickhouse_to_arrow(inner_type)

    # 处理 LowCardinality 包装类型
    if ch_type.startswith("LowCardinality("):
        inner_type = ch_type[15:-1]
        return map_clickhouse_to_arrow(inner_type)

    # 处理 DateTime64(precision[, 'tz']) 精度
    if ch_type.startswith("DateTime64("):
        # 支持 DateTime64(3) 或 DateTime64(3, 'UTC')
        m = re.match(r"DateTime64\(\s*(\d+)(?:\s*,\s*'[^']+'\s*)?\)", ch_type)
        if m:
            precision = m.group(1)
            unit = timeunit_from_precision(precision) or "ms"
            return pa.timestamp(unit)
        # 无法解析则回退到毫秒
        return pa.timestamp("ms")

    # 动态处理 Tuple 类型
    if ch_type.startswith("Tuple("):
        inner_types = ch_type[6:-1].split(",")  # 提取 Tuple 内的字段类型
        return pa.struct(
            [
                ("field" + str(i), map_clickhouse_to_arrow(t.strip()))
                for i, t in enumerate(inner_types)
            ]
        )

    # 动态处理 Map 类型
    if ch_type.startswith("Map("):
        key_type, value_type = ch_type[4:-1].split(",")
        return pa.map_(
            map_clickhouse_to_arrow(key_type.strip()),
            map_clickhouse_to_arrow(value_type.strip()),
        )

    raise ValueError(f"Unsupported ClickHouse type: {ch_type}")
