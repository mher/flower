Tasks filtering
===============

Tasks can be filtered by worker, type, state, received and started datetime.
The search box also supports boolean searches over task details.

Flower uses a small GitHub Issues-style query syntax. Whitespace is an implicit
``AND``; ``AND`` can also be written explicitly. Use uppercase ``OR`` and
parentheses when either condition may match.

 - ``email invoice`` finds tasks containing both substrings
 - ``email AND invoice`` is the explicit equivalent
 - ``invoice OR receipt`` finds tasks containing either substring
 - ``(email OR report) urgent`` finds tasks containing urgent and either email or report
 - ``"connection refused"`` finds that contiguous substring
 - ``args:customer`` searches for customer anywhere in task arguments
 - ``kwargs:queue=priority`` searches for an exact keyword/value pair
 - ``result:timeout`` searches for timeout anywhere in task results
 - ``name:send_email`` finds task names containing send_email
 - ``worker:celery@host`` finds worker names containing celery@host
 - ``state:FAILURE`` finds failed tasks
 - ``(state:FAILURE OR state:RETRY)`` finds failed or retried tasks

The searchable qualifiers are ``name:``, ``state:``, ``worker:``, ``args:``,
``kwargs:``, and ``result:``. A sufficiently long part of a UUID finds that task,
so there is no separate UUID qualifier. Plain terms, ``name:``, ``worker:``,
``args:``, ``kwargs:``, and ``result:`` use case-insensitive substring matching.
Each substring term must contain at least three characters. ``state:`` uses exact
matching and ``kwargs:key=value`` matches an exact normalized pair; those forms are
exempt from the length limit. The separate worker API filter retains exact matching.
Terms containing spaces must be enclosed in double quotes, for example
``result:"connection refused"``.

Negation is not supported. The task API returns HTTP status 400 for invalid queries;
the task table presents the same syntax error below the search box.
