import unittest

from task_service import SimulatedAction, Task, TaskExecutor
from task_service.executor import ActionExecutionError


class MutatingAction:
    def execute(self, parameters):
        parameters["target"] = "changed"


class FailingAction:
    def execute(self, parameters):
        raise RuntimeError("sample failure")


class ExecutorTests(unittest.TestCase):
    def make_task(self, action="delete"):
        return Task.from_dict({
            "task_id": "sample", "user": "alice", "time": "12:00",
            "action": action, "parameters": {"target": "/tmp/z"},
        })

    def test_simulated_action_logs_and_succeeds(self):
        executor = TaskExecutor()
        executor.register("delete", SimulatedAction("delete"))
        with self.assertLogs("task_service.executor", level="INFO") as logs:
            executor.execute(self.make_task())
        self.assertTrue(any("Simulated action=delete" in line for line in logs.output))
        self.assertTrue(any("Succeeded task=sample user=alice" in line for line in logs.output))

    def test_rejects_invalid_or_duplicate_registration(self):
        executor = TaskExecutor()
        for name in ("", "  ", " delete ", None, 3):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Invalid action name"):
                executor.register(name, SimulatedAction("delete"))
        with self.assertRaisesRegex(ValueError, "must define execute"):
            executor.register("broken", object())
        executor.register("delete", SimulatedAction("delete"))
        with self.assertRaisesRegex(ValueError, "Duplicate action"):
            executor.register("delete", SimulatedAction("delete"))

    def test_rejects_unknown_action(self):
        with self.assertRaisesRegex(ValueError, "Unknown action: delete"):
            TaskExecutor().execute(self.make_task())

    def test_action_failure_is_logged_and_wrapped(self):
        executor = TaskExecutor()
        executor.register("fail", FailingAction())
        with self.assertLogs("task_service.executor", level="ERROR") as logs:
            with self.assertRaises(ActionExecutionError) as raised:
                executor.execute(self.make_task("fail"))
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertIn("Failed task=sample user=alice action=fail", logs.output[0])

    def test_action_cannot_change_stored_task_parameters(self):
        executor = TaskExecutor()
        executor.register("mutate", MutatingAction())
        task = self.make_task("mutate")
        executor.execute(task)
        self.assertEqual(task.parameters, {"target": "/tmp/z"})


if __name__ == "__main__":
    unittest.main()
