"""
Factor 用户 API

提供用户友好的因子创建接口。
"""

from __future__ import annotations

from .core import BasicFactor, delay


class Factor(BasicFactor):
    def __init__(
        self,
        *depends: BasicFactor,
        fn: callable,
        insert_time: str,
        name: str = None,
        frame: int = 1,
    ):
        self._frame = frame

        if name is None:
            from varname import varname

            try:
                name = varname(self._frame, strict=False)
            except Exception as e:
                raise e
        name = str(name).split("fac_")[-1]
        super().__init__(
            *depends,
            fn=fn,
            name=name,
            insert_time=insert_time,
        )

    def __call__(self, **kwargs) -> Factor:
        frame = self._frame + 1
        newFactor = Factor(
            *self._depends,
            fn=delay(self.fn).bind(**kwargs),
            insert_time=self.insert_time,
            name=self.name,
            frame=frame,
        )
        return newFactor
