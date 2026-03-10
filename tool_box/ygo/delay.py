from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


class DelayedFunction:
    """
    A wrapper class for functions that supports delayed execution and partial argument binding.
    """

    def __init__(self, func: Callable[..., Any]):
        self.func = func
        self._fn_params_k = inspect.signature(self.func).parameters.keys()
        self.stored_kwargs: dict[str, Any] = self._get_default_args(func)
        if hasattr(func, "stored_kwargs"):
            self.stored_kwargs.update(func.stored_kwargs)

    def _get_default_args(self, func: Callable[..., Any]) -> dict[str, Any]:
        """
        Extracts default arguments from the function signature.
        """
        signature = inspect.signature(func)
        return {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

    def __call__(self, *args: Any, **kwargs: Any) -> Callable[..., Any]:
        """
        When called, updates stored arguments and returns a new wrapped function.
        If called with no arguments, executes the original function with stored arguments.
        """

        def delayed(*args: Any, **_kwargs: Any) -> Any:
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
        Updates the stored keyword arguments.
        """
        for k, v in kwargs.items():
            if k not in self._fn_params_k:
                continue
            self.stored_kwargs[k] = v


def delay(func: T) -> DelayedFunction:
    """
    Decorator to create a DelayedFunction.

    Args:
        func: The callable object to be delayed.

    Returns:
        DelayedFunction: A wrapper around the original callable.

    Examples:
        >>> fn = delay(lambda a, b: a+b)(a=1, b=2)
        >>> fn()
        3

        >>> fn1 = delay(lambda a, b, c: a+b+c)(a=1)
        >>> fn2 = delay(fn1)(b=2)
        >>> fn2(c=3)
        6
    """
    return DelayedFunction(func)
