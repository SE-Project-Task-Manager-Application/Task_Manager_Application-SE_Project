"""Seed the dev/test database with the three test accounts and sample tasks (S-07b).

Usage: python manage.py seed_test_data

- Accounts and password match SETUP.md.
- One sample task per status, read from Task.Status (not hard-coded).
- Safe to run twice: existing rows are updated, not duplicated.
- Refuses to run outside the dev/test settings.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from tasks.models import Task, TaskAssignment

SEED_PASSWORD = "SEPROG123"
ALLOWED_SETTINGS = {"dev", "test"}

ACCOUNTS = [
    ("member@example.com", User.Role.MEMBER),
    ("pm@example.com", User.Role.PROJECT_MANAGER),
    ("admin@example.com", User.Role.ADMIN),
]


class Command(BaseCommand):
    help = "Create the test accounts and sample tasks (dev/test only)."

    def handle(self, *args, **options):
        module = settings.SETTINGS_MODULE.rsplit(".", 1)[-1]
        if module not in ALLOWED_SETTINGS:
            raise CommandError(
                f"Refusing to seed data with settings '{settings.SETTINGS_MODULE}'. "
                "This command only runs with the dev or test settings."
            )

        users = {}
        for email, role in ACCOUNTS:
            is_admin = role == User.Role.ADMIN
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email,
                    SEED_PASSWORD,
                    role=role,
                    is_staff=is_admin,
                    is_superuser=is_admin,
                )
            else:
                user.role = role
                user.is_active = True
                user.deleted_at = None
                user.is_staff = is_admin
                user.is_superuser = is_admin
                if not user.check_password(SEED_PASSWORD):
                    user.set_password(SEED_PASSWORD)
                user.save()
            users[role] = user

        member = users[User.Role.MEMBER]
        manager = users[User.Role.PROJECT_MANAGER]

        for value, label in Task.Status.choices:
            Task.objects.update_or_create(
                owner=member,
                title=f"Sample task: {label}",
                defaults={
                    "description": f"Seeded task with status '{label}'.",
                    "status": value,
                    "deleted_at": None,
                },
            )

        assigned, _ = Task.objects.update_or_create(
            owner=manager,
            title="Sample task: assigned to member, due soon",
            defaults={
                "description": "Seeded task for assignment and reminder tests.",
                "status": Task.Status.TODO,
                "due_date": timezone.now() + timedelta(days=1),
                "deleted_at": None,
            },
        )
        TaskAssignment.objects.get_or_create(
            task=assigned, user=member, defaults={"assigned_by": manager}
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(ACCOUNTS)} accounts and "
                f"{Task.objects.active().count()} active tasks "
                f"(password for all test accounts: {SEED_PASSWORD})."
            )
        )
