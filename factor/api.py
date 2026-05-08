"""
Factor 用户 API

提供用户友好的因子创建接口。
"""

from __future__ import annotations

from .core import BasicFactor, Cubase, delay


class Factor(BasicFactor):
    def __init__(
        self,
        *depends,
        fn: callable,
        insert_time: str,
        name: str = None,
        frame: int = 1,
    ):
        """
        创建因子。

        支持两种依赖声明方式：
        1. Cubase: Factor(cubase, fn=...)
        2. 直接因子: Factor(fac1, fac2, fn=...)
        """
        self._frame = frame

        # 处理依赖：可能是 Cubase 或直接是 BasicFactor
        if len(depends) == 1 and isinstance(depends[0], Cubase):
            cubase = depends[0]
            raw_depends = cubase.factors
        else:
            raw_depends = depends
            cubase = Cubase(
                [{"factor": fac, "lag": getattr(fac, "lag", 0)} for fac in raw_depends]
            )

        self._cubase = cubase

        if name is None:
            from varname import varname

            try:
                name = varname(self._frame, strict=False)
            except Exception as e:
                raise e
        name = str(name).split("fac_")[-1]
        super().__init__(
            *raw_depends,
            fn=fn,
            name=name,
            insert_time=insert_time,
        )

    def __call__(self, **kwargs) -> Factor:
        frame = self._frame + 1
        newFactor = Factor(
            self._cubase,
            fn=delay(self.fn).bind(**kwargs),
            insert_time=self.insert_time,
            name=self.name,
            frame=frame,
        )
        return newFactor
