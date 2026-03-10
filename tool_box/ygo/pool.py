from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from joblib import Parallel, delayed
from loguru import logger
from tqdm.auto import tqdm

from .delay import DelayedFunction, delay

T = TypeVar("T")


def run_job(job: DelayedFunction, task_name: str) -> tuple[str, Any]:
    """
    Executes a single delayed job.

    Args:
        job: The delayed function to execute.
        task_name: The name of the task group.

    Returns:
        tuple[str, Any]: A tuple containing the task name and the result of the job.
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
    Executes multiple tasks in parallel.

    Args:
        job_map: A dictionary mapping task names to lists of delayed functions.
        job_num: The number of parallel jobs to run.
        backend: The backend to use for parallel execution (e.g., 'threading', 'multiprocessing').
        show_progress: Whether to show a progress bar.

    Returns:
        list[Any] | dict[str, list[Any]]: The results of the executed tasks.
        If only one task group exists, returns a list of results.
        Otherwise, returns a dictionary mapping task names to lists of results.
    """
    _parallel = Parallel(
        n_jobs=job_num,
        verbose=0,
        backend=backend,
        return_as="generator_unordered",
    )

    if show_progress:
        tqdm_map = {k: tqdm(desc=f"{k} ", total=len(v)) for k, v in job_map.items()}

        job_lst = []
        for name, jobs in job_map.items():
            for job in jobs:
                job_lst.append(delayed(run_job)(job=job, task_name=name))

        results: dict[str, list[Any]] = {}
        for name, result in _parallel(job_lst):
            tqdm_map[name].update(1)
            if results.get(name) is None:
                results[name] = [result]
            else:
                results[name].append(result)

        for v in tqdm_map.values():
            v.close()
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
    def __init__(
        self,
        n_jobs: int = 5,
        show_progress: bool = True,
        backend: str = "threading",
    ):
        """
        Initializes the Pool.

        Args:
            n_jobs: Number of parallel jobs. Defaults to 5.
            show_progress: Whether to show progress bar. Defaults to True.
            backend: Parallel backend ('threading' or 'multiprocessing'). Defaults to "threading".
        """
        self._n_jobs = n_jobs
        self.backend = backend
        self.show_progress = show_progress

        self._job_map: dict[str, list[DelayedFunction]] = {}  # Task collection

    def submit(
        self, fn: Callable[..., T], job_name: str | None = None
    ) -> Callable[..., DelayedFunction]:
        """
        Submits a task to the pool.

        Args:
            fn: The function to execute.
            job_name: Optional name for the task group. Defaults to "Null-JOB".

        Returns:
            Callable: A wrapper function that, when called, adds the job to the pool.
        """
        job_name = "Null-JOB" if job_name is None else job_name

        @functools.wraps(fn)
        def collect(**kwargs) -> DelayedFunction:
            """Collects the task."""
            job = delay(fn)(**kwargs)

            if self._job_map.get(job_name) is None:
                self._job_map[job_name] = [job]
            else:
                self._job_map[job_name].append(job)

            return job

        return collect

    def do(self) -> list[Any] | dict[str, list[Any]]:
        """
        Executes all submitted tasks.

        Returns:
            list[Any] | dict[str, list[Any]]: The results of the tasks.
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
