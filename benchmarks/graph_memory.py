"""Measure retained Python allocations in the relationship benchmark graph."""

import gc
import platform
import sys
import tracemalloc
from statistics import median

from benchmarks.dict_vs_corm import load_corm, make_payload


def sample(count):
    gc.collect()
    tracemalloc.start()
    try:
        project = load_corm(make_payload(count))
        points = count * (count + 1) // 2
        assert project.sum_task_points() == project.sum_assigned_points() == points
        assert project.sum_assignee_ids() == sum(i % 16 for i in range(count))
        gc.collect()
        retained = tracemalloc.get_traced_memory()[0]
    finally:
        tracemalloc.stop()

    entities = [project, *project.assignees, *project.tasks]
    revisions = (e._paired_list_revisions for e in entities)
    empty = [value for value in revisions if value is not None and not value]
    return retained, len(empty), sum(map(sys.getsizeof, empty))


if __name__ == "__main__":
    sample(16)  # Resolve descriptors and warm the interpreter before measuring.
    samples = [sample(20_000) for _ in range(3)]
    print(f"{platform.python_implementation()} {platform.python_version()}")
    print(f"Retained bytes: {[row[0] for row in samples]}")
    print(f"Median: {median(row[0] for row in samples):,.0f} bytes")
    print(f"Empty revision dictionaries (count, shallow bytes): {samples[-1][1:]}")
