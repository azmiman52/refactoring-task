"""Validated task data supplied by users."""

from dataclasses import dataclass, field
from datetime import time
from typing import Any


@dataclass(frozen=True)
class Task:
    task_id: str
    user: str
    scheduled_time: time
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        if not isinstance(data, dict):
            raise ValueError("Task must be a dictionary")

        for key in ("task_id", "user", "time", "action"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"Task {key} must be a non-empty string")

        try:
            scheduled_time = time.fromisoformat(data["time"])
        except ValueError as exc:
            raise ValueError("Task time must use HH:MM format") from exc
        if len(data["time"]) != 5 or data["time"][2] != ":":
            raise ValueError("Task time must use HH:MM format")

        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("Task parameters must be a dictionary")

        return cls(
            task_id=data["task_id"].strip(),
            user=data["user"].strip(),
            scheduled_time=scheduled_time,
            action=data["action"].strip(),
            parameters=parameters.copy(),
        )
