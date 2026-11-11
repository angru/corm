# Dictionary and corm benchmark

Run from the repository root with Python 3.11 or later. The benchmark uses the
checkout and the Python standard library.

```sh
python -m benchmarks.dict_vs_corm
python -m benchmarks.dict_vs_corm --repeat 3 100 1000
```

The default run takes five samples at each of 8,000 and 80,000 tasks. Each
sample starts with an equivalent project dictionary. Tasks are assigned to up
to 16 assignees in round-robin order. Each row reports the median elapsed time
in milliseconds for one setup or one complete scan, and the ratio of the corm
median to the dictionary median.

| Operation | Raw dictionaries | corm |
| --- | --- | --- |
| Setup | Build an assignee lookup by ID and group tasks by assignee ID | Create storage, wrap assignees and tasks with `Nested`, and register the paired `KeyNested` links |
| Nested tasks | Traverse the project's task list and sum task points | Traverse `project.tasks` and sum task points |
| Task to assignee | Resolve each task's assignee through the ID lookup and sum the resolved IDs | Follow each `task.assignee` and sum the resolved IDs |
| Assignee to tasks | Traverse each assignee's task group and sum task points | Follow each `assignee.tasks` relationship and sum task points |

The runner generates fresh input and checks scan results outside the timed
regions. Setup and traversal are timed separately on the same input per sample.
The timings describe this read workload on the reported Python version and
platform. Input parsing, relationship edits, export, and memory usage are
outside the measured operations.

To measure the single-target back-relation load from issue #23 in isolation,
run `python -m benchmarks.relation_membership 8000 80000`.
