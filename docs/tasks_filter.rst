Tasks filtering
===============

By now, tasks can be filtered by worker, type, state, received and started datetime.
Also, filtering by args/kwargs/result/state value available.

Task filter syntax
------------------

Flower uses github-style syntax for args/kwargs/result filtering.

 - `foo` find all tasks containing foo in args, kwargs or result
 - `args:foo` find all tasks containing foo in arguments
 - `kwargs:foo=bar` find all tasks containing foo=bar keyword
 - `result:foo` find all tasks containing foo in result
 - `state:FAILURE` find all failed tasks

If the search term contains spaces it should be enclosed in " (e.g. `args:"hello world"`).

For examples, see `tests/utils/test_search.py`.
