"""In-memory daily scheduling and task orchestration."""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from .executor import ActionExecutionError, TaskExecutor
from .models import Task
from .users import UserManager

logger = logging.getLogger(__name__)


class Outcome(str, Enum):
    SUCCEEDED = "succeeded"
    QUOTA_EXCEEDED = "quota_exceeded"
    FAILED = "failed"


@dataclass(frozen=True)
class RunResult:
    task_id: str
    outcome: Outcome


class DailyScheduler:
    def __init__(self, users: UserManager, executor: TaskExecutor) -> None:
        self._users = users
        self._executor = executor
        self._tasks: dict[str, Task] = {}
        self._attempted: set[tuple[date, str]] = set()

    def submit(self, data: dict[str, Any]) -> Task:
        task = Task.from_dict(data)
        if not self._users.has_user(task.user):
            raise ValueError(f"Unknown user: {task.user}")
        if not self._executor.has_action(task.action):
            raise ValueError(f"Unknown action: {task.action}")
        if task.task_id in self._tasks:
            raise ValueError(f"Duplicate task ID: {task.task_id}")
        self._tasks[task.task_id] = task
        logger.info("Submitted task=%s user=%s time=%s", task.task_id, task.user, task.scheduled_time)
        return task

    def run_due(self, now: datetime) -> list[RunResult]:
        """Attempt tasks scheduled for this minute once on the given date."""
        results: list[RunResult] = []
        current_minute = now.time().replace(second=0, microsecond=0)
        for task in self._tasks.values():
            key = (now.date(), task.task_id)
            if task.scheduled_time != current_minute or key in self._attempted:
                continue
            self._attempted.add(key)

            if not self._users.can_execute(task.user, now.date()):
                logger.warning("Quota exceeded task=%s user=%s date=%s", task.task_id, task.user, now.date())
                results.append(RunResult(task.task_id, Outcome.QUOTA_EXCEEDED))
                continue

            try:
                self._executor.execute(task)
            except ActionExecutionError:
                results.append(RunResult(task.task_id, Outcome.FAILED))
                continue

            self._users.record_success(task.user, now.date())
            results.append(RunResult(task.task_id, Outcome.SUCCEEDED))
        return results
