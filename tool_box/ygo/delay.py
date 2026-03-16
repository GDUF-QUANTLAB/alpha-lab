"""
延迟执行函数

提供函数延迟执行和参数绑定功能。
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


class DelayedFunction:
    """
    延迟执行函数包装器

    支持延迟执行和部分参数绑定的函数包装类。

    Attributes:
        func: 原始函数
        _fn_params_k: 函数参数名称列表
        stored_kwargs: 存储的关键字参数字典

    Examples:
        >>> from tool_box.ygo import delay
        >>> fn = delay(lambda a, b: a + b)(a=1, b=2)
        >>> fn()
        3

        >>> fn1 = delay(lambda a, b, c: a + b + c)(a=1)
        >>> fn2 = delay(fn1)(b=2)
        >>> fn2(c=3)
        6
    """

    def __init__(self, func: Callable[..., Any]):
        """
        初始化延迟函数。

        Args:
            func: 要包装的可调用对象
        """
        self.func = func
        self._fn_params_k = inspect.signature(self.func).parameters.keys()
        self.stored_kwargs: dict[str, Any] = self._get_default_args(func)
        if hasattr(func, "stored_kwargs"):
            self.stored_kwargs.update(func.stored_kwargs)

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

    def __call__(self, *args: Any, **kwargs: Any) -> Callable[..., Any]:
        """
        调用时更新存储的参数并返回新的包装函数。
        如果没有参数，则使用存储的参数执行原始函数。

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Callable[..., Any]: 新的包装函数

        Examples:
            >>> fn = delay(lambda x: x * 2)
            >>> wrapped = fn(x=5)
            >>> wrapped()
            10
        """

        def delayed(*args: Any, **_kwargs: Any) -> Any:
            """
            延迟执行函数。

            Args:
                *args: 位置参数
                **_kwargs: 关键字参数

            Returns:
                Any: 函数执行结果
            """
            new_kwargs = dict(self.stored_kwargs)
            for k, v in _kwargs.items():
                if k not in self._fn_params_k:
                    continue
                new_kwargs[k] = v
            return self.func(*args, **new_kwargs)

        self._update_stored_kwargs(**kwargs)
        new_fn = wraps(self.func)(delayed)
        new_fn.stored_kwargs = self.stored_kwargs
        return new_fn

    def _update_stored_kwargs(self, **kwargs: Any) -> None:
        """
        更新存储的关键字参数。

        Args:
            **kwargs: 要更新的关键字参数
        """
        for k, v in kwargs.items():
            if k not in self._fn_params_k:
                continue
            self.stored_kwargs[k] = v


def delay(func: T) -> DelayedFunction:
    """
    创建延迟执行函数的装饰器。

    Args:
        func: 要延迟执行的可调用对象

    Returns:
        DelayedFunction: 原始可调用对象的包装器

    Examples:
        基本使用：

        >>> fn = delay(lambda a, b: a+b)(a=1, b=2)
        >>> fn()
        3

        逐步传递参数：

        >>> fn1 = delay(lambda a, b, c: a+b+c)(a=1)
        >>> fn2 = delay(fn1)(b=2)
        >>> fn2(c=3)
        6

        参数更新：

        >>> fn1 = delay(lambda a, b, c: a+b+c)(a=1, b=2)
        >>> fn2 = delay(fn1)(c=3, b=5)
        >>> fn2()
        9
    """
    return DelayedFunction(func)
