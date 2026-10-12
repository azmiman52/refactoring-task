"""Action dispatch and execution logging."""

import logging
from typing import Any, Protocol

from .models import Task

logger = logging.getLogger(__name__)


class Action(Protocol):
    def execute(self, parameters: dict[str, Any]) -> None:
        """Perform one action with its task-specific parameters."""


class ActionExecutionError(Exception):
    """An action failed while running a task."""


class TaskExecutor:
    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(self, name: str, action: Action) -> None:
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError(f"Invalid action name: {name}")
        if name in self._actions:
            raise ValueError(f"Duplicate action: {name}")
        if not callable(getattr(action, "execute", None)):
            raise ValueError(f"Action {name} must define execute(parameters)")
        self._actions[name] = action

    def has_action(self, name: str) -> bool:
        return name in self._actions

    def execute(self, task: Task) -> None:
        try:
            action = self._actions[task.action]
        except KeyError as exc:
            raise ValueError(f"Unknown action: {task.action}") from exc

        logger.info("Starting task=%s user=%s action=%s", task.task_id, task.user, task.action)
        try:
            action.execute(task.parameters.copy())
        except Exception as exc:
            logger.exception("Failed task=%s user=%s action=%s", task.task_id, task.user, task.action)
            raise ActionExecutionError(f"Task {task.task_id} failed") from exc
        logger.info("Succeeded task=%s user=%s action=%s", task.task_id, task.user, task.action)


class SimulatedAction:
    """Exercise action routing without changing the file system."""

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, parameters: dict[str, Any]) -> None:
        logger.info("Simulated action=%s parameters=%s", self.name, parameters)
