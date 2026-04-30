"""
因子计算框架

提供因子定义、依赖管理和计算执行引擎。
"""

from . import ops
from .api import Factor
from .context import FactorContext
from .core import (
    FIELD,
    FORMAT,
    INDEX,
    TIMETYPE,
    BasicFactor,
    DelayedFunction,
    delay,
    fn_code,
    fn_info,
    fn_params,
    fn_path,
)
from .engine import get_history, get_update_tasks, get_value
from .graph import get_execution_plan


def update_factors(
    factors: list[Factor],
    beg_date: str,
    end_date: str,
    n_jobs: int = 11,
):
    from tool_box import ygo

    plan = get_execution_plan(*factors)
    groups = plan["parallel_groups"]

    def run_update(factors: list, epoch: int):
        with ygo.Pool(n_jobs=n_jobs) as go:
            for fac in factors:
                for task in get_update_tasks(fac, beg_date, end_date):
                    go.submit(task, job_name=f"[{epoch}/{len(groups)}] {fac.name}")()
            go.do()

    for i, g in enumerate(groups):
        run_update(g, epoch=i + 1)


__all__ = [
    "ops",
    "Factor",
    "BasicFactor",
    "FactorContext",
    "get_value",
    "get_history",
    "update_factors",
    # core exports
    "FIELD",
    "FORMAT",
    "INDEX",
    "TIMETYPE",
    "DelayedFunction",
    "delay",
    "fn_code",
    "fn_info",
    "fn_params",
    "fn_path",
]
