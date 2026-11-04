from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import User
from tasks.models import Task


class SeedTestDataTests(TestCase):
    def test_creates_accounts_and_one_task_per_status(self):
        call_command("seed_test_data")
        self.assertEqual(
            set(User.objects.values_list("role", flat=True)),
            {"member", "project_manager", "admin"},
        )
        statuses = set(Task.objects.values_list("status", flat=True))
        self.assertEqual(statuses, set(Task.Status.values))
        user = User.objects.get(email="member@example.com")
        self.assertTrue(user.check_password("SEPROG123"))

    def test_safe_to_run_twice(self):
        call_command("seed_test_data")
        users, tasks = User.objects.count(), Task.objects.count()
        call_command("seed_test_data")
        self.assertEqual(User.objects.count(), users)
        self.assertEqual(Task.objects.count(), tasks)

    @override_settings(SETTINGS_MODULE="config.settings.prod")
    def test_refuses_outside_dev_test(self):
        with self.assertRaises(CommandError):
            call_command("seed_test_data")
        self.assertEqual(User.objects.count(), 0)
