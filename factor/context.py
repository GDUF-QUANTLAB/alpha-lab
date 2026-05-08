from __future__ import annotations

import polars as pl

from .core import BasicFactor, Cubase


class FactorContext:
    """
    依赖因子数据加载上下文。

    支持两种初始化方式：
    1. Cubase: FactorContext(cubase, loader_time="15:00:00")
    2. 直接因子: FactorContext(fac1, fac2, ..., loader_time="15:00:00")
    """

    def __init__(self, *args, loader_time: str):
        if len(args) == 1 and isinstance(args[0], Cubase):
            self.cubase = args[0]
        else:
            # 兼容旧API: 将 *dep_fac 转为 Cubase
            self.cubase = Cubase([{"factor": fac} for fac in args])
        self.loader_time = loader_time

    @property
    def dep_names(self) -> list[str]:
        return self.cubase.dep_names

    @property
    def dep_facs(self) -> list[BasicFactor]:
        """兼容属性，返回因子列表"""
        return self.cubase.factors

    def load(
        self,
        date: str = None,
        beg_date: str = None,
        end_date: str = None,
    ) -> pl.DataFrame:
        return self.cubase.load(
            date=date,
            beg_date=beg_date,
            end_date=end_date,
            loader_time=self.loader_time,
        )

    def load_window(
        self,
        date: str,
        window: int = 1,
    ) -> pl.DataFrame:
        return self.cubase.load_window(
            date,
            window=window,
            loader_time=self.loader_time,
        )
