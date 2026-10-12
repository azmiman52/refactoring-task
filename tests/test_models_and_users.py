import unittest
from datetime import date, time

from task_service.models import Task
from task_service.users import UserManager


class TaskModelTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            "task_id": "task-1", "user": "alice", "time": "12:00", "action": "sync",
        }

    def test_accepts_configurable_parameters(self):
        source = self.valid | {"parameters": {"target": "/data/x", "force": True}}
        task = Task.from_dict(source)
        source["parameters"]["target"] = "changed"
        self.assertEqual(task.scheduled_time, time(12, 0))
        self.assertEqual(task.parameters, {"target": "/data/x", "force": True})

    def test_default_parameters_and_time_boundaries(self):
        for value, expected in (("00:00", time(0, 0)), ("23:59", time(23, 59))):
            with self.subTest(value=value):
                task = Task.from_dict(self.valid | {"time": value})
                self.assertEqual(task.scheduled_time, expected)
                self.assertEqual(task.parameters, {})

    def test_rejects_missing_empty_and_wrong_type_required_fields(self):
        for field in ("task_id", "user", "time", "action"):
            for value in (None, "", "   ", 1):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    Task.from_dict(self.valid | {field: value})
            incomplete = self.valid.copy()
            del incomplete[field]
            with self.subTest(field=field, value="missing"), self.assertRaisesRegex(ValueError, field):
                Task.from_dict(incomplete)

    def test_rejects_bad_time_and_parameters(self):
        for replacement in (
            {"time": "12:00:00"}, {"time": "25:00"}, {"time": "12:60"},
            {"time": "1:00"}, {"time": "noon"}, {"parameters": []},
            {"parameters": None},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                Task.from_dict(self.valid | replacement)

    def test_rejects_non_dictionary_input(self):
        with self.assertRaisesRegex(ValueError, "dictionary"):
            Task.from_dict(None)


class UserManagerTests(unittest.TestCase):
    def test_quota_is_per_user_and_day(self):
        users = UserManager()
        users.add_user("alice", 1)
        users.add_user("bob", 1)
        first_day = date(2026, 10, 12)
        users.record_success("alice", first_day)
        self.assertFalse(users.can_execute("alice", first_day))
        self.assertTrue(users.can_execute("bob", first_day))
        self.assertTrue(users.can_execute("alice", date(2026, 10, 13)))
        with self.assertRaisesRegex(ValueError, "quota exhausted"):
            users.record_success("alice", first_day)

    def test_rejects_unknown_user_and_invalid_quota(self):
        users = UserManager()
        for operation in (users.usage, users.can_execute, users.record_success):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, "Unknown user"):
                operation("missing", date(2026, 10, 12))
        for invalid in (True, -1, 1.5, "3", None):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "quota"):
                users.add_user("alice", invalid)
        for invalid in ("", "  ", None, 7):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "name"):
                users.add_user(invalid, 1)

    def test_zero_quota_and_duplicate_user(self):
        users = UserManager()
        users.add_user(" alice ", 0)
        self.assertTrue(users.has_user("alice"))
        self.assertFalse(users.can_execute("alice", date(2026, 10, 12)))
        with self.assertRaisesRegex(ValueError, "already exists"):
            users.add_user("alice", 2)


if __name__ == "__main__":
    unittest.main()
