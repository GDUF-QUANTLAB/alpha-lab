from __future__ import annotations

from enum import Enum


class FIELD:
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    ASSET = "asset"
    VERSION = "version"
    ENDTIME = "end_time"
    VALUE = "value"
    NAME = "name"
    FIELDNAMES = "field_names"


class TIMETYPE(Enum):
    FIXED = "fixed_time"
    REAL = "real_time"


class FORMAT:
    DATE = "%Y-%m-%d"
    TIME = "%H:%M:%S"


INDEX = (FIELD.ASSET, FIELD.DATETIME)
