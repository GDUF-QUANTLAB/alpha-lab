from __future__ import annotations

import hashlib
import inspect
import os
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import rich


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


class BasicFactor:
    """
    因子类

    通过组合方式维护函数元信息，添加依赖管理和因子特有功能。
    """

    def __init__(
        self,
        *depends: BasicFactor,
        fn: callable,
        name: str = None,
        insert_time: str = None,
    ):
        self.fn = fn
        self.__doc__ = fn.__doc__
        self._fn_info = fn_info(fn)
        self.fn_params = fn_params(fn)
        self.name = name if name else fn.__name__
        self._version = None
        self.insert_time = insert_time
        self.lag = 0

        self._depends = list(depends)
        self._detect_circular_dependency()

        self._version = self._compute_version()

    def _detect_circular_dependency(self) -> None:
        visited: set[BasicFactor] = set()
        path: list[BasicFactor] = []

        def dfs(factor: BasicFactor) -> None:
            if factor in path:
                cycle = " -> ".join(
                    [str(f) or f"{f.fn.__name__}" for f in path[path.index(factor) :]]
                )
                raise ValueError(f"Circular dependency detected: {cycle}")

            if factor in visited:
                return

            visited.add(factor)
            path.append(factor)

            for depend in factor._depends:
                dfs(depend)

            path.pop()

        dfs(self)

    def _compute_version(self) -> str:
        self_version = hashlib.md5(self._fn_info.encode()).hexdigest()

        if not self._depends:
            return self_version

        depends_version = [f"{depend.version}.{depend.lag}" for depend in self._depends]
        depends_version.append(self_version)

        combined_version = ",".join(depends_version)
        return hashlib.md5(combined_version.encode()).hexdigest()

    @property
    def version(self) -> str:
        if self._version is None:
            self._version = self._compute_version()
        return self._version

    def _format_params(self) -> str:
        params = self.fn_params
        all_define_params = sorted(inspect.signature(self.fn).parameters.keys())

        default_params = dict(params)
        params_infos = []

        for p in all_define_params:
            if p in default_params:
                params_infos.append(f"{p}={default_params[p]}")
            else:
                params_infos.append(p)

        return ", ".join(params_infos)

    def __repr__(self) -> str:
        params_infos = self._format_params()
        mod = fn_path(self.fn)
        return f"{mod}.{self.fn.__name__}({params_infos})"

    def __str__(self) -> str:
        return str(self.name) if self.name is not None else ""

    @property
    def tb_name(self) -> str:
        return os.path.join(
            "factors",
            f"name={self.name}",
            f"version={self.version}",
        )

    def info(self) -> None:
        rich.inspect(self, help=True)

    def get_dependencies(self) -> list[BasicFactor]:
        return self._depends

    def get_all_dependencies(self) -> set[BasicFactor]:
        dependencies: set[BasicFactor] = set()

        def collect_dependencies(factor: BasicFactor) -> None:
            for depend in factor._depends:
                if depend not in dependencies:
                    dependencies.add(depend)
                    collect_dependencies(depend)

        collect_dependencies(self)
        return dependencies

    @abstractmethod
    def shift(self, n: int = 1) -> BasicFactor:
        raise NotImplementedError("shift method must be implemented")
