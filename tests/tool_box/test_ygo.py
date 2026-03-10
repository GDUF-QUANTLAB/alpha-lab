from tool_box.ygo import Pool, delay


def add(a, b):
    return a + b


def test_delay():
    # Basic usage
    fn = delay(add)(a=1, b=2)
    assert fn() == 3

    # Partial args
    fn_partial = delay(add)(a=1)
    assert fn_partial(b=2) == 3

    # Override args
    _ = delay(add)(a=1, b=2)
    # Note: delay returns a function that when called executes the original function
    # but the implementation of DelayedFunction.__call__ returns a WRAPPED function 'delayed'
    # which when called executes self.func.

    # Wait, let's look at DelayedFunction.__call__:
    # return new_fn (which is 'delayed')

    # So fn_override is 'delayed'.
    # Calling fn_override() calls self.func(*args, **new_kwargs)

    # However, DelayedFunction.__call__ logic:
    # def delayed(*args, **_kwargs): ...
    # self._stored_kwargs(**kwargs)  <-- This updates stored_kwargs immediately when delay()() is called?

    # Usage: delay(func)(a=1, b=2)
    # 1. delay(func) -> DelayedFunction(func)
    # 2. DelayedFunction(func)(a=1, b=2) -> calls __call__(a=1, b=2)
    #    -> updates self.stored_kwargs with a=1, b=2
    #    -> returns 'delayed' function wrapper

    # 3. 'delayed'() -> calls func with stored_kwargs

    fn = delay(add)(a=1, b=2)
    assert fn() == 3


def test_pool():
    p = Pool(n_jobs=2, show_progress=False)

    def task_impl(x):
        return x * x

    task = p.submit(task_impl, job_name="test_job")

    # Submit tasks
    # The decorator returns 'collect', which when called:
    # 1. calls delay(fn)(**kwargs) -> returns delayed function 'job'
    # 2. adds 'job' to p._job_map
    # 3. returns 'job'

    task(x=1)
    task(x=2)
    task(x=3)

    assert len(p._job_map["test_job"]) == 3

    # Execute
    results = p.do()

    # Results structure:
    # If multiple job_names: {name: [results...]}
    # If single job_name: [results...] due to line 55 in pool.py

    assert isinstance(results, list)
    # Order is not guaranteed due to "generator_unordered"
    results_sorted = sorted(results)
    assert results_sorted == [1, 4, 9]


def test_pool_multiple_groups():
    p = Pool(n_jobs=2, show_progress=False)

    def task1_impl(x):
        return x

    task1 = p.submit(task1_impl, job_name="group1")

    def task2_impl(x):
        return x * 2

    task2 = p.submit(task2_impl, job_name="group2")

    task1(x=1)
    task2(x=1)

    results = p.do()
    assert isinstance(results, dict)
    assert "group1" in results
    assert "group2" in results
    assert results["group1"] == [1]
    assert results["group2"] == [2]
