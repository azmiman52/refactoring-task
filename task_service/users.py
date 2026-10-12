"""User registration and per-day execution quotas."""

from datetime import date


class UserManager:
    def __init__(self) -> None:
        self._quotas: dict[str, int] = {}
        self._usage: dict[tuple[str, date], int] = {}

    def add_user(self, name: str, daily_quota: int) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("User name must be a non-empty string")
        if isinstance(daily_quota, bool) or not isinstance(daily_quota, int) or daily_quota < 0:
            raise ValueError("Daily quota must be a non-negative integer")
        name = name.strip()
        if name in self._quotas:
            raise ValueError(f"User already exists: {name}")
        self._quotas[name] = daily_quota

    def has_user(self, name: str) -> bool:
        return name in self._quotas

    def usage(self, name: str, day: date) -> int:
        self._require_user(name)
        return self._usage.get((name, day), 0)

    def can_execute(self, name: str, day: date) -> bool:
        self._require_user(name)
        return self.usage(name, day) < self._quotas[name]

    def record_success(self, name: str, day: date) -> None:
        if not self.can_execute(name, day):
            raise ValueError(f"Daily quota exhausted for {name} on {day}")
        key = (name, day)
        self._usage[key] = self._usage.get(key, 0) + 1

    def _require_user(self, name: str) -> None:
        if name not in self._quotas:
            raise ValueError(f"Unknown user: {name}")
