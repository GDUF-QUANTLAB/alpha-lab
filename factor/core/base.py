from __future__ import annotations

import hashlib
import inspect
import os

import rich

from .constants import FIELD
from .delayed import delay, fn_code, fn_info, fn_params, fn_path


class BasicFactor:
    """
    因子类

    通过组合方式维护函数元信息，添加依赖管理和因子特有功能。
    """

    def __init__(
        self,
        *depends,
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
        visited: set = set()
        path: list = []

        def dfs(factor) -> None:
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

        cubase = getattr(self, "_cubase", None)
        depends_version = []
        for idx, depend in enumerate(self._depends):
            if cubase is None:
                config = {"lag": depend.lag}
            else:
                config = {
                    key: value
                    for key, value in cubase.get_config(idx).items()
                    if key != "factor"
                }
            config_info = ",".join(
                f"{key}={value!r}" for key, value in sorted(config.items())
            )
            depends_version.append(f"{depend.version}.{config_info}")
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

    def get_dependencies(self) -> list:
        return self._depends

    def get_all_dependencies(self) -> set:
        dependencies: set = set()

        def collect_dependencies(factor) -> None:
            for depend in factor._depends:
                if depend not in dependencies:
                    dependencies.add(depend)
                    collect_dependencies(depend)

        collect_dependencies(self)
        return dependencies
