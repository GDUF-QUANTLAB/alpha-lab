from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Any


class DelayedFunction:
    def __init__(self, func: callable, stored_kwargs: dict[str, Any] | None = None):
        if isinstance(func, DelayedFunction):
            self.func = func
            self._fn_params_k = func._fn_params_k
            self.stored_kwargs = func.stored_kwargs
            if stored_kwargs is not None:
                self.stored_kwargs.update(stored_kwargs)
        else:
            self.func = func
            self._fn_params_k = set(inspect.signature(self.func).parameters.keys())
            if stored_kwargs is not None:
                self.stored_kwargs = stored_kwargs
            else:
                self.stored_kwargs = self._get_default_args(func)
                if hasattr(func, "stored_kwargs"):
                    self.stored_kwargs = {**self.stored_kwargs, **func.stored_kwargs}

    @property
    def __name__(self) -> str:
        return self.func.__name__

    def _get_default_args(self, func: callable) -> dict[str, Any]:
        signature = inspect.signature(func)
        return {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

    def bind(self, **kwargs) -> DelayedFunction:
        new_kwargs = {k: v for k, v in kwargs.items() if k in self._fn_params_k}
        merged_kwargs = {**self.stored_kwargs, **new_kwargs}
        return DelayedFunction(self.func, stored_kwargs=merged_kwargs)

    def __call__(self, *args, **kwargs) -> Any:
        final_kwargs = dict(self.stored_kwargs)
        for k, v in kwargs.items():
            if k in self._fn_params_k:
                final_kwargs[k] = v
        return self.func(*args, **final_kwargs)


def delay(func: callable) -> DelayedFunction:
    return DelayedFunction(func)


def fn_params(func: callable) -> list[tuple]:
    if isinstance(func, DelayedFunction):
        return sorted(func.stored_kwargs.items())
    stored = delay(func).stored_kwargs.items()
    return sorted(stored)


def fn_path(fn: callable) -> str:
    module = fn.__module__
    if module.startswith("__main__"):
        if hasattr(module, "__file__"):
            module = module.__file__
        else:
            module = "<interactive environment>"
    if module.endswith(".py"):
        module = module.split(".py")[0].split(str(Path(__file__).parent.absolute()))[-1]
        module = ".".join(module.strip(os.sep).split(os.sep))
    return module


def fn_code(fn: callable) -> str:
    if isinstance(fn, DelayedFunction):
        return inspect.getsource(fn.func)
    return inspect.getsource(fn)


def fn_info(fn: callable) -> str:
    params = fn_params(fn)
    code = fn_code(fn)

    target_fn = fn.func if isinstance(fn, DelayedFunction) else fn
    all_define_params = sorted(inspect.signature(target_fn).parameters.keys())

    default_params = dict(params)
    params_infos = []
    for p in all_define_params:
        if p in default_params:
            params_infos.append(f"{p}={default_params[p]}")
        else:
            params_infos.append(p)
    params_infos = ", ".join(params_infos)
    s = "=============================================================\n"
    s += f"{target_fn.__name__}({params_infos})\n"
    s += "=============================================================\n"
    s += f"{code}\n"
    return s