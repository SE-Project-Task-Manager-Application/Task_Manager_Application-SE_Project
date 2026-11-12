"""Queue due-date reminders and retry scheduled email delivery."""

from django.core.management.base import BaseCommand

from notif.services import NotificationService


class Command(BaseCommand):
    help = "Queue task due-date reminders and deliver due notifications."

    def handle(self, *args, **options):
        queued = NotificationService.enqueue_due_reminders()
        sent, failed, cancelled = NotificationService.deliver_scheduled()
        self.stdout.write(self.style.SUCCESS(
            f"Queued {queued}; sent {sent}; failed {failed}; cancelled {cancelled}."
        ))
