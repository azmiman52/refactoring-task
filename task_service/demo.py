"""Run the original sample tasks through the refactored service."""

import logging
from datetime import datetime

from .executor import SimulatedAction, TaskExecutor
from .scheduler import DailyScheduler
from .users import UserManager


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    users = UserManager()
    users.add_user("alice", daily_quota=3)
    users.add_user("bob", daily_quota=5)

    executor = TaskExecutor()
    for name in ("sync", "backup", "delete"):
        executor.register(name, SimulatedAction(name))

    scheduler = DailyScheduler(users, executor)
    for task in (
        {"task_id": "alice-sync", "user": "alice", "time": "12:00", "action": "sync", "parameters": {"target": "/data/x"}},
        {"task_id": "bob-backup", "user": "bob", "time": "12:00", "action": "backup", "parameters": {"target": "/srv/y"}},
        {"task_id": "alice-delete", "user": "alice", "time": "12:00", "action": "delete", "parameters": {"target": "/tmp/z"}},
    ):
        scheduler.submit(task)

    for result in scheduler.run_due(datetime.now().replace(hour=12, minute=0)):
        logging.info("Result task=%s outcome=%s", result.task_id, result.outcome.value)


if __name__ == "__main__":
    main()
