from ygo import Pool, ProgressManager, delay


def add(a, b):
    return a + b


def test_delay():
    fn = delay(add).bind(a=1, b=2)
    assert fn() == 3

    fn_partial = delay(add).bind(a=1)
    assert fn_partial(b=2) == 3

    fn_direct = delay(add)
    assert fn_direct(a=1, b=2) == 3


def test_delay_with_lambda():
    fn = delay(lambda a, b: a * b).bind(a=3, b=4)
    assert fn() == 12


def test_delay_chain_binding():
    fn1 = delay(lambda a, b, c: a + b + c).bind(a=1)
    fn2 = fn1.bind(b=2)
    assert fn2(c=3) == 6


def test_delay_override_params():
    fn = delay(add).bind(a=1, b=2)
    assert fn(b=5) == 6


def test_delay_with_default_args():
    def fn_with_default(a, b=10):
        return a + b

    fn = delay(fn_with_default).bind(a=5)
    assert fn() == 15
    assert fn(b=20) == 25


def test_pool():
    p = Pool(n_jobs=2, show_progress=False)

    def task_impl(x):
        return x * x

    task = p.submit(task_impl, job_name="test_job")

    task(x=1)
    task(x=2)
    task(x=3)

    assert len(p._job_map["test_job"]) == 3

    results = p.do()

    assert isinstance(results, list)
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


def test_pool_context_manager():
    with Pool(n_jobs=2, show_progress=False) as p:

        def task_impl(x):
            return x + 1

        task = p.submit(task_impl, job_name="test")
        task(x=1)
        task(x=2)

        results = p.do()
        assert sorted(results) == [2, 3]


def test_pool_empty():
    p = Pool(n_jobs=2, show_progress=False)
    results = p.do()
    assert results == []


def test_progress_manager_disabled():
    pm = ProgressManager(show_progress=False)

    task_id = pm.create_task("test_task", total=10)
    assert task_id is None

    pm.update(task_id, advance=5)
    pm.complete(task_id)


def test_progress_manager_context():
    with ProgressManager(show_progress=False) as pm:
        task_id = pm.create_task("test_task", total=10)
        assert task_id is None

        pm.update(task_id, advance=5)
        pm.complete(task_id)
