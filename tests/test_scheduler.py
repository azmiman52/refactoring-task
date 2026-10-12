import unittest
from datetime import datetime

from task_service import DailyScheduler, Outcome, TaskExecutor, UserManager


class RecordingAction:
    def __init__(self):
        self.calls = []

    def execute(self, parameters):
        self.calls.append(parameters)


class FailingAction:
    def execute(self, parameters):
        raise RuntimeError("sample failure")


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.users = UserManager()
        self.users.add_user("alice", 2)
        self.users.add_user("bob", 1)
        self.action = RecordingAction()
        self.executor = TaskExecutor()
        self.executor.register("sync", self.action)
        self.executor.register("fail", FailingAction())
        self.scheduler = DailyScheduler(self.users, self.executor)
        self.noon = datetime(2026, 10, 12, 12, 0)

    def submit(self, task_id, user="alice", action="sync", parameters=None):
        return self.scheduler.submit({
            "task_id": task_id, "user": user, "time": "12:00",
            "action": action, "parameters": parameters or {"target": task_id},
        })

    def test_multiple_due_tasks_obey_per_user_quota(self):
        self.submit("a1")
        self.submit("b1", user="bob")
        self.submit("a2")
        self.submit("a3")
        with self.assertLogs("task_service", level="INFO") as logs:
            results = self.scheduler.run_due(self.noon)
        self.assertEqual([r.outcome for r in results], [
            Outcome.SUCCEEDED, Outcome.SUCCEEDED, Outcome.SUCCEEDED, Outcome.QUOTA_EXCEEDED,
        ])
        self.assertEqual(len(self.action.calls), 3)
        self.assertEqual(self.users.usage("alice", self.noon.date()), 2)
        self.assertTrue(any("Quota exceeded task=a3" in line for line in logs.output))

    def test_same_minute_does_not_repeat_and_next_day_runs_again(self):
        self.submit("a1")
        self.assertEqual(len(self.scheduler.run_due(self.noon)), 1)
        self.assertEqual(self.scheduler.run_due(self.noon.replace(second=40)), [])
        self.assertEqual(len(self.scheduler.run_due(self.noon.replace(day=13))), 1)
        self.assertEqual(len(self.action.calls), 2)

    def test_failure_is_logged_without_quota_or_automatic_retry(self):
        self.submit("bad", action="fail")
        self.submit("good")
        with self.assertLogs("task_service.executor", level="ERROR") as logs:
            results = self.scheduler.run_due(self.noon)
        self.assertEqual([r.outcome for r in results], [Outcome.FAILED, Outcome.SUCCEEDED])
        self.assertIn("Failed task=bad user=alice", logs.output[0])
        self.assertEqual(self.users.usage("alice", self.noon.date()), 1)
        self.assertEqual(self.scheduler.run_due(self.noon), [])

    def test_failed_task_is_eligible_again_next_day(self):
        self.submit("bad", action="fail")
        with self.assertLogs("task_service.executor", level="ERROR"):
            first = self.scheduler.run_due(self.noon)
            second = self.scheduler.run_due(self.noon.replace(day=13))
        self.assertEqual(first[0].outcome, Outcome.FAILED)
        self.assertEqual(second[0].outcome, Outcome.FAILED)
        self.assertEqual(self.users.usage("alice", self.noon.date()), 0)

    def test_quota_skip_is_not_retried_that_day(self):
        self.users.add_user("no-quota", 0)
        self.submit("skipped", user="no-quota")
        with self.assertLogs("task_service.scheduler", level="WARNING"):
            first = self.scheduler.run_due(self.noon)
        self.assertEqual(first[0].outcome, Outcome.QUOTA_EXCEEDED)
        self.assertEqual(self.scheduler.run_due(self.noon.replace(second=30)), [])
        self.assertEqual(self.action.calls, [])

    def test_only_tasks_due_in_current_minute_run(self):
        self.submit("a1")
        self.assertEqual(self.scheduler.run_due(self.noon.replace(hour=11, minute=59)), [])
        self.assertEqual(len(self.scheduler.run_due(self.noon)), 1)

    def test_midnight_task_runs_once_per_calendar_date(self):
        self.scheduler.submit({
            "task_id": "midnight", "user": "alice", "time": "00:00", "action": "sync",
        })
        first_day = self.noon.replace(hour=0)
        self.assertEqual(self.scheduler.run_due(first_day.replace(minute=1)), [])
        self.assertEqual(self.scheduler.run_due(first_day)[0].outcome, Outcome.SUCCEEDED)
        self.assertEqual(self.scheduler.run_due(first_day.replace(second=59)), [])
        self.assertEqual(self.scheduler.run_due(first_day.replace(day=13))[0].outcome, Outcome.SUCCEEDED)
        self.assertEqual(len(self.action.calls), 2)

    def test_rejects_unknown_user_action_and_duplicate_task_id(self):
        with self.assertRaisesRegex(ValueError, "Unknown user"):
            self.submit("bad-user", user="missing")
        with self.assertRaisesRegex(ValueError, "Unknown action"):
            self.submit("bad-action", action="delete")
        self.submit("a1")
        with self.assertRaisesRegex(ValueError, "Duplicate task ID"):
            self.submit("a1")

    def test_rejects_malformed_submission_without_storing_it(self):
        with self.assertRaisesRegex(ValueError, "time"):
            self.scheduler.submit({
                "task_id": "bad", "user": "alice", "time": "25:00", "action": "sync",
            })
        self.submit("bad")
        self.assertEqual(self.scheduler.run_due(self.noon)[0].outcome, Outcome.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
