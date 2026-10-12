# Daily task service

A small, synchronous refactor of the supplied task runner. It uses only the Python standard library.

## Design

- `Task` validates submitted dictionary data and holds the task ID, user, daily `HH:MM` time, action name, and parameters.
- `UserManager` registers users and counts successful executions per user and calendar date.
- `TaskExecutor` routes actions through a registry and logs execution outcomes. An action implements `execute(parameters)`.
- `DailyScheduler` stores tasks, selects those due in the current minute, checks quota, and runs each scheduled occurrence once.

Tasks scheduled for the same minute are processed in submission order. This is a synchronous implementation: they can all be due simultaneously, while actions execute one at a time.

Each due task receives one attempt per date. A failed action is logged, does not use quota, and is not retried automatically that day. A task skipped for quota is likewise not retried that day. The next day is a new scheduled occurrence. This avoids repeating a possibly partially completed action. Adding retries later would require an explicit retry policy and idempotent action design.

The `sync`, `backup`, and `delete` actions in the demo only log their intended operation. They never change files.

## Run

From this directory:

```text
python -m unittest discover -s tests -v
python -m task_service.demo
```

`DailyScheduler.run_due(datetime.now())` is the scheduler entry point. A process timer can call it once a minute. Callers can pass a specific `datetime` in tests. The service uses the date and time supplied by the caller; production callers should choose and consistently use their intended timezone.

## QA coverage

The unit tests cover valid and malformed task input, optional parameters, time boundaries, user registration and zero quotas, unknown users and actions, duplicate registrations and task IDs, action success and failure logging, quota accounting, multiple tasks due together, non-due tasks, duplicate scheduler checks, midnight, and next-day execution. The demo exercises all three simulated action names.

These checks cover the defined behavior of this single-process implementation. They cannot establish correctness for process restarts, concurrent workers, or persistence because those capabilities are outside its current scope.

## Growth path

The in-memory task list, usage counts, and attempt markers are suitable for one process and a small exercise. They reset on process restart, and each scheduler check scans all tasks. For a durable service, store tasks and run records in a database with a unique `(task_id, scheduled_date)` key and an index on scheduled time. Reserve quota atomically alongside claiming a run so multiple workers cannot exceed it. A queue and worker pool can then distribute due tasks while preserving the same task model and action interface. Monitor failures and add an explicit retry policy per action.
