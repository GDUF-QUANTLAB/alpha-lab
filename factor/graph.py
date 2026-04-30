from collections import deque


def topological_sort(*functions) -> list:
    if not functions:
        return []

    all_functions: set = set()
    queue = deque(functions)

    while queue:
        func = queue.popleft()
        if func in all_functions:
            continue
        all_functions.add(func)
        if hasattr(func, "_depends"):
            for dep in func._depends:
                if dep not in all_functions:
                    queue.append(dep)

    in_degree: dict = dict.fromkeys(all_functions, 0)
    for func in all_functions:
        if hasattr(func, "_depends"):
            for _ in func._depends:
                in_degree[func] += 1

    result: list = []
    zero_in_degree = deque([f for f in all_functions if in_degree[f] == 0])

    while zero_in_degree:
        func = zero_in_degree.popleft()
        result.append(func)

        for dependent in all_functions:
            if hasattr(dependent, "_depends") and func in dependent._depends:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    zero_in_degree.append(dependent)

    if len(result) != len(all_functions):
        raise ValueError("Circular dependency detected in function DAG")

    return result


def group_by_level(*functions) -> list[list]:
    if not functions:
        return []

    sorted_functions = topological_sort(*functions)

    level_map: dict = {}

    for func in sorted_functions:
        if not hasattr(func, "_depends") or not func._depends:
            level_map[func] = 0
        else:
            max_dep_level = max(level_map[dep] for dep in func._depends)
            level_map[func] = max_dep_level + 1

    max_level = max(level_map.values()) if level_map else 0
    levels: list[list] = [[] for _ in range(max_level + 1)]

    for func, level in level_map.items():
        levels[level].append(func)

    return levels


def get_execution_plan(*functions) -> dict:
    groups = group_by_level(*functions)
    independent = [f for f in set(topological_sort(*functions)) if not f._depends]

    return {
        "parallel_groups": groups,
        "total_functions": sum(len(g) for g in groups),
        "independent_functions": len(independent),
        "max_parallelism": max(len(g) for g in groups) if groups else 0,
    }
