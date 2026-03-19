"""
并发任务调度器

提供基于joblib的并行任务调度功能，支持进度条显示和任务分组。
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from joblib import Parallel, delayed
from loguru import logger

from .delay import DelayedFunction, delay
from .progress import ProgressManager

T = TypeVar("T")


def run_job(job: DelayedFunction, task_name: str) -> tuple[str, Any]:
    """
    执行单个延迟任务。

    Args:
        job: 要执行的延迟函数
        task_name: 任务组名称

    Returns:
        tuple[str, Any]: 包含任务名称和结果的元组

    Raises:
        Exception: 如果任务执行失败

    Examples:
        >>> from tool_box.ygo import delay
        >>> job = delay(lambda x: x * 2)(x=5)
        >>> result = run_job(job, "test_task")
        >>> result
        ('test_task', 10)
    """
    try:
        return task_name, job()
    except Exception as e:
        logger.error(f"Failed to run job: {task_name}-{job}:{job.stored_kwargs}\n{e}")
        return task_name, None


def multi_task_name(
    job_map: dict[str, list[DelayedFunction]],
    job_num: int,
    backend: str,
    show_progress: bool,
) -> list[Any] | dict[str, list[Any]]:
    """
    并行执行多个任务。

    Args:
        job_map: 任务名称到延迟函数列表的映射字典
        job_num: 并行任务数量
        backend: 并行执行后端（如 'threading', 'multiprocessing'）
        show_progress: 是否显示进度条

    Returns:
        Union[List[Any], Dict[str, List[Any]]]: 执行任务的结果
        如果只有一个任务组，返回结果列表
        否则返回任务名称到结果列表的映射字典

    Examples:
        >>> from tool_box.ygo import delay
        >>> jobs = {"task1": [delay(lambda: 1)(), "task2": [delay(lambda: 2)()]}
        >>> results = multi_task_name(jobs, 2, "threading", False)
        >>> results
        {'task1': [1], 'task2': [2]}
    """
    _parallel = Parallel(
        n_jobs=job_num,
        verbose=0,
        backend=backend,
        return_as="generator_unordered",
    )

    if show_progress:
        with ProgressManager(show_progress=True) as progress_mgr:
            for name, jobs in job_map.items():
                progress_mgr.create_task(name, total=len(jobs))

            job_lst = []
            for name, jobs in job_map.items():
                for job in jobs:
                    job_lst.append(delayed(run_job)(job=job, task_name=name))

            results: dict[str, list[Any]] = {}
            for name, result in _parallel(job_lst):
                progress_mgr.update(progress_mgr._task_map.get(name))
                if results.get(name) is None:
                    results[name] = [result]
                else:
                    results[name].append(result)
    else:
        job_lst = []
        for name, jobs in job_map.items():
            for job in jobs:
                job_lst.append(delayed(run_job)(job=job, task_name=name))

        results: dict[str, list[Any]] = {}
        for name, result in _parallel(job_lst):
            if results.get(name) is None:
                results[name] = [result]
            else:
                results[name].append(result)

    if len(results) == 1:
        return list(results.values())[0]
    return results


class Pool:
    """
    并发任务池

    用于管理和执行并行任务的池类，支持任务分组、进度显示等功能。

    Attributes:
        _n_jobs: 并行任务数量
        backend: 并行执行后端
        show_progress: 是否显示进度条
        _job_map: 任务收集字典

    Examples:
        >>> pool = Pool(n_jobs=4, show_progress=True)
        >>> @pool.submit(job_name="data_processing")
        >>> def process_data(date: str):
        ...     return f"Processed {date}"
        >>> process_data(date="2023-01-01")
        >>> pool.do()
        ['Processed 2023-01-01']
    """

    def __init__(
        self,
        n_jobs: int = 5,
        show_progress: bool = True,
        backend: str = "threading",
    ):
        """
        初始化并发任务池。

        Args:
            n_jobs: 并行任务数量，默认为 5
            show_progress: 是否显示进度条，默认为 True
            backend: 并行执行后端 ('threading' 或 'multiprocessing')，默认为 "threading"
        """
        self._n_jobs = n_jobs
        self.backend = backend
        self.show_progress = show_progress

        self._job_map: dict[str, list[DelayedFunction]] = {}

    def submit(
        self, fn: Callable[..., T], job_name: str | None = None
    ) -> Callable[..., DelayedFunction]:
        """
        提交任务到池中。

        Args:
            fn: 要执行的函数
            job_name: 任务组名称，默认为 "Null-JOB"

        Returns:
            Callable: 包装函数，调用时将任务添加到池中

        Examples:
            >>> pool = Pool()
            >>> @pool.submit(job_name="test")
            >>> def add(a: int, b: int) -> int:
            ...     return a + b
            >>> add(a=1, b=2)
            <DelayedFunction object>
        """
        job_name = "Null-JOB" if job_name is None else job_name

        @functools.wraps(fn)
        def collect(**kwargs) -> DelayedFunction:
            """收集任务"""
            job = delay(fn)(**kwargs)

            if self._job_map.get(job_name) is None:
                self._job_map[job_name] = [job]
            else:
                self._job_map[job_name].append(job)

            return job

        return collect

    def do(self) -> list[Any] | dict[str, list[Any]]:
        """
        执行所有提交的任务。

        Returns:
            list[Any] | dict[str, list[Any]]: 任务执行的结果
            如果只有一个任务组，返回结果列表
            否则返回任务名称到结果列表的映射字典

        Examples:
            >>> pool = Pool(n_jobs=2)
            >>> @pool.submit(job_name="task1")
            >>> def task1_func():
            ...     return 1
            >>> @pool.submit(job_name="task2")
            >>> def task2_func():
            ...     return 2
            >>> task1_func()
            >>> task2_func()
            >>> pool.do()
            {'task1': [1], 'task2': [2]}
        """
        job_num = min(sum([len(i) for i in self._job_map.values()]), self._n_jobs)
        if job_num == 0:
            return []
        if job_num < self._n_jobs:
            logger.warning(
                f"N_JOBS floating out: use max job num {job_num} under {self._n_jobs}"
            )

        res = multi_task_name(
            self._job_map,
            job_num,
            self.backend,
            self.show_progress,
        )
        self._job_map = {}
        return res

    def close(self):
        self._n_jobs = None
        self._job_map = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
