"""Compare dictionary and corm setup and relationship traversal."""

import argparse
import gc
import platform
from collections.abc import Callable
from statistics import median
from time import perf_counter

from corm import Entity, Field, KeyNested, Nested, Relationship, Storage

Payload = dict[str, list[dict[str, int]]]
OPERATIONS = ("Setup", "Nested tasks", "Task to assignee", "Assignee to tasks")


class Assignee(Entity):
    id: int = Field(pk=True)
    tasks: list["Task"] = Relationship()


class Task(Entity):
    points: int
    assignee: Assignee = KeyNested(
        Assignee.id, origin="assignee_id", back_populates="tasks"
    )


class Project(Entity):
    assignees: list[Assignee] = Nested()
    tasks: list[Task] = Nested()

    def sum_task_points(self) -> int:
        return sum(task.points for task in self.tasks)

    def sum_assignee_ids(self) -> int:
        return sum(task.assignee.id for task in self.tasks)

    def sum_assigned_points(self) -> int:
        return sum(
            task.points for assignee in self.assignees for task in assignee.tasks
        )


class DictProject:
    def __init__(self, data: Payload) -> None:
        self.data = data
        self.assignees_by_id = {
            assignee["id"]: assignee for assignee in data["assignees"]
        }
        self.tasks_by_assignee: dict[int, list[dict[str, int]]] = {
            assignee_id: [] for assignee_id in self.assignees_by_id
        }
        for task in data["tasks"]:
            self.tasks_by_assignee[task["assignee_id"]].append(task)

    def sum_task_points(self) -> int:
        return sum(task["points"] for task in self.data["tasks"])

    def sum_assignee_ids(self) -> int:
        return sum(
            self.assignees_by_id[task["assignee_id"]]["id"]
            for task in self.data["tasks"]
        )

    def sum_assigned_points(self) -> int:
        return sum(
            task["points"]
            for assignee in self.data["assignees"]
            for task in self.tasks_by_assignee[assignee["id"]]
        )


def make_payload(count: int) -> Payload:
    assignee_count = min(count, 16)
    return {
        "assignees": [{"id": i} for i in range(assignee_count)],
        "tasks": [
            {"points": i + 1, "assignee_id": i % assignee_count} for i in range(count)
        ],
    }


def load_corm(data: Payload) -> Project:
    return Project(data, Storage())


def measure(
    count: int, load: Callable[[Payload], DictProject | Project]
) -> list[float]:
    # corm wraps its input in place, so each sample needs a fresh payload.
    payload = make_payload(count)
    points = sum(task["points"] for task in payload["tasks"])
    assignee_ids = sum(task["assignee_id"] for task in payload["tasks"])
    gc.collect()

    start = perf_counter()
    project = load(payload)
    timings = [perf_counter() - start]

    scans = (
        project.sum_task_points,
        project.sum_assignee_ids,
        project.sum_assigned_points,
    )
    for scan, expected in zip(scans, (points, assignee_ids, points), strict=True):
        start = perf_counter()
        actual = scan()
        timings.append(perf_counter() - start)
        if actual != expected:
            raise AssertionError(
                f"{scan.__qualname__} returned {actual}, expected {expected}"
            )

    return timings


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "counts",
        metavar="COUNT",
        nargs="*",
        type=positive_int,
        default=[8000, 80000],
        help="task counts (default: 8000 80000)",
    )
    parser.add_argument(
        "--repeat", type=positive_int, default=5, help="samples per case (default: 5)"
    )
    args = parser.parse_args()

    python = f"{platform.python_implementation()} {platform.python_version()}"
    print(f"{python} on {platform.platform()}")
    for count in args.counts:
        print(
            f"\n{count:,} tasks, median of {args.repeat} samples per case", flush=True
        )
        dict_samples = []
        corm_samples = []
        for _ in range(args.repeat):
            dict_samples.append(measure(count, DictProject))
            corm_samples.append(measure(count, load_corm))

        print(
            f"{'Operation':<20} {'dict (ms)':>12} {'corm (ms)':>12} {'corm/dict':>10}"
        )
        for operation, raw, wrapped in zip(
            OPERATIONS,
            zip(*dict_samples, strict=True),
            zip(*corm_samples, strict=True),
            strict=True,
        ):
            dict_ms = median(raw) * 1000
            corm_ms = median(wrapped) * 1000
            ratio = f"{corm_ms / dict_ms:.2f}x" if dict_ms else "n/a"
            print(f"{operation:<20} {dict_ms:>12.6f} {corm_ms:>12.6f} {ratio:>10}")


if __name__ == "__main__":
    main()
