"""
因子运算函数

提供常用的因子运算操作。
"""

import math

import polars as pl

from ..context import FactorContext
from ..core import FIELD


def LOG(cb: FactorContext, date: str, base: int = None):
    if base is None:
        base = math.e
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.col(cb.dep_names[0]).log(base),
    )


def EXP(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.col(cb.dep_names[0]).exp(),
    )


def ADD(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.sum_horizontal(cb.dep_names),
    )


def SUB(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.col(cb.dep_names[0]) - pl.col(cb.dep_names[1]),
    )


def DIV(cb: FactorContext, date: str):
    left, right = (
        pl.col(cb.dep_names[0]).cast(float),
        pl.col(cb.dep_names[1]).cast(float),
    )
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.when(right == 0).then(None).otherwise(left / right),
    )


def MUL(cb: FactorContext, date: str):
    left, right = (
        pl.col(cb.dep_names[0]).cast(float),
        pl.col(cb.dep_names[1]).cast(float),
    )
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=left * right,
    )


def PCT(cb: FactorContext, date: str):
    left, right = (
        pl.col(cb.dep_names[0]).cast(float),
        pl.col(cb.dep_names[1]).cast(float),
    )
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.when(right == 0).then(None).otherwise(left / right - 1),
    )


def ABS(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=pl.col(cb.dep_names[0]).abs(),
    )


def UFOLD(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=(pl.col(cb.dep_names[0]) - pl.col(cb.dep_names[0]).median()).abs(),
    )


def ZFOLD(cb: FactorContext, date: str):
    return cb.load(date).select(
        pl.col(FIELD.ASSET),
        value=(pl.col(cb.dep_names[0]) - pl.col(cb.dep_names[0]).mean()).abs(),
    )
