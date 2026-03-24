"""
延迟执行函数

提供函数延迟执行和参数绑定功能。
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


class DelayedFunction:
    """
    延迟执行函数包装器

    支持参数绑定和延迟执行。参数绑定返回新的 DelayedFunction（不可变）。

    Attributes:
        func: 原始函数
        _fn_params_k: 函数参数名称集合
        stored_kwargs: 存储的关键字参数字典

    Examples:
        >>> from tool_box.ygo import delay
        >>> fn = delay(lambda a, b: a + b).bind(a=1, b=2)
        >>> fn()
        3

        >>> fn1 = delay(lambda a, b, c: a + b + c).bind(a=1)
        >>> fn2 = fn1.bind(b=2)
        >>> fn2(c=3)
        6
    """

    def __init__(
        self, func: Callable[..., Any], stored_kwargs: dict[str, Any] | None = None
    ):
        """
        初始化延迟函数。

        Args:
            func: 要包装的可调用对象
            stored_kwargs: 已存储的参数
        """
        self.func = func
        self._fn_params_k = set(inspect.signature(self.func).parameters.keys())
        if stored_kwargs is not None:
            self.stored_kwargs = stored_kwargs
        else:
            self.stored_kwargs = self._get_default_args(func)
            if hasattr(func, "stored_kwargs"):
                self.stored_kwargs = {**self.stored_kwargs, **func.stored_kwargs}

    def _get_default_args(self, func: Callable[..., Any]) -> dict[str, Any]:
        """
        从函数签名中提取默认参数。

        Args:
            func: 要分析的函数

        Returns:
            Dict[str, Any]: 默认参数字典
        """
        signature = inspect.signature(func)
        return {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

    def bind(self, **kwargs: Any) -> DelayedFunction:
        """
        绑定参数，返回新的 DelayedFunction。

        Args:
            **kwargs: 要绑定的参数

        Returns:
            DelayedFunction: 新的延迟函数对象
        """
        new_kwargs = {k: v for k, v in kwargs.items() if k in self._fn_params_k}
        merged_kwargs = {**self.stored_kwargs, **new_kwargs}
        return DelayedFunction(self.func, stored_kwargs=merged_kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        执行函数，使用绑定的参数和传入的参数。

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Any: 函数执行结果
        """
        final_kwargs = dict(self.stored_kwargs)
        for k, v in kwargs.items():
            if k in self._fn_params_k:
                final_kwargs[k] = v
        return self.func(*args, **final_kwargs)


def delay(func: T) -> DelayedFunction:
    """
    创建延迟执行函数。

    Args:
        func: 要延迟执行的可调用对象

    Returns:
        DelayedFunction: 延迟函数对象

    Examples:
        基本使用：

        >>> fn = delay(lambda a, b: a + b)
        >>> fn(a=1, b=2)
        3

        链式绑定参数：

        >>> fn1 = delay(lambda a, b, c: a + b + c).bind(a=1)
        >>> fn2 = fn1.bind(b=2)
        >>> fn2(c=3)
        6

        参数覆盖：

        >>> fn = delay(lambda a, b: a + b).bind(a=1, b=2)
        >>> fn(b=5)
        6
    """
    return DelayedFunction(func)
