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

## Query scope

Run `python -m benchmarks.query_scope` to reproduce the experiment for #5.
Each case builds an application-owned list of 10,000 standalone users and
searches for the last user's name. The prototype scans the private key index,
includes subclasses and yields each Python object once. It compares an inline
condition with a prebuilt field-equality predicate. A separate timing looks
up the last ID directly through each declared primary-key field.

Times are medians of five batches of 20 calls, with construction excluded.
For the unkeyed case the keyed scans search an empty index. The lifetime check
drops the application list, counts live weak references with the store still
alive, then drops the store. These users have no relationships.

## Retained memory of a related graph

Run `python -m benchmarks.graph_memory` from the checkout. Each sample loads
20,000 tasks and 16 assignees into one project and checks traversal in both
directions. Tracing starts before payload creation. The reported allocation
count in bytes is taken with the graph alive after garbage collection.
Descriptor resolution is warmed on a small graph first. Empty revision
dictionaries are counted separately after tracing stops.

To repeat the original layout experiment, use a disposable copy of commit
`8e9f34e`. Give all three
entity classes in `benchmarks/dict_vs_corm.py` an empty `__slots__ = ()` and
run the baseline. For the second run, also give the base `Entity` slots for
`_data`, `storage`, `_paired_list_revisions`, `_paired_list_views` and
`__weakref__`. Move the class default for `_paired_list_views` to
`self._paired_list_views = None` in its constructor, leaving the annotation
on the class. Run each layout in a fresh process with the same interpreter.

| CPython 3.14.5, median of three samples | Retained bytes |
| --- | ---: |
| Ordinary base | 10,335,440 |
| Slotted base and subclasses | 10,014,824 |

Slots saved 320,616 bytes (3.1%) on this graph. Both layouts retained 20,017
empty revision dictionaries with a combined shallow size of 1,281,088 bytes.
This graph exercises a scalar paired owner and its reverse collection.
A workload that edits owning many-valued fields can populate the dictionaries.

### Allocate revision counters on first write

On CPython 3.14.5 the original read workload dropped from 10,335,440 to
8,894,224 retained bytes (13.9%). Run `python -m benchmarks.edited_graph_memory`
for the mutation workload. It creates 10,000 owner/target pairs, removes each
link through the owner and restores it through the reverse field. The median
of three samples dropped from 32,187,472 to 31,467,472 bytes (2.2%). To
compare versions, run the same benchmark scripts on both checkouts.
